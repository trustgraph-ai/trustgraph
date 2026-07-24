from __future__ import annotations

from argparse import ArgumentParser
from typing import Any, Callable

import asyncio
import argparse
import time
import uuid
import logging
import os
from prometheus_client import start_http_server, Info

from .. schema import ConfigPush, ConfigRequest, ConfigResponse
from .. schema import config_push_queue, config_request_queue
from .. schema import config_response_queue
from .. log_level import LogLevel
from . pubsub import get_async_pubsub, add_pubsub_args
from . receiver_pool import ReceiverPool
from . sender_pool import SenderPool
from . request_response_client import RequestResponseClient
from . logging import add_logging_args, setup_logging

default_config_queue = config_push_queue

logger = logging.getLogger(__name__)


class AsyncProcessor:

    def __init__(self, **params):

        self.id = params.get("id")

        self.async_backend = get_async_pubsub(**params)

        self._pulsar_host = params.get("pulsar_host", "pulsar://pulsar:6650")

        from . metrics import ProcessorMetrics
        ProcessorMetrics(processor = self.id).info({
            k: str(params[k])
            for k in params
            if k != "id"
        })

        self.taskgroup = params.get("taskgroup")

        self.concurrency = params.get("concurrency", 1)

        self.receiver_pool = ReceiverPool(
            backend=self.async_backend,
            concurrency=self.concurrency,
        )

        self.sender_pool = SenderPool(
            backend=self.async_backend,
        )

        self.config_push_queue = params.get(
            "config_push_queue", default_config_queue
        )

        self.config_handlers = []
        self.workspace_handlers = []
        self.config_version = 0

        self._config_consumer_reg = None

        self.running = True

    @property
    def pubsub(self) -> Any:
        return self.async_backend

    @property
    def pulsar_host(self) -> str:
        return self._pulsar_host

    async def _create_config_client(self):
        return await RequestResponseClient.create(
            backend=self.async_backend,
            request_topic=config_request_queue,
            response_topic=config_response_queue,
            request_schema=ConfigRequest,
            response_schema=ConfigResponse,
        )

    async def _fetch_type_workspace(self, client, workspace, config_type):
        resp = await client.request(
            ConfigRequest(
                operation="getvalues",
                workspace=workspace,
                type=config_type,
            ),
            timeout=60,
        )
        if resp.error:
            raise RuntimeError(f"Config error: {resp.error.message}")
        return {v.key: v.value for v in resp.values}

    async def _fetch_type_all_workspaces(self, client, config_type):
        resp = await client.request(
            ConfigRequest(
                operation="getkeys-all-ws",
                type=config_type,
            ),
            timeout=60,
        )
        if resp.error:
            raise RuntimeError(f"Config error: {resp.error.message}")

        version = resp.version

        workspaces = set()
        for v in resp.values:
            workspaces.add(v.workspace)

        async def fetch_one(ws):
            kv = await self._fetch_type_workspace(client, ws, config_type)
            return ws, kv

        results = await asyncio.gather(
            *(fetch_one(ws) for ws in workspaces),
            return_exceptions=True,
        )

        grouped = {}
        for result in results:
            if isinstance(result, Exception):
                raise result
            ws, kv = result
            if kv:
                grouped[ws] = kv

        return grouped, version

    async def start(self):

        await self.receiver_pool.start()
        await self.sender_pool.start()

        config_subscriber_id = str(uuid.uuid4())

        async def config_notify_handler(message):
            await self.on_config_notify(message, None, None)

        self._config_consumer_reg = \
            await self.receiver_pool.add_consumer(
                topic=self.config_push_queue,
                subscription=config_subscriber_id,
                schema=ConfigPush,
                handler=config_notify_handler,
                initial_position='latest',
            )

        await self.fetch_and_apply_config()

    async def fetch_and_apply_config(self):

        applied_ws = set()

        while self.running:

            try:
                client = await self._create_config_client()
                try:

                    version = 0

                    for entry in self.config_handlers:
                        handler_types = entry["types"]

                        if not handler_types:
                            continue

                        per_ws = {}
                        for t in handler_types:
                            type_data, v = \
                                await self._fetch_type_all_workspaces(
                                    client, t,
                                )
                            version = max(version, v)
                            for ws, kv in type_data.items():
                                per_ws.setdefault(ws, {})[t] = kv

                        for ws, config in per_ws.items():
                            if ws.startswith("_"):
                                continue
                            if ws in applied_ws:
                                continue
                            await entry["handler"](ws, config, version)
                            applied_ws.add(ws)

                    logger.info(
                        f"Applied startup config version {version}"
                    )
                    self.config_version = version

                finally:
                    await client.close()

                return

            except Exception as e:
                logger.warning(
                    f"Config fetch failed: {e}, retrying in 2s...",
                    exc_info=True
                )
                await asyncio.sleep(2)

    async def stop(self):
        self.running = False

        if self._config_consumer_reg:
            await self._config_consumer_reg.unregister()

        await self.receiver_pool.stop()
        await self.sender_pool.stop()
        await self.async_backend.close()

    def register_config_handler(
        self, handler: Callable[..., Any],
        types: list[type] | None = None,
    ) -> None:
        self.config_handlers.append({
            "handler": handler,
            "types": set(types) if types else None,
        })

    def register_workspace_handler(
        self, handler: Callable[..., Any],
    ) -> None:
        self.workspace_handlers.append(handler)

    async def on_config_notify(self, message, consumer, flow):

        v = message.value()
        notify_version = v.version
        changes = v.changes

        if notify_version <= self.config_version:
            logger.debug(
                f"Ignoring config notify v{notify_version}, "
                f"already at v{self.config_version}"
            )
            return

        if v.workspace_changes and self.workspace_handlers:
            for handler in self.workspace_handlers:
                try:
                    await handler(v.workspace_changes)
                except Exception as e:
                    logger.error(
                        f"Workspace handler failed: {e}", exc_info=True
                    )

        notify_types = set(changes.keys())

        interested = []
        for entry in self.config_handlers:
            handler_types = entry["types"]
            if handler_types and notify_types & handler_types:
                interested.append(entry)

        if not interested:
            logger.debug(
                f"Ignoring config notify v{notify_version}, "
                f"no handlers for types {notify_types}"
            )
            self.config_version = notify_version
            return

        logger.info(
            f"Config notify v{notify_version} "
            f"types={list(notify_types)}, fetching config..."
        )

        try:
            client = await self._create_config_client()
            try:

                for entry in interested:
                    handler_types = entry["types"]

                    per_ws = {}
                    for t in handler_types:
                        if t not in changes:
                            continue
                        for ws in changes[t]:
                            kv = await self._fetch_type_workspace(
                                client, ws, t,
                            )
                            per_ws.setdefault(ws, {})[t] = kv

                    for ws, config in per_ws.items():
                        if ws.startswith("_"):
                            continue
                        await entry["handler"](
                            ws, config, notify_version,
                        )

            finally:
                await client.close()

            self.config_version = notify_version

        except Exception as e:
            logger.error(
                f"Failed to fetch config on notify: {e}", exc_info=True
            )

    async def run(self):
        while self.running:
            await asyncio.sleep(2)

    @classmethod
    async def launch_async(cls, args):

        p = None

        try:

            async with asyncio.TaskGroup() as tg:

                p = cls(**args | {"taskgroup": tg})

                await p.start()

                task = tg.create_task(p.run())

        except ExceptionGroup as e:

            logger.error("Exception group:")

            for se in e.exceptions:
                logger.error(f"  Type: {type(se)}")
                logger.error(f"  Exception: {se}", exc_info=se)

        except Exception as e:
            logger.error("Exception in processor", exc_info=True)
            raise e

        finally:
            if p:
                try:
                    await p.stop()
                except Exception:
                    pass

    @classmethod
    def setup_logging(cls, args: dict[str, Any]) -> None:
        setup_logging(args)

    @classmethod
    def launch(cls, ident: str, doc: str) -> None:

        parser = argparse.ArgumentParser(
            prog=ident,
            description=doc
        )

        parser.add_argument(
            '--id',
            default=ident,
            help=f'Configuration identity (default: {ident})',
        )

        cls.add_args(parser)

        args = parser.parse_args()
        args = vars(args)

        cls.setup_logging(args)

        logger.debug(f"Arguments: {args}")

        if args["metrics"]:
            start_http_server(args["metrics_port"])

        while True:

            logger.info("Starting...")

            try:

                asyncio.run(cls.launch_async(
                    args
                ))

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt.")
                return

            except Exception as e:
                logger.error(f"Type: {type(e)}")
                logger.error(f"Exception: {e}", exc_info=True)

            logger.warning("Will retry...")
            time.sleep(4)
            logger.info("Retrying...")

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        add_pubsub_args(parser)
        add_logging_args(parser)

        parser.add_argument(
            '--config-push-queue',
            default=default_config_queue,
            help=f'Config push queue (default: {default_config_queue})',
        )

        parser.add_argument(
            '--concurrency',
            type=int,
            default=1,
            help='Number of concurrent workers (default: 1)',
        )

        parser.add_argument(
            '--metrics',
            action=argparse.BooleanOptionalAction,
            default=True,
            help=f'Metrics enabled (default: true)',
        )

        parser.add_argument(
            '-P', '--metrics-port',
            type=int,
            default=8000,
            help=f'Metrics port (default: 8000)',
        )
