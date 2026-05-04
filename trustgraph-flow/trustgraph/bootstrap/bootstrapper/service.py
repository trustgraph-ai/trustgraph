"""
Bootstrapper processor.

Runs a pluggable list of initialisers in a reconciliation loop.
Each initialiser's completion state is recorded in the reserved
``__system__`` workspace under the ``init-state`` config type.

See docs/tech-specs/bootstrap.md for the full design.
"""

import asyncio
import importlib
import json
import logging
import uuid
from argparse import ArgumentParser
from dataclasses import dataclass

from trustgraph.base import AsyncProcessor
from trustgraph.base import ProducerMetrics, SubscriberMetrics
from trustgraph.base.config_client import ConfigClient
from trustgraph.base.request_response_spec import RequestResponse
from trustgraph.schema import (
    ConfigRequest, ConfigResponse,
    config_request_queue, config_response_queue,
)
from trustgraph.schema import (
    FlowRequest, FlowResponse,
    flow_request_queue, flow_response_queue,
)

from .. base import Initialiser, InitContext

logger = logging.getLogger(__name__)

default_ident = "bootstrap"

# Reserved workspace + config type under which completion state is
# stored.  Reserved (`_`-prefix) workspaces are excluded from the
# config push broadcast — live processors never see these keys.
SYSTEM_WORKSPACE = "__system__"
INIT_STATE_TYPE = "init-state"

# Cadence tiers.
GATE_BACKOFF = 5           # Services not responding; retry soon.
INIT_RETRY = 15            # Gate passed but something ran/failed;
                           # converge quickly.
STEADY_INTERVAL = 300      # Everything at target flag; idle cheaply.


@dataclass
class InitialiserSpec:
    """One entry in the bootstrapper's configured list of initialisers."""
    name: str
    flag: str
    instance: Initialiser


def _resolve_class(dotted):
    """Import and return a class by its dotted path."""
    module_path, _, class_name = dotted.rpartition(".")
    if not module_path:
        raise ValueError(
            f"Initialiser class must be a dotted path, got {dotted!r}"
        )
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _load_initialisers_file(path):
    """Load the initialisers spec list from a YAML or JSON file.

    File shape:

    .. code-block:: yaml

        initialisers:
          - class: trustgraph.bootstrap.initialisers.PulsarTopology
            name: pulsar-topology
            flag: v1
            params:
              admin_url: http://pulsar:8080
              tenant: tg
          - ...
    """
    with open(path) as f:
        content = f.read()
    if path.endswith((".yaml", ".yml")):
        import yaml
        doc = yaml.safe_load(content)
    else:
        doc = json.loads(content)
    if not isinstance(doc, dict) or "initialisers" not in doc:
        raise RuntimeError(
            f"{path}: expected a mapping with an 'initialisers' key"
        )
    return doc["initialisers"]


