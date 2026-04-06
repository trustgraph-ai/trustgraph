
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
            consumer_type = 'exclusive',
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

    async def fetch_config(self):
        """Fetch full config from config service using a short-lived
        request/response client. Returns (config, version) or raises."""
        client = self._create_config_client()
        try:
            await client.start()
            resp = await client.request(
                ConfigRequest(operation="config"),
                timeout=10,
            )
            if resp.error:
                raise RuntimeError(f"Config error: {resp.error.message}")
            return resp.config, resp.version
        finally:
            await client.stop()

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
        """Fetch full config from config service and apply to all handlers.
        Retries until successful — config service may not be ready yet."""

        while self.running:

            try:
                config, version = await self.fetch_config()

                logger.info(f"Fetched config version {version}")

                self.config_version = version

                # Apply to all handlers (startup = invoke all)
                for entry in self.config_handlers:
                    await entry["handler"](config, version)

                return

            except Exception as e:
                logger.warning(
                    f"Config fetch failed: {e}, retrying in 2s..."
                )
                await asyncio.sleep(2)

    # This is called to stop all threads.  An over-ride point for extra
    # functionality
    def stop(self):
        self.pubsub_backend.close()
        self.running = False

    # Returns the pub/sub backend (new interface)
    @property
    def pubsub(self): return self.pubsub_backend

    # Returns the pulsar host (backward compatibility)
    @property
    def pulsar_host(self): return self._pulsar_host

    # Register a new event handler for configuration change
    def register_config_handler(self, handler, types=None):
        self.config_handlers.append({
            "handler": handler,
            "types": set(types) if types else None,
        })

    # Called when a config notify message arrives
    async def on_config_notify(self, message, consumer, flow):

        notify_version = message.value().version
        notify_types = set(message.value().types)

        # Skip if we already have this version or newer
        if notify_version <= self.config_version:
            logger.debug(
                f"Ignoring config notify v{notify_version}, "
                f"already at v{self.config_version}"
            )
            return

        # Check if any handler cares about the affected types
        if notify_types:
            any_interested = False
            for entry in self.config_handlers:
                handler_types = entry["types"]
                if handler_types is None or notify_types & handler_types:
                    any_interested = True
                    break

            if not any_interested:
                logger.debug(
                    f"Ignoring config notify v{notify_version}, "
                    f"no handlers for types {notify_types}"
                )
                self.config_version = notify_version
                return

        logger.info(
            f"Config notify v{notify_version} types={list(notify_types)}, "
            f"fetching config..."
        )

        # Fetch full config using short-lived client
        try:
            config, version = await self.fetch_config()

            self.config_version = version

            # Invoke handlers that care about the affected types
            for entry in self.config_handlers:
                handler_types = entry["types"]
                if handler_types is None:
                    await entry["handler"](config, version)
                elif not notify_types or notify_types & handler_types:
                    await entry["handler"](config, version)

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
    def setup_logging(cls, args):
        """Configure logging for the entire application"""
        setup_logging(args)

    # Startup fabric.  launch calls launch_async in async mode.
    @classmethod
    def launch(cls, ident, doc):

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
    def add_args(parser):

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
