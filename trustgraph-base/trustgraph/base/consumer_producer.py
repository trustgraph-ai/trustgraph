
from pulsar.schema import JsonSchema
import pulsar
from prometheus_client import Histogram, Info, Counter, Enum
import time

from . base_processor import BaseProcessor
from .. exceptions import TooManyRequests

# FIXME: Derive from consumer?  And producer?

class ConsumerProducer(BaseProcessor):

    def __init__(self, **params):

        if not hasattr(__class__, "state_metric"):
            __class__.state_metric = Enum(
                'processor_state', 'Processor state',
                states=['starting', 'running', 'stopped']
            )
            __class__.state_metric.state('starting')

        __class__.state_metric.state('starting')

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

        self.producer = self.client.create_producer(
            topic=output_queue,
            schema=JsonSchema(output_schema),
            chunking_enabled=True,
        )

        self.consumer = self.client.subscribe(
            input_queue, subscriber,
            consumer_type=pulsar.ConsumerType.Shared,
            schema=JsonSchema(input_schema),
        )

    def run(self):

        __class__.state_metric.state('running')

        while True:

            msg = self.consumer.receive()

            try:

                with __class__.request_metric.time():
                    resp = self.handle(msg)

                # Acknowledge successful processing of the message
                self.consumer.acknowledge(msg)

                __class__.processing_metric.labels(status="success").inc()

            except TooManyRequests:
                self.consumer.negative_acknowledge(msg)
                print("TooManyRequests: will retry")
                __class__.processing_metric.labels(status="rate-limit").inc()
                time.sleep(5)
                continue

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

