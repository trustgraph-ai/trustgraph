
import asyncio
import os
import argparse
import pulsar
from pulsar.schema import JsonSchema
import _pulsar
import time
import uuid
from prometheus_client import start_http_server, Info

from .. schema import ConfigPush, config_push_queue
from .. log_level import LogLevel

default_config_queue = config_push_queue
config_subscriber_id = str(uuid.uuid4())

class BaseProcessor:

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_pulsar_api_key = os.getenv("PULSAR_API_KEY", None)

    def __init__(self, **params):

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
            schema=JsonSchema(ConfigPush),         
        )

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

            await self.on_config(v.version, v.config)

    async def on_config(self, version, config):
        pass

    async def run(self):
        raise RuntimeError("Something should have implemented the run method")

    @classmethod
    async def launch_async(cls, args, prog):
        p = cls(**args)
        p.module = prog
        await p.start()

        task1 = asyncio.create_task(p.run_config_queue())
        task2 = asyncio.create_task(p.run())

        await asyncio.gather(task1, task2)

    @classmethod
    def launch(cls, prog, doc):

        parser = argparse.ArgumentParser(
            prog=prog,
            description=doc
        )

        cls.add_args(parser)

        args = parser.parse_args()
        args = vars(args)

        print(args)

        if args["metrics"]:
            start_http_server(args["metrics_port"])

        while True:

            try:

                asyncio.run(cls.launch_async(args, prog))

            except KeyboardInterrupt:
                print("Keyboard interrupt.")
                return

            except _pulsar.Interrupted:
                print("Pulsar Interrupted.")
                return

            except Exception as e:

                print(type(e))

                print("Exception:", e, flush=True)
                print("Will retry...", flush=True)

                time.sleep(4)

