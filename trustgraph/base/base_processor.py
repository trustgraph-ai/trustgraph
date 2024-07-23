
import os
import argparse
import pulsar
import _pulsar
import time
from prometheus_client import start_http_server, Info

from .. log_level import LogLevel

class BaseProcessor:

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')

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
        log_level = params.get("log_level", LogLevel.INFO)

        self.pulsar_host = pulsar_host

        self.client = pulsar.Client(
            pulsar_host,
            logger=pulsar.ConsoleLogger(log_level.to_pulsar())
        )

    def __del__(self):

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
            '-l', '--log-level',
            type=LogLevel,
            default=LogLevel.INFO,
            choices=list(LogLevel),
            help=f'Output queue (default: info)'
        )

        parser.add_argument(
            '-M', '--metrics-enabled',
            type=bool,
            default=True,
            help=f'Pulsar host (default: true)',
        )

        parser.add_argument(
            '-P', '--metrics-port',
            type=int,
            default=8000,
            help=f'Pulsar host (default: 8000)',
        )

    def run(self):
        raise RuntimeError("Something should have implemented the run method")

    @classmethod
    def start(cls, prog, doc):

        while True:

            parser = argparse.ArgumentParser(
                prog=prog,
                description=doc
            )

            cls.add_args(parser)

            args = parser.parse_args()
            args = vars(args)

            if args["metrics_enabled"]:
                start_http_server(args["metrics_port"])

            try:

                p = cls(**args)
                p.run()

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

                time.sleep(10)