class Processor(AsyncProcessor):

    def __init__(self, **params):

        super().__init__(**params)

        # Source the initialisers list either from a direct parameter
        # (processor-group embedding) or from a file (CLI launch).
        inits = params.get("initialisers")
        if inits is None:
            inits_file = params.get("initialisers_file")
            if inits_file is None:
                raise RuntimeError(
                    "Bootstrapper requires either the 'initialisers' "
                    "parameter or --initialisers-file"
                )
            inits = _load_initialisers_file(inits_file)

        self.specs = []
        names = set()

        for entry in inits:
            if not isinstance(entry, dict):
                raise RuntimeError(
                    f"Initialiser entry must be a mapping, got: {entry!r}"
                )
            for required in ("class", "name", "flag"):
                if required not in entry:
                    raise RuntimeError(
                        f"Initialiser entry missing required field "
                        f"{required!r}: {entry!r}"
                    )

            name = entry["name"]
            if name in names:
                raise RuntimeError(f"Duplicate initialiser name {name!r}")
            names.add(name)

            cls = _resolve_class(entry["class"])

            try:
                instance = cls(**entry.get("params", {}))
            except Exception as e:
                raise RuntimeError(
                    f"Failed to instantiate initialiser "
                    f"{entry['class']!r} as {name!r}: "
                    f"{type(e).__name__}: {e}"
                )

            self.specs.append(InitialiserSpec(
                name=name,
                flag=entry["flag"],
                instance=instance,
            ))

        logger.info(
            f"Bootstrapper: loaded {len(self.specs)} initialisers"
        )

    # ------------------------------------------------------------------
    # Client construction (short-lived per wake cycle).
    # ------------------------------------------------------------------

    def _make_config_client(self):
        rr_id = str(uuid.uuid4())
        return ConfigClient(
            backend=self.pubsub_backend,
            subscription=f"{self.id}--config--{rr_id}",
            consumer_name=self.id,
            request_topic=config_request_queue,
            request_schema=ConfigRequest,
            request_metrics=ProducerMetrics(
                processor=self.id, flow=None, name="config-request",
            ),
            response_topic=config_response_queue,
            response_schema=ConfigResponse,
            response_metrics=SubscriberMetrics(
                processor=self.id, flow=None, name="config-response",
            ),
        )

    def _make_flow_client(self, workspace):
        rr_id = str(uuid.uuid4())
        return RequestResponse(
            backend=self.pubsub_backend,
            subscription=f"{self.id}--flow--{rr_id}",
            consumer_name=self.id,
            request_topic=f"{flow_request_queue}:{workspace}",
            request_schema=FlowRequest,
            request_metrics=ProducerMetrics(
                processor=self.id, flow=None, name="flow-request",
            ),
            response_topic=flow_response_queue,
            response_schema=FlowResponse,
            response_metrics=SubscriberMetrics(
                processor=self.id, flow=None, name="flow-response",
            ),
        )

    async def _open_clients(self):
        config = self._make_config_client()
        await config.start()
        return config

    async def _safe_stop(self, client):
        try:
            await client.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Service gate.
    # ------------------------------------------------------------------

    def _gate_workspace(self):
        for spec in self.specs:
            ws = getattr(spec.instance, "workspace", None)
            if ws and not ws.startswith("_"):
                return ws
        return None

    async def _gate_ready(self, config):
        try:
            await config.keys(SYSTEM_WORKSPACE, INIT_STATE_TYPE)
        except Exception as e:
            logger.info(
                f"Gate: config-svc not ready ({type(e).__name__}: {e})"
            )
            return False

        workspace = self._gate_workspace()
        if workspace is None:
            return True

        flow = self._make_flow_client(workspace)
        try:
            await flow.start()
            resp = await flow.request(
                FlowRequest(
                    operation="list-blueprints",
                ),
                timeout=5,
            )
            if resp.error:
                logger.info(
                    f"Gate: flow-svc error: "
                    f"{resp.error.type}: {resp.error.message}"
                )
                return False
        except Exception as e:
            logger.info(
                f"Gate: flow-svc not ready ({type(e).__name__}: {e})"
            )
            return False
        finally:
            await self._safe_stop(flow)

        return True

    # ------------------------------------------------------------------
    # Completion state.
    # ------------------------------------------------------------------

    async def _stored_flag(self, config, name):
        raw = await config.get(SYSTEM_WORKSPACE, INIT_STATE_TYPE, name)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return raw

    async def _store_flag(self, config, name, flag):
        await config.put(
            SYSTEM_WORKSPACE, INIT_STATE_TYPE, name,
            json.dumps(flag),
        )

    # ------------------------------------------------------------------
    # Per-spec execution.
    # ------------------------------------------------------------------

    async def _run_spec(self, spec, config):
        """Run a single initialiser spec.

        Returns one of:
          - ``"skip"``: stored flag already matches target, nothing to do.
          - ``"ran"``: initialiser ran and completion state was updated.
          - ``"failed"``: initialiser raised.
          - ``"failed-state-write"``: initialiser succeeded but we could
            not persist the new flag (transient — will re-run next cycle).
        """

        try:
            old_flag = await self._stored_flag(config, spec.name)
        except Exception as e:
            logger.warning(
                f"{spec.name}: could not read stored flag "
                f"({type(e).__name__}: {e})"
            )
            return "failed"

        if old_flag == spec.flag:
            return "skip"

        child_logger = logger.getChild(spec.name)
        child_ctx = InitContext(
            logger=child_logger,
            config=config,
            make_flow_client=self._make_flow_client,
        )

        child_logger.info(
            f"Running (old_flag={old_flag!r} -> new_flag={spec.flag!r})"
        )

        try:
            await spec.instance.run(child_ctx, old_flag, spec.flag)
        except Exception as e:
            child_logger.error(
                f"Failed: {type(e).__name__}: {e}", exc_info=True,
            )
            return "failed"

        try:
            await self._store_flag(config, spec.name, spec.flag)
        except Exception as e:
            child_logger.warning(
                f"Completed but could not persist state flag "
                f"({type(e).__name__}: {e}); will re-run next cycle"
            )
            return "failed-state-write"

        child_logger.info(f"Completed (flag={spec.flag!r})")
        return "ran"

    # ------------------------------------------------------------------
    # Main loop.
    # ------------------------------------------------------------------

    async def run(self):

        logger.info(
            f"Bootstrapper starting with {len(self.specs)} initialisers"
        )

        while self.running:

            sleep_for = STEADY_INTERVAL

            try:
                config = await self._open_clients()
            except Exception as e:
                logger.info(
                    f"Failed to open clients "
                    f"({type(e).__name__}: {e}); retry in {GATE_BACKOFF}s"
                )
                await asyncio.sleep(GATE_BACKOFF)
                continue

            try:
                # Phase 1: pre-service initialisers run unconditionally.
                pre_specs = [
                    s for s in self.specs
                    if not s.instance.wait_for_services
                ]
                pre_results = {}
                for spec in pre_specs:
                    pre_results[spec.name] = await self._run_spec(
                        spec, config,
                    )

                # Phase 2: gate.
                gate_ok = await self._gate_ready(config)

                # Phase 3: post-service initialisers, if gate passed.
                post_results = {}
                if gate_ok:
                    post_specs = [
                        s for s in self.specs
                        if s.instance.wait_for_services
                    ]
                    for spec in post_specs:
                        post_results[spec.name] = await self._run_spec(
                            spec, config,
                        )

                # Cadence selection.
                if not gate_ok:
                    sleep_for = GATE_BACKOFF
                else:
                    all_results = {**pre_results, **post_results}
                    if any(r != "skip" for r in all_results.values()):
                        sleep_for = INIT_RETRY
                    else:
                        sleep_for = STEADY_INTERVAL

            finally:
                await self._safe_stop(config)

            await asyncio.sleep(sleep_for)

    # ------------------------------------------------------------------
    # CLI arg plumbing.
    # ------------------------------------------------------------------

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        AsyncProcessor.add_args(parser)

        parser.add_argument(
            '-c', '--initialisers-file',
            help='Path to YAML or JSON file describing the '
                 'initialisers to run.  Ignored when the '
                 "'initialisers' parameter is provided directly "
                 '(e.g. when running inside a processor group).',
        )


def run():
    Processor.launch(default_ident, __doc__)
