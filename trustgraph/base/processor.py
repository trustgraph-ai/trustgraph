
import os
import argparse
import pulsar
import time
from pulsar.schema import JsonSchema

from .. log_level import LogLevel

class BaseProcessor:

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')

    def __init__(
            self,
            pulsar_host=default_pulsar_host,
            log_level=LogLevel.INFO,
    ):

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

    def run(self):
        raise RuntimeError("Something should have implemented the run method")

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

class Consumer(BaseProcessor):

    def __init__(
            self,
            pulsar_host=None,
            log_level=LogLevel.INFO,
            input_queue="input",
            subscriber="subscriber",
            request_schema=None,
    ):

        super(Consumer, self).__init__(
            pulsar_host=pulsar_host,
            log_level=log_level,
        )

        if request_schema == None:
            raise RuntimeError("request_schema must be specified")

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(request_schema),
        )

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                self.handle(msg)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

            except Exception as e:

                print("Exception:", e, flush=True)

                # Message failed to be processed
                self.consumer.negative_acknowledge(msg)

    @staticmethod
    def add_args(parser, default_input_queue, default_subscriber):

        BaseProcessor.add_args(parser)

        parser.add_argument(
            '-i', '--input-queue',
            default=default_input_queue,
            help=f'Input queue (default: {default_input_queue})'
        )

        parser.add_argument(
            '-s', '--subscriber',
            default=default_subscriber,
            help=f'Queue subscriber name (default: {default_subscriber})'
        )

class ConsumerProducer(BaseProcessor):

    def __init__(
            self,
            pulsar_host=None,
            log_level=LogLevel.INFO,
            input_queue="input",
            output_queue="output",
            subscriber="subscriber",
            request_schema=None,
            response_schema=None,
    ):

        super(ConsumerProducer, self).__init__(
            pulsar_host=pulsar_host,
            log_level=log_level,
        )

        if request_schema == None:
            raise RuntimeError("request_schema must be specified")

        if response_schema == None:
            raise RuntimeError("response_schema must be specified")

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(request_schema),
        )

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(response_schema),
        )

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                resp = self.handle(msg)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

            except Exception as e:

                print("Exception:", e, flush=True)

                # Message failed to be processed
                self.consumer.negative_acknowledge(msg)

    def send(self, msg, properties={}):

        print(msg)
        self.producer.send(msg, properties)

    @staticmethod
    def add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
    ):

        BaseProcessor.add_args(parser)

        parser.add_argument(
            '-i', '--input-queue',
            default=default_input_queue,
            help=f'Input queue (default: {default_input_queue})'
        )

        parser.add_argument(
            '-s', '--subscriber',
            default=default_subscriber,
            help=f'Queue subscriber name (default: {default_subscriber})'
        )

        parser.add_argument(
            '-o', '--output-queue',
            default=default_output_queue,
            help=f'Output queue (default: {default_output_queue})'
        )
