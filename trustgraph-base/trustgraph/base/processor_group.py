
# Multi-processor group runner.  Runs multiple AsyncProcessor descendants
# as concurrent tasks inside a single process, sharing one event loop,
# one Prometheus HTTP server, and one pub/sub backend pool.
#
# Intended for dev and resource-constrained deployments.  Scale deployments
# should continue to use per-processor endpoints.
#
# Group config is a YAML or JSON file with shape:
#
#   processors:
#     - class: trustgraph.extract.kg.definitions.extract.Processor
#       params:
#         id: kg-extract-definitions
#         triples_batch_size: 1000
#     - class: trustgraph.chunking.recursive.Processor
#       params:
#         id: chunker-recursive
#
# Each entry's params are passed directly to the class constructor alongside
# the shared taskgroup.  Defaults live inside each processor class.

import argparse
import asyncio
import importlib
import json
import logging
import time

from prometheus_client import start_http_server

from . logging import add_logging_args, setup_logging, set_processor_id

logger = logging.getLogger(__name__)


def _load_config(path):
    with open(path) as f:
        text = f.read()
    if path.endswith((".yaml", ".yml")):
        import yaml
        return yaml.safe_load(text)
    return json.loads(text)


def _resolve_class(dotted):
    module_path, _, class_name = dotted.rpartition(".")
    if not module_path:
        raise ValueError(
            f"Processor class must be a dotted path, got {dotted!r}"
        )
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


RESTART_DELAY_SECONDS = 4


async def _supervise(entry):
    """Run one processor with its own nested TaskGroup, restarting on any
    failure.  Each processor is isolated from its siblings — a crash here
    does not propagate to the outer group."""

    pid = entry["params"]["id"]
    class_path = entry["class"]

    # Stamp the contextvar for this supervisor task.  Every log
    # record emitted from this task — and from any inner TaskGroup
    # child created by the processor — inherits this id via
    # contextvar propagation.  Siblings in the outer group set
    # their own id in their own task context and do not interfere.
    set_processor_id(pid)

    while True:

        try:

            async with asyncio.TaskGroup() as inner_tg:

                cls = _resolve_class(class_path)
                params = dict(entry.get("params", {}))
                params["taskgroup"] = inner_tg

                logger.info(f"Starting {class_path} as {pid}")

                p = cls(**params)
                await p.start()
                inner_tg.create_task(p.run())

            # Clean exit — processor's run() returned without raising.
            # Treat as a transient shutdown and restart, matching the
            # behaviour of per-container `restart: on-failure`.
            logger.warning(
                f"Processor {pid} exited cleanly, will restart"
            )

        except asyncio.CancelledError:
            logger.info(f"Processor {pid} cancelled")
            raise

        except BaseExceptionGroup as eg:
            for e in eg.exceptions:
                logger.error(
                    f"Processor {pid} failure: {type(e).__name__}: {e}",
                    exc_info=e,
                )

        except Exception as e:
            logger.error(
                f"Processor {pid} failure: {type(e).__name__}: {e}",
                exc_info=True,
            )

        logger.info(
            f"Restarting {pid} in {RESTART_DELAY_SECONDS}s..."
        )
        await asyncio.sleep(RESTART_DELAY_SECONDS)


async def run_group(config):

    entries = config.get("processors", [])
    if not entries:
        raise RuntimeError("Group config has no processors")

    seen_ids = set()
    for entry in entries:
        pid = entry.get("params", {}).get("id")
        if pid is None:
            raise RuntimeError(
                f"Entry {entry.get('class')!r} missing params.id — "
                f"required for metrics labelling"
            )
        if pid in seen_ids:
            raise RuntimeError(f"Duplicate processor id {pid!r} in group")
        seen_ids.add(pid)

    async with asyncio.TaskGroup() as outer_tg:
        for entry in entries:
            outer_tg.create_task(_supervise(entry))


def run():

    parser = argparse.ArgumentParser(
        prog="processor-group",
        description="Run multiple processors as tasks in one process",
    )

    parser.add_argument(
        "-c", "--config",
        required=True,
        help="Path to group config file (JSON or YAML)",
    )

    parser.add_argument(
        "--metrics",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Metrics enabled (default: true)",
    )

    parser.add_argument(
        "-P", "--metrics-port",
        type=int,
        default=8000,
        help="Prometheus metrics port (default: 8000)",
    )

    add_logging_args(parser)

    args = vars(parser.parse_args())

    setup_logging(args)

    config = _load_config(args["config"])

    if args["metrics"]:
        start_http_server(args["metrics_port"])

    while True:

        logger.info("Starting group...")

        try:
            asyncio.run(run_group(config))

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt.")
            return

        except ExceptionGroup as e:
            logger.error("Exception group:")
            for se in e.exceptions:
                logger.error(f"  Type: {type(se)}")
                logger.error(f"  Exception: {se}", exc_info=se)

        except Exception as e:
            logger.error(f"Type: {type(e)}")
            logger.error(f"Exception: {e}", exc_info=True)

        logger.warning("Will retry...")
        time.sleep(4)
        logger.info("Retrying...")
