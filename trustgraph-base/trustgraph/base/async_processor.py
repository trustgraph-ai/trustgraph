
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
from . pubsub import PulsarClient
from . producer import Producer
from . consumer import Consumer

default_config_queue = config_push_queue
config_subscriber_id = str(uuid.uuid4())

class AsyncProcessor:


    def __init__(self, **params):

        self.client = PulsarClient(**params)

        self.taskgroup = params.get("taskgroup")
        if self.taskgroup is None:
            raise RuntimeError("Essential taskgroup missing")

        if not hasattr(__class__, "params_metric"):
            __class__.params_metric = Info(
                'params', 'Parameters configuration'
            )

        # FIXME: Maybe outputs information it should not
        __class__.params_metric.info({
            k: str(params[k])
            for k in params
        })

        self.config_push_queue = params.get(
            "config_push_queue", default_config_queue
        )

        self.config_handlers = []

        self.config_sub_task = self.subscribe(
            self.config_push_queue, config_subscriber_id,
            schema=ConfigPush, handler=self.on_config_change,
            start_of_messages=True
        )

        self.running = True

    def stop(self):
        self.client.close()
        self.running = False

    @property
    def pulsar_host(self): return self.client.pulsar_host

    def on_config(self, handler):
        self.config_handlers.append(handler)

    async def start(self):

        print("STARTING CONFIG SUB", flush=True)
        await self.config_sub_task.start()

    async def on_config_change(self, message, consumer):

        config = message.value().config
        version = message.value().version

        consumer.acknowledge(message)

        print("Config change event", config, version, flush=True)
        for ch in self.config_handlers:
            print("Invoke... handler...", flush=True)
            await ch(config, version)


    async def run_config_queue(self):

        if self.module == "config.service":
            print("I am config-svc, not looking at config queue", flush=True)
            return

        print("Config thread running", flush=True)

    async def run(self):
        while self.running:
            await asyncio.sleep(2)

    def subscribe(
            self, queue, subscriber, schema, handler, metrics=None,
            start_of_messages=False
    ):

        print("Processing subscription!!!!")
        return Consumer(
            taskgroup = self.taskgroup,
            client = self.client,
            queue = queue,
            subscriber = subscriber,
            schema = schema,
            handler = handler,
            metrics = metrics,
            start_of_messages=start_of_messages,
        )

    def publish(self, queue, schema, metrics=None):

        return Producer(
            client = self.client,
            queue = queue,
            schema = schema,
            metrics = metrics,
        )

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

            try:
                print("CREATING...", flush=True)

                p = cls(**args | { "taskgroup": tg })

                # FIXME: Two sort of 'ident' things going on here?
                p.module = ident
                p.config_ident = args.get("ident", "FIXME")

                print("STARTING...", flush=True)
                await p.start()

                task2 = tg.create_task(p.run())

            except Exception as e:
                print("Exception, dropping out", flush=True)
                raise e

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

        print(args, flush=True)

        if args["metrics"]:
            start_http_server(args["metrics_port"])

        while True:

            print("Starting...", flush=True)

            try:

                asyncio.run(cls.launch_async(
                    args, ident
                ))

            except KeyboardInterrupt:
                print("Keyboard interrupt.", flush=True)
                return

            except _pulsar.Interrupted:
                print("Pulsar Interrupted.", flush=True)
                return

            except ExceptionGroup as e:

                print("Exception group:", flush=True)

                for se in e.exceptions:
                    print("  Type:", type(se), flush=True)
                    print(f"  Exception: {se}", flush=True)

            except Exception as e:
                print("Type:", type(e), flush=True)
                print("Exception:", e, flush=True)

            print("Will retry...", flush=True)
            time.sleep(4)

    @staticmethod
    def add_args(parser):

        PulsarClient.add_args(parser)

        parser.add_argument(
            '--config-push-queue',
            default=default_config_queue,
            help=f'Config push queue {default_config_queue}',
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
