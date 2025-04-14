
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

    @property
    def pulsar_host(self): return self.client.pulsar_host

    async def start(self):

        self.config_sub_task = self.subscribe(
            self.config_push_queue, config_subscriber_id,
            schema=ConfigPush, handler=self.on_config_change
        )

    async def on_config_change(self, config, version):
        for ch in self.config_handlers:
            ch(config, version)

    async def run_config_queue(self):

        if self.module == "config.service":
            print("I am config-svc, not looking at config queue", flush=True)
            return

        print("Config thread running", flush=True)

    async def run(self):
        while True:
            await asyncio.sleep(2)

    def subscribe(self, queue, subscriber, schema, handler):

        return Consumer(
            self.taskgroup, self.client, queue, subscriber, schema, handler
        )

    def publish(self, queue, schema):

        return Producer(
            self.client, queue, schema
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

            p = cls(**args | { "taskgroup": tg })

            # FIXME: Two sort of 'ident' things going on here?
            p.module = ident
            p.config_ident = args.get("ident", "FIXME")

            await p.start()

#            task1 = tg.create_task(p.run_config_queue())
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

            except ExceptionGroup as e:

                print("Exception group:")

                for se in e.exceptions:
                    print("   Type:", type(se))
                    print(f"  Exception: {se}")

            except Exception as e:
                print("Type:", type(e))
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
