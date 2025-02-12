
import asyncio
import os
import argparse
import pulsar
import _pulsar
import time
from prometheus_client import start_http_server, Info

from .. log_level import LogLevel

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
        pulsar_api_key = params.get("pulsar_api_key", None)
        pulsar_listener = params.get("pulsar_listener", None)
        log_level = params.get("log_level", LogLevel.INFO)

        self.pulsar_host = pulsar_host
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

    async def run(self):
        raise RuntimeError("Something should have implemented the run method")

    @classmethod
    async def launch_async(cls, args):
        p = cls(**args)
        await p.start()
        await p.run()

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

                asyncio.run(cls.launch_async(args))

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

