
import os
import argparse
import pulsar
import time

from .. log_level import LogLevel

class BaseProcessor:

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')

    def __init__(
            self,
            pulsar_host=default_pulsar_host,
            log_level=LogLevel.INFO,
    ):

        print("BASE INIT")

        self.client = None

        if pulsar_host == None:
            pulsar_host = default_pulsar_host

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

    @classmethod
    def start(cls, prog, doc):

        parser = argparse.ArgumentParser(
            prog=prog,
            description=doc
        )

        cls.add_args(parser)

        args = parser.parse_args()
        args = vars(args)

        try:

            p = cls(**args)
            p.run()

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

            time.sleep(10)

