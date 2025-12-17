
# Base class for processors.  Implements:
# - Pulsar client, subscribe and consume basic
# - the async startup logic
# - Initialising metrics

import asyncio
import argparse
import _pulsar
import time
import uuid
import logging
import os
from prometheus_client import start_http_server, Info

from .. schema import ConfigPush, config_push_queue
from .. log_level import LogLevel
from . pubsub import PulsarClient, get_pubsub
from . producer import Producer
from . consumer import Consumer
from . metrics import ProcessorMetrics, ConsumerMetrics
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

        # This records registered configuration handlers
        self.config_handlers = []

        # Create a random ID for this subscription to the configuration
        # service
        config_subscriber_id = str(uuid.uuid4())

        config_consumer_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "config",
        )

        # Subscribe to config queue
        self.config_sub_task = Consumer(

            taskgroup = self.taskgroup,
            backend = self.pubsub_backend,  # Changed from client to backend
            subscriber = config_subscriber_id,
            flow = None,

            topic = self.config_push_queue,
            schema = ConfigPush,

            handler = self.on_config_change,

            metrics = config_consumer_metrics,

            # This causes new subscriptions to view the entire history of
            # configuration
            start_of_messages = True
        )

        self.running = True

    # This is called to start dynamic behaviour.  An over-ride point for
    # extra functionality
    async def start(self):
        await self.config_sub_task.start()

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
    def register_config_handler(self, handler):
        self.config_handlers.append(handler)

    # Called when a new configuration message push occurs
    async def on_config_change(self, message, consumer, flow):

        # Get configuration data and version number
        config = message.value().config
        version = message.value().version

        # Invoke message handlers
        logger.info(f"Config change event: version={version}")
        for ch in self.config_handlers:
            await ch(config, version)

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

            except _pulsar.Interrupted:
                logger.info("Pulsar Interrupted.")
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

        # Pub/sub backend selection
        parser.add_argument(
            '--pubsub-backend',
            default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
            choices=['pulsar', 'mqtt'],
            help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)',
        )

        PulsarClient.add_args(parser)
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

