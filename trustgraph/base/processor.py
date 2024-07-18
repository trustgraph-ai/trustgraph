
import os
import argparse
import pulsar
import _pulsar
import time
from pulsar.schema import JsonSchema
from prometheus_client import start_http_server, Histogram, Info, Counter

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

class Consumer(BaseProcessor):

    def __init__(self, **params):

        super(Consumer, self).__init__(**params)

        input_queue = params.get("input_queue")
        subscriber = params.get("subscriber")
        input_schema = params.get("input_schema")

        if input_schema == None:
            raise RuntimeError("input_schema must be specified")

        if not hasattr(__class__, "request_metric"):
            __class__.request_metric = Histogram(
                'request_latency', 'Request latency (seconds)'
            )

        if not hasattr(__class__, "pubsub_metric"):
            __class__.pubsub_metric = Info(
                'pubsub', 'Pub/sub configuration'
            )

        if not hasattr(__class__, "processing_metric"):
            __class__.processing_metric = Counter(
                'processing_count', 'Processing count', ["status"]
            )

        __class__.pubsub_metric.info({
            "input_queue": input_queue,
            "subscriber": subscriber,
            "input_schema": input_schema.__name__,
        })

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(input_schema),
        )

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                with __class__.request_metric.time():
                    self.handle(msg)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

                __class__.processing_metric.labels(status="success").inc()

            except Exception as e:

                print("Exception:", e, flush=True)

                # Message failed to be processed
                self.consumer.negative_acknowledge(msg)

                __class__.processing_metric.labels(status="error").inc()

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

    def __init__(self, **params):

        input_queue = params.get("input_queue")
        output_queue = params.get("output_queue")
        subscriber = params.get("subscriber")
        input_schema = params.get("input_schema")
        output_schema = params.get("output_schema")

        if not hasattr(__class__, "request_metric"):
            __class__.request_metric = Histogram(
                'request_latency', 'Request latency (seconds)'
            )

        if not hasattr(__class__, "output_metric"):
            __class__.output_metric = Counter(
                'output_count', 'Output items created'
            )

        if not hasattr(__class__, "pubsub_metric"):
            __class__.pubsub_metric = Info(
                'pubsub', 'Pub/sub configuration'
            )

        if not hasattr(__class__, "processing_metric"):
            __class__.processing_metric = Counter(
                'processing_count', 'Processing count', ["status"]
            )

        __class__.pubsub_metric.info({
            "input_queue": input_queue,
            "output_queue": output_queue,
            "subscriber": subscriber,
            "input_schema": input_schema.__name__,
            "output_schema": output_schema.__name__,
        })

        super(ConsumerProducer, self).__init__(**params)

        if input_schema == None:
            raise RuntimeError("input_schema must be specified")

        if output_schema == None:
            raise RuntimeError("output_schema must be specified")

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            schema=JsonSchema(input_schema),
        )

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(output_schema),
        )

    def run(self):

        while True:

            msg = self.consumer.receive()

            try:

                with __class__.request_metric.time():
                    resp = self.handle(msg)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

                __class__.processing_metric.labels(status="success").inc()

            except Exception as e:

                print("Exception:", e, flush=True)

                # Message failed to be processed
                self.consumer.negative_acknowledge(msg)

                __class__.processing_metric.labels(status="error").inc()

    def send(self, msg, properties={}):
        self.producer.send(msg, properties)
        __class__.output_metric.inc()

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

class Producer(BaseProcessor):

    def __init__(self, **params):

        output_queue = params.get("output_queue")
        output_schema = params.get("output_schema")

        if not hasattr(__class__, "output_metric"):
            __class__.output_metric = Counter(
                'output_count', 'Output items created'
            )

        if not hasattr(__class__, "pubsub_metric"):
            __class__.pubsub_metric = Info(
                'pubsub', 'Pub/sub configuration'
            )

        __class__.pubsub_metric.info({
            "output_queue": output_queue,
            "output_schema": output_schema.__name__,
        })

        super(Producer, self).__init__(**params)

        if output_schema == None:
            raise RuntimeError("output_schema must be specified")

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(output_schema),
        )

    def send(self, msg, properties={}):
        self.producer.send(msg, properties)
        __class__.output_metric.inc()

    @staticmethod
    def add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
    ):

        BaseProcessor.add_args(parser)

        parser.add_argument(
            '-o', '--output-queue',
            default=default_output_queue,
            help=f'Output queue (default: {default_output_queue})'
        )
