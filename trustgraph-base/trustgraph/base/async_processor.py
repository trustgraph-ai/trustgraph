from __future__ import annotations

from argparse import ArgumentParser
from typing import Any, Callable

# Base class for processors.  Implements:
# - Pub/sub client, subscribe and consume basic
# - the async startup logic
# - Config notify handling with subscribe-then-fetch pattern
# - Initialising metrics

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
from . pubsub import get_pubsub, add_pubsub_args
from . producer import Producer
from . consumer import Consumer
from . subscriber import Subscriber
from . request_response_spec import RequestResponse
from . metrics import ProcessorMetrics, ConsumerMetrics, ProducerMetrics
from . metrics import SubscriberMetrics
from . logging import add_logging_args, setup_logging

default_config_queue = config_push_queue

# Module logger
logger = logging.getLogger(__name__)

# Async processor
class AsyncProcessor:

    def __init__(self, **params):

        # Store the identity
        self.id = params.get("id")

        # Create pub/sub backend via factory
        self.pubsub_backend = get_pubsub(**params)

        # Store pulsar_host for backward compatibility
        self._pulsar_host = params.get("pulsar_host", "pulsar://pulsar:6650")

        # Initialise metrics, records the parameters
        ProcessorMetrics(processor = self.id).info({
            k: str(params[k])
            for k in params
            if k != "id"
        })

        # The processor runs all activity in a taskgroup, it's mandatory
        # that this is provded
        self.taskgroup = params.get("taskgroup")
        if self.taskgroup is None:
            raise RuntimeError("Essential taskgroup missing")

        # Get the configuration topic
        self.config_push_queue = params.get(
            "config_push_queue", default_config_queue
        )

        # This records registered configuration handlers, each entry is:
        # { "handler": async_fn, "types": set_or_none }
        self.config_handlers = []

        # Track the current config version for dedup
        self.config_version = 0

        # Create a random ID for this subscription to the configuration
        # service
        config_subscriber_id = str(uuid.uuid4())

        config_consumer_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "config",
        )

        # Subscribe to config notify queue
        self.config_sub_task = Consumer(

            taskgroup = self.taskgroup,
            backend = self.pubsub_backend,
            subscriber = config_subscriber_id,
            flow = None,

            topic = self.config_push_queue,
            schema = ConfigPush,

            handler = self.on_config_notify,

            metrics = config_consumer_metrics,

            start_of_messages = False,
        )

        self.running = True

    def _create_config_client(self):
        """Create a short-lived config request/response client."""
        config_rr_id = str(uuid.uuid4())

        config_req_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "config-request",
        )
        config_resp_metrics = SubscriberMetrics(
            processor = self.id, flow = None, name = "config-response",
        )

        return RequestResponse(
            backend = self.pubsub_backend,
            subscription = f"{self.id}--config--{config_rr_id}",
            consumer_name = self.id,
            request_topic = config_request_queue,
            request_schema = ConfigRequest,
            request_metrics = config_req_metrics,
            response_topic = config_response_queue,
            response_schema = ConfigResponse,
            response_metrics = config_resp_metrics,
        )

    async def _fetch_type_workspace(self, client, workspace, config_type):
        """Fetch config values of a single type within one workspace.
        Returns dict of {key: value}."""
        resp = await client.request(
            ConfigRequest(
                operation="getvalues",
                workspace=workspace,
                type=config_type,
            ),
            timeout=10,
        )
        if resp.error:
            raise RuntimeError(f"Config error: {resp.error.message}")
        return {v.key: v.value for v in resp.values}

    async def _fetch_type_all_workspaces(self, client, config_type):
        """Fetch config values of a single type across all workspaces.
        Returns dict of {workspace: {key: value}}."""
        resp = await client.request(
            ConfigRequest(
                operation="getvalues-all-ws",
                type=config_type,
            ),
            timeout=10,
        )
        if resp.error:
            raise RuntimeError(f"Config error: {resp.error.message}")

        grouped = {}
        for v in resp.values:
            ws = grouped.setdefault(v.workspace, {})
            ws[v.key] = v.value
        return grouped, resp.version

    # This is called to start dynamic behaviour.
    # Implements the subscribe-then-fetch pattern to avoid race conditions.
    async def start(self):

        # 1. Start the notify consumer (begins buffering incoming notifys)
        await self.config_sub_task.start()

        # 2. Fetch current config via request/response
        await self.fetch_and_apply_config()

        # 3. Any buffered notifys with version > fetched version will be
        #    processed by on_config_notify, which does the version check

    async def fetch_and_apply_config(self):
        """Startup: for each registered handler, fetch config for all its
        types across all workspaces and invoke the handler once per
        workspace. Retries until successful — config service may not be
        ready yet."""

        while self.running:

            try:
                client = self._create_config_client()
                try:
                    await client.start()

                    version = 0

                    for entry in self.config_handlers:
                        handler_types = entry["types"]

                        # Handlers registered without types get nothing
                        # at startup (there is no "all types" fetch).
                        if not handler_types:
                            continue

                        # Group all registered types by workspace:
                        # {workspace: {type: {key: value}}}
                        per_ws = {}
                        for t in handler_types:
                            type_data, v = \
                                await self._fetch_type_all_workspaces(
                                    client, t,
                                )
                            version = max(version, v)
                            for ws, kv in type_data.items():
                                per_ws.setdefault(ws, {})[t] = kv

                        # Call the handler once per workspace
                        for ws, config in per_ws.items():
                            await entry["handler"](ws, config, version)

                    logger.info(
                        f"Applied startup config version {version}"
                    )
                    self.config_version = version

                finally:
                    await client.stop()

                return

            except Exception as e:
                logger.warning(
                    f"Config fetch failed: {e}, retrying in 2s...",
                    exc_info=True
                )
                await asyncio.sleep(2)

    # This is called to stop all threads.  An over-ride point for extra
    # functionality
    def stop(self) -> None:
        self.pubsub_backend.close()
        self.running = False

    # Returns the pub/sub backend (new interface)
    @property
    def pubsub(self) -> Any: return self.pubsub_backend

    # Returns the pulsar host (backward compatibility)
    @property
    def pulsar_host(self) -> str: return self._pulsar_host

    # Register a new event handler for configuration change
    def register_config_handler(self, handler: Callable[..., Any], types: list[type] | None = None) -> None:
        self.config_handlers.append({
            "handler": handler,
            "types": set(types) if types else None,
        })

    # Called when a config notify message arrives
    async def on_config_notify(self, message, consumer, flow):

        v = message.value()
        notify_version = v.version
        changes = v.changes  # dict of type -> [workspaces]

        # Skip if we already have this version or newer
        if notify_version <= self.config_version:
            logger.debug(
                f"Ignoring config notify v{notify_version}, "
                f"already at v{self.config_version}"
            )
            return

        notify_types = set(changes.keys())

        # Filter out handlers that don't care about any of the changed
        # types. A handler registered without types never fires on
        # notifications (nothing to scope to).
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
            client = self._create_config_client()
            try:
                await client.start()

                for entry in interested:
                    handler_types = entry["types"]

                    # Build {workspace: {type: {key: value}}} for types
                    # this handler cares about, where the workspace was
                    # affected for that type.
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
                        await entry["handler"](
                            ws, config, notify_version,
                        )

            finally:
                await client.stop()

            self.config_version = notify_version

        except Exception as e:
            logger.error(
                f"Failed to fetch config on notify: {e}", exc_info=True
            )

    # This is the 'main' body of the handler.  It is a point to override
    # if needed.  By default does nothing.  Processors are implemented
    # by adding consumer/producer functionality so maybe nothing is needed
    # in the run() body
    async def run(self):
        while self.running:
            await asyncio.sleep(2)

    # Startup fabric.  This runs in 'async' mode, creates a taskgroup and
    # runs the producer.
    @classmethod
    async def launch_async(cls, args):

        try:

            # Create a taskgroup.  This seems complicated, when an exception
            # occurs, unhandled it looks like it cancels all threads in the
            # taskgroup.  Needs the exception to be caught in the right
            # place.
            async with asyncio.TaskGroup() as tg:


                    # Create a processor instance, and include the taskgroup
                    # as a paramter.  A processor identity ident is used as
                    # - subscriber name
                    # - an identifier for flow configuration
                    p = cls(**args | { "taskgroup": tg })

                    # Start the processor
                    await p.start()

                    # Run the processor
                    task = tg.create_task(p.run())

                    # The taskgroup causes everything to wait until
                    # all threads have stopped

        # This is here to output a debug message, shouldn't be needed.
        except Exception as e:
            logger.error("Exception, closing taskgroup", exc_info=True)
            raise e

    @classmethod
    def setup_logging(cls, args: dict[str, Any]) -> None:
        """Configure logging for the entire application"""
        setup_logging(args)

    # Startup fabric.  launch calls launch_async in async mode.
    @classmethod
    def launch(cls, ident: str, doc: str) -> None:

        # Start assembling CLI arguments
        parser = argparse.ArgumentParser(
            prog=ident,
            description=doc
        )

        parser.add_argument(
            '--id',
            default=ident,
            help=f'Configuration identity (default: {ident})',
        )

        # Invoke the class-specific add_args, which manages adding all the
        # command-line arguments
        cls.add_args(parser)

        # Parse arguments
        args = parser.parse_args()
        args = vars(args)

        # Setup logging before anything else
        cls.setup_logging(args)

        # Debug
        logger.debug(f"Arguments: {args}")

        # Start the Prometheus metrics service if needed
        if args["metrics"]:
            start_http_server(args["metrics_port"])

        # Loop forever, exception handler
        while True:

            logger.info("Starting...")

            try:

                # Launch the processor in an asyncio handler
                asyncio.run(cls.launch_async(
                    args
                ))

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt.")
                return

            except KeyboardInterrupt:
                logger.info("Interrupted.")
                return

            # Exceptions from a taskgroup come in as an exception group
            except ExceptionGroup as e:

                logger.error("Exception group:")

                for se in e.exceptions:
                    logger.error(f"  Type: {type(se)}")
                    logger.error(f"  Exception: {se}", exc_info=se)

            except Exception as e:
                logger.error(f"Type: {type(e)}")
                logger.error(f"Exception: {e}", exc_info=True)

            # Retry occurs here
            logger.warning("Will retry...")
            time.sleep(4)
            logger.info("Retrying...")

    # The command-line arguments are built using a stack of add_args
    # invocations
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
            '--metrics',
            action=argparse.BooleanOptionalAction,
            default=True,
            help=f'Metrics enabled (default: true)',
        )

        parser.add_argument(
            '-P', '--metrics-port',
            type=int,
            default=8000,
            help=f'Pulsar host (default: 8000)',
        )
