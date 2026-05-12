"""
API gateway config receiver.  Subscribes to config notify notifications and
fetches full config via request/response to manage flow lifecycle.
"""

module = "api-gateway"

import asyncio
import uuid
import logging
import json

from ... schema import ConfigPush, ConfigRequest, ConfigResponse
from ... schema import config_push_queue, config_request_queue
from ... schema import config_response_queue
from ... base import Consumer, Producer
from ... base.subscriber import Subscriber
from ... base.request_response_spec import RequestResponse
from ... base.metrics import ProducerMetrics, SubscriberMetrics

logger = logging.getLogger("config.receiver")
logger.setLevel(logging.INFO)


class ConfigReceiver:

    def __init__(self, backend, auth=None):

        self.backend = backend
        self.auth = auth

        self.flow_handlers = []

        # Per-workspace flow tracking: {workspace: {flow_id: flow_def}}
        self.flows = {}

        self.config_version = 0

    def add_handler(self, h):
        self.flow_handlers.append(h)

    async def on_config_notify(self, msg, proc, flow):

        try:

            v = msg.value()
            notify_version = v.version
            changes = v.changes

            # Skip if we already have this version or newer
            if notify_version <= self.config_version:
                logger.debug(
                    f"Ignoring config notify v{notify_version}, "
                    f"already at v{self.config_version}"
                )
                return

            # Track workspace lifecycle
            if v.workspace_changes and self.auth:
                for ws in (v.workspace_changes.created or []):
                    self.auth.known_workspaces.add(ws)
                    logger.info(f"Workspace registered: {ws}")
                for ws in (v.workspace_changes.deleted or []):
                    self.auth.known_workspaces.discard(ws)
                    logger.info(f"Workspace deregistered: {ws}")

            # Gateway cares about flow config — check if any flow
            # types changed in any workspace
            flow_workspaces = changes.get("flow", [])
            if changes and not flow_workspaces:
                logger.debug(
                    f"Ignoring config notify v{notify_version}, "
                    f"no flow changes"
                )
                self.config_version = notify_version
                return

            logger.info(
                f"Config notify v{notify_version} "
                f"types={list(changes.keys())}, fetching config..."
            )

            # Refresh config for each affected workspace
            for workspace in flow_workspaces:
                await self.fetch_and_apply_workspace(workspace)

            self.config_version = notify_version

        except Exception as e:
            logger.error(
                f"Config notify processing exception: {e}", exc_info=True
            )

    def _create_config_client(self):
        """Create a short-lived config request/response client."""
        id = str(uuid.uuid4())

        config_req_metrics = ProducerMetrics(
            processor="api-gateway", flow=None,
            name="config-request",
        )
        config_resp_metrics = SubscriberMetrics(
            processor="api-gateway", flow=None,
            name="config-response",
        )

        return RequestResponse(
            backend=self.backend,
            subscription=f"api-gateway--config--{id}",
            consumer_name="api-gateway",
            request_topic=config_request_queue,
            request_schema=ConfigRequest,
            request_metrics=config_req_metrics,
            response_topic=config_response_queue,
            response_schema=ConfigResponse,
            response_metrics=config_resp_metrics,
        )

    async def fetch_and_apply_workspace(self, workspace, retry=False):
        """Fetch config for a single workspace and apply flow changes.
        If retry=True, keeps retrying until successful."""

        while True:

            try:
                logger.info(
                    f"Fetching config for workspace {workspace}..."
                )

                client = self._create_config_client()
                try:
                    await client.start()
                    resp = await client.request(
                        ConfigRequest(
                            operation="config",
                            workspace=workspace,
                        ),
                        timeout=10,
                    )
                finally:
                    await client.stop()

                logger.info(f"Config response received")

                if resp.error:
                    if retry:
                        logger.warning(
                            f"Config fetch error: {resp.error.message}, "
                            f"retrying in 2s..."
                        )
                        await asyncio.sleep(2)
                        continue
                    logger.error(
                        f"Config fetch error: {resp.error.message}"
                    )
                    return

                self.config_version = resp.version
                config = resp.config

                flows = config.get("flow", {})

                ws_flows = self.flows.get(workspace, {})

                wanted = list(flows.keys())
                current = list(ws_flows.keys())

                for k in wanted:
                    if k not in current:
                        ws_flows[k] = json.loads(flows[k])
                        await self.start_flow(workspace, k, ws_flows[k])

                for k in current:
                    if k not in wanted:
                        await self.stop_flow(workspace, k, ws_flows[k])
                        del ws_flows[k]

                self.flows[workspace] = ws_flows

                return

            except Exception as e:
                if retry:
                    logger.warning(
                        f"Config fetch failed: {e}, retrying in 2s..."
                    )
                    await asyncio.sleep(2)
                    continue
                logger.error(
                    f"Config fetch exception: {e}", exc_info=True
                )
                return

    async def fetch_all_workspaces(self, retry=False):
        """Fetch config for all workspaces at startup.
        Discovers workspaces via the config service getvalues-all-ws
        operation on the flow type."""

        while True:

            try:
                logger.info("Discovering workspaces with flows...")

                client = self._create_config_client()
                try:
                    await client.start()

                    # Discover all known workspaces
                    ws_resp = await client.request(
                        ConfigRequest(
                            operation="getvalues",
                            workspace="__workspaces__",
                            type="workspace",
                        ),
                        timeout=10,
                    )

                    if ws_resp.error:
                        raise RuntimeError(
                            f"Workspace discovery error: "
                            f"{ws_resp.error.message}"
                        )

                    discovered = {
                        v.key for v in ws_resp.values if v.key
                    }

                    if self.auth:
                        self.auth.known_workspaces = discovered

                    logger.info(
                        f"Known workspaces: {discovered}"
                    )

                    # Discover workspaces that have any flow config
                    resp = await client.request(
                        ConfigRequest(
                            operation="getvalues-all-ws",
                            type="flow",
                        ),
                        timeout=10,
                    )

                    if resp.error:
                        raise RuntimeError(
                            f"Config error: {resp.error.message}"
                        )

                    workspaces = {
                        v.workspace for v in resp.values if v.workspace
                    }

                    # Always include the default workspace, even if
                    # empty, so that newly-created flows in it can be
                    # picked up by subsequent notifications.
                    workspaces.add("default")

                    logger.info(
                        f"Found workspaces with flows: {workspaces}"
                    )

                finally:
                    await client.stop()

                # Fetch and apply config for each workspace
                for workspace in workspaces:
                    await self.fetch_and_apply_workspace(
                        workspace, retry=retry
                    )

                return

            except Exception as e:
                if retry:
                    logger.warning(
                        f"Workspace fetch failed: {e}, retrying in 2s..."
                    )
                    await asyncio.sleep(2)
                    continue
                logger.error(
                    f"Workspace fetch exception: {e}", exc_info=True
                )
                return

    async def start_flow(self, workspace, id, flow):

        logger.info(f"Starting flow: {workspace}/{id}")

        for handler in self.flow_handlers:

            try:
                await handler.start_flow(workspace, id, flow)
            except Exception as e:
                logger.error(
                    f"Config processing exception: {e}", exc_info=True
                )

    async def stop_flow(self, workspace, id, flow):

        logger.info(f"Stopping flow: {workspace}/{id}")

        for handler in self.flow_handlers:

            try:
                await handler.stop_flow(workspace, id, flow)
            except Exception as e:
                logger.error(
                    f"Config processing exception: {e}", exc_info=True
                )

    async def config_loader(self):

        while True:

            try:

                async with asyncio.TaskGroup() as tg:

                    id = str(uuid.uuid4())

                    # Subscribe to notify queue
                    self.config_cons = Consumer(
                        taskgroup=tg,
                        flow=None,
                        backend=self.backend,
                        subscriber=f"gateway-{id}",
                        topic=config_push_queue,
                        schema=ConfigPush,
                        handler=self.on_config_notify,
                        start_of_messages=False,
                    )

                    logger.info("Starting config notify consumer...")
                    await self.config_cons.start()
                    logger.info("Config notify consumer started")

                    # Fetch current config (subscribe-then-fetch pattern)
                    # Retry until config service is available
                    await self.fetch_all_workspaces(retry=True)

                    logger.info(
                        "Config loader initialised, waiting for notifys..."
                    )

                logger.warning("Config consumer exited, restarting...")

            except Exception as e:
                logger.error(
                    f"Config loader exception: {e}, restarting in 4s...",
                    exc_info=True
                )

            await asyncio.sleep(4)

    async def start(self):

        asyncio.create_task(self.config_loader())
