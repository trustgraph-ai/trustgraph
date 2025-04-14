
import asyncio
import os
import argparse
import pulsar
from pulsar.schema import JsonSchema
import _pulsar
import time
import uuid
from prometheus_client import start_http_server, Info, Enum

from .. schema import ConfigPush, config_push_queue
from .. log_level import LogLevel
from .. exceptions import TooManyRequests

default_config_queue = config_push_queue
config_subscriber_id = str(uuid.uuid4())

class Subscription:
    def __init__(self, consumer, handler, taskgroup):
        self.running = True
        self.task = None
        self.consumer = consumer
        self.handle = handler
        self.taskgroup=taskgroup

    async def start(self):
        self.running = True
        self.task = self.taskgroup.create_task(self.run())

    async def run(self):

        while self.running:

            print("Waiting...")
            msg = await asyncio.to_thread(self.consumer.receive)
            print("Got", msg)

#             expiry = time.time() + self.rate_limit_timeout
            expiry = time.time() + 10

            # This loop is for retry on rate-limit / resource limits
            while True:

                if time.time() > expiry:

                    print("Gave up waiting for rate-limit retry", flush=True)

                    # Message failed to be processed, this causes it to
                    # be retried
                    self.consumer.negative_acknowledge(msg)

                    # FIXME
#                    __class__.processing_metric.labels(status="error").inc()

                    # Break out of retry loop, processes next message
                    break

                try:

                    print("Handle...")
                    # FIXME
#                    with __class__.request_metric.time():
                    await self.handle(msg, self.consumer)
                    print("Handled.")

                    # Acknowledge successful processing of the message
                    self.consumer.acknowledge(msg)

#                    __class__.processing_metric.labels(status="success").inc()

                    # Break out of retry loop
                    break

                except TooManyRequests:

                    print("TooManyRequests: will retry...", flush=True)

                    # FIXME
#                     __class__.rate_limit_metric.inc()

                    # Sleep
                    time.sleep(self.rate_limit_retry)

                    # Contine from retry loop, just causes a reprocessing
                    continue

                except Exception as e:

                    print("Exception:", e, flush=True)

                    # Message failed to be processed, this causes it to
                    # be retried
                    self.consumer.negative_acknowledge(msg)

#                    __class__.processing_metric.labels(status="error").inc()

                    # Break out of retry loop, processes next message
                    break

class Publisher:

    def __init__(self, producer):
        self.producer = producer
#         self.running = True

    async def send(self, msg, properties={}):
        self.producer.send(msg, properties)

        # FIXME
