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

    def __init__(self, backend):

        self.backend = backend

        self.flow_handlers = []

        self.flows = {}

        self.config_version = 0

    def add_handler(self, h):
        self.flow_handlers.append(h)

    async def on_config_notify(self, msg, proc, flow):

        try:

            v = msg.value()
            notify_version = v.version
            notify_types = set(v.types)

            # Skip if we already have this version or newer
            if notify_version <= self.config_version:
                logger.debug(
                    f"Ignoring config notify v{notify_version}, "
                    f"already at v{self.config_version}"
                )
                return

            # Gateway cares about flow config
            if notify_types and "flow" not in notify_types:
                logger.debug(
                    f"Ignoring config notify v{notify_version}, "
                    f"no flow types in {notify_types}"
                )
                self.config_version = notify_version
                return

            logger.info(
                f"Config notify v{notify_version}, fetching config..."
            )

            await self.fetch_and_apply()

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

    async def fetch_and_apply(self, retry=False):
        """Fetch full config and apply flow changes.
        If retry=True, keeps retrying until successful."""

        while True:

            try:
                logger.info("Fetching config from config service...")

                client = self._create_config_client()
                try:
                    await client.start()
                    resp = await client.request(
                        ConfigRequest(operation="config"),
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

                wanted = list(flows.keys())
                current = list(self.flows.keys())

                for k in wanted:
                    if k not in current:
                        self.flows[k] = json.loads(flows[k])
                        await self.start_flow(k, self.flows[k])

                for k in current:
                    if k not in wanted:
                        await self.stop_flow(k, self.flows[k])
                        del self.flows[k]

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

    async def start_flow(self, id, flow):

        logger.info(f"Starting flow: {id}")

        for handler in self.flow_handlers:

            try:
                await handler.start_flow(id, flow)
            except Exception as e:
                logger.error(
                    f"Config processing exception: {e}", exc_info=True
                )

    async def stop_flow(self, id, flow):

        logger.info(f"Stopping flow: {id}")

        for handler in self.flow_handlers:

            try:
                await handler.stop_flow(id, flow)
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
                    await self.fetch_and_apply(retry=True)

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
