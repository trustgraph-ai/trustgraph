"""
API gateway config receiver.  Subscribes to config notify notifications and
fetches full config via request/response to manage flow lifecycle.
"""

module = "api-gateway"

import asyncio
import uuid
import logging
import json
from prometheus_client import Gauge

from ... schema import ConfigPush, ConfigRequest, ConfigResponse
from ... schema import config_push_queue, config_request_queue
from ... schema import config_response_queue
from ... base.request_response_client import RequestResponseClient

logger = logging.getLogger("config.receiver")
logger.setLevel(logging.INFO)


_flow_count_gauge = Gauge(
    'tg_gateway_active_flow_count',
    'Number of active flows tracked by the gateway',
)


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

    async def on_config_notify(self, msg):

        try:

            v = msg.value()
            notify_version = v.version
            changes = v.changes

            if notify_version <= self.config_version:
                logger.debug(
                    f"Ignoring config notify v{notify_version}, "
                    f"already at v{self.config_version}"
                )
                return

            if v.workspace_changes and self.auth:
                for ws in (v.workspace_changes.created or []):
                    self.auth.known_workspaces.add(ws)
                    logger.info(f"Workspace registered: {ws}")
                for ws in (v.workspace_changes.deleted or []):
                    self.auth.known_workspaces.discard(ws)
                    logger.info(f"Workspace deregistered: {ws}")
                from ..auth import IamAuth
                if hasattr(IamAuth, 'known_workspaces_metric'):
                    IamAuth.known_workspaces_metric.set(
                        len(self.auth.known_workspaces),
                    )

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

            for workspace in flow_workspaces:
                await self.fetch_and_apply_workspace(workspace)

            self.config_version = notify_version

        except Exception as e:
            logger.error(
                f"Config notify processing exception: {e}", exc_info=True
            )

    async def _create_config_client(self):
        return await RequestResponseClient.create(
            backend=self.backend,
            request_topic=config_request_queue,
            response_topic=config_response_queue,
            request_schema=ConfigRequest,
            response_schema=ConfigResponse,
        )

    async def fetch_and_apply_workspace(self, workspace, retry=False):

        while True:

            try:
                logger.info(
                    f"Fetching config for workspace {workspace}..."
                )

                client = await self._create_config_client()
                try:
                    resp = await client.request(
                        ConfigRequest(
                            operation="config",
                            workspace=workspace,
                        ),
                        timeout=10,
                    )
                finally:
                    await client.close()

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

                _flow_count_gauge.set(
                    sum(len(v) for v in self.flows.values())
                )

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

        while True:

            try:
                logger.info("Discovering workspaces with flows...")

                client = await self._create_config_client()
                try:

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
                        from ..auth import IamAuth
                        if hasattr(IamAuth, 'known_workspaces_metric'):
                            IamAuth.known_workspaces_metric.set(
                                len(discovered),
                            )

                    logger.info(
                        f"Known workspaces: {discovered}"
                    )

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

                    workspaces.add("default")

                    logger.info(
                        f"Found workspaces with flows: {workspaces}"
                    )

                finally:
                    await client.close()

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

            consumer = None

            try:

                consumer = await self.backend.create_consumer(
                    topic=config_push_queue,
                    subscription=f"gateway-{uuid.uuid4()}",
                    schema=ConfigPush,
                    initial_position='latest',
                )

                logger.info("Config notify consumer started")

                await self.fetch_all_workspaces(retry=True)

                logger.info(
                    "Config loader initialised, waiting for notifys..."
                )

                while True:
                    msg = await consumer.receive()
                    try:
                        await self.on_config_notify(msg)
                        await consumer.acknowledge(msg)
                    except Exception as e:
                        logger.error(
                            f"Config notify error: {e}", exc_info=True
                        )
                        await consumer.negative_acknowledge(msg)

            except Exception as e:
                logger.error(
                    f"Config loader exception: {e}, restarting in 4s...",
                    exc_info=True
                )

            finally:
                if consumer:
                    try:
                        await consumer.close()
                    except BaseException:
                        pass

            await asyncio.sleep(4)

    async def start(self):

        asyncio.create_task(self.config_loader())