#         __class__.output_metric.inc()

                
class BaseProcessor:

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_pulsar_api_key = os.getenv("PULSAR_API_KEY", None)

    def __init__(self, **params):

        self.taskgroup = params.get("taskgroup")
        if self.taskgroup is None:
            raise RuntimeError("Essential taskgroup missing")

        self.client = None

        if not hasattr(__class__, "params_metric"):
            __class__.params_metric = Info(
                'params', 'Parameters configuration'
            )

        # FIXME: Maybe outputs information it should not
        __class__.params_metric.info({
            k: str(params[k])
            for k in params
        })

        pulsar_host = params.get("pulsar_host", self.default_pulsar_host)
        pulsar_listener = params.get("pulsar_listener", None)
        pulsar_api_key = params.get("pulsar_api_key", None)
        log_level = params.get("log_level", LogLevel.INFO)

        self.config_push_queue = params.get(
            "config_push_queue",
            default_config_queue
        )

        self.pulsar_host = pulsar_host
        self.pulsar_api_key = pulsar_api_key

        if pulsar_api_key:
            auth = pulsar.AuthenticationToken(pulsar_api_key)
            self.client = pulsar.Client(
            pulsar_host,
            authentication=auth,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
            )
        else:
            self.client = pulsar.Client(
            pulsar_host,
            listener_name=pulsar_listener,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
            )

        self.pulsar_listener = pulsar_listener

        self.config_subscriber = self.client.subscribe(
            self.config_push_queue, config_subscriber_id,
            consumer_type=pulsar.ConsumerType.Shared,
            initial_position=pulsar.InitialPosition.Earliest,
            schema=JsonSchema(ConfigPush),
        )

        self.config_handlers = []

    def __del__(self):

        if hasattr(self, "client"):
            if self.client:
                self.client.close()

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '-p', '--pulsar-host',
            default=__class__.default_pulsar_host,
            help=f'Pulsar host (default: {__class__.default_pulsar_host})',
        )
        
        parser.add_argument(
            '--pulsar-api-key',
            default=__class__.default_pulsar_api_key,
            help=f'Pulsar API key',
        )

        parser.add_argument(
            '--config-push-queue',
            default=default_config_queue,
            help=f'Config push queue {default_config_queue}',
        )

        parser.add_argument(
            '--pulsar-listener',
            help=f'Pulsar listener (default: none)',
        )

        parser.add_argument(
            '-l', '--log-level',
            type=LogLevel,
            default=LogLevel.INFO,
            choices=list(LogLevel),
            help=f'Output queue (default: info)'
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

    async def start(self):
        pass

    async def run_config_queue(self):

        if self.module == "config.service":
            print("I am config-svc, not looking at config queue", flush=True)
            return

        print("Config thread running", flush=True)
        
        while True:

            try:
                msg = await asyncio.to_thread(
                    self.config_subscriber.receive, timeout_millis=2000
                )
            except pulsar.Timeout:
                continue

            v = msg.value()
            print("Got config version", v.version, flush=True)

            for h in self.config_handlers:
                await h(v.version, v.config)

    async def run(self):
        while True:
            await asyncio.sleep(2)

#       raise RuntimeError("Something should have implemented the run method")

    def subscribe(self, input_queue, subscriber, schema, handler):

        consumer = self.client.subscribe(
            input_queue, subscriber,
            consumer_type=pulsar.ConsumerType.Shared,
            schema=JsonSchema(schema),
        )

        s = Subscription(consumer, handler, self.taskgroup)

        return s

    def publish(self, output_queue, schema):

        producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(schema),
            chunking_enabled=True,
        )

        p = Publisher(producer)

        return p

    def set_processor_state(self, flow, state):

        if not hasattr(__class__, "state_metric"):
            __class__.state_metric = Enum(
                'processor_state', 'Processor state',
                ["flow"],
                states=['starting', 'running', 'stopped']
            )

        __class__.state_metric.labels("flow").state(state)

    def set_pubsub_info(self, flow, info) :

        if not hasattr(__class__, "pubsub_metric"):
            __class__.pubsub_metric = Info(
                'pubsub', 'Pub/sub configuration',
                ["flow"]
            )

        __class__.pubsub_metric.labels(flow=flow).info(info)

    @classmethod
    async def launch_async(cls, args, ident):

        async with asyncio.TaskGroup() as tg:

            p = cls(taskgroup=tg, **args)

            # FIXME: Two sort of 'ident' things going on here?
            p.module = ident
            p.config_ident = args.get("ident", "FIXME")

            await p.start()

            task1 = tg.create_task(p.run_config_queue())
            task2 = tg.create_task(p.run())

    @classmethod
    def launch(cls, ident, doc):

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

        print(args)

        if args["metrics"]:
            start_http_server(args["metrics_port"])

        while True:

            try:

                asyncio.run(cls.launch_async(
                    args, ident
                ))

            except KeyboardInterrupt:
                print("Keyboard interrupt.")
                return

            except _pulsar.Interrupted:
                print("Pulsar Interrupted.")
                return

            except Exception as e:

                print(type(e))

                print(e.message)
                print(e.exceptions)
                print(e)

                print("Exception:", e, flush=True)
                print("Will retry...", flush=True)

                time.sleep(4)

