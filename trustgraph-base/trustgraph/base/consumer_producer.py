
from pulsar.schema import JsonSchema
import pulsar
from prometheus_client import Histogram, Info, Counter, Enum
import time

from . consumer import Consumer
from .. exceptions import TooManyRequests

class ConsumerProducer(Consumer):

    def __init__(self, **params):

        super(ConsumerProducer, self).__init__(**params)

        self.output_queue = params.get("output_queue")
        self.output_schema = params.get("output_schema")

        if not hasattr(__class__, "output_metric"):
            __class__.output_metric = Counter(
                'output_count', 'Output items created'
            )

        __class__.pubsub_metric.info({
            "input_queue": self.input_queue,
            "output_queue": self.output_queue,
            "subscriber": self.subscriber,
            "input_schema": self.input_schema.__name__,
            "output_schema": self.output_schema.__name__,
            "rate_limit_retry": str(self.rate_limit_retry),
            "rate_limit_timeout": str(self.rate_limit_timeout),
        })

        if self.output_schema == None:
            raise RuntimeError("output_schema must be specified")

        self.producer = self.client.create_producer(
            topic=self.output_queue,
            schema=JsonSchema(self.output_schema),
            chunking_enabled=True,
        )

        print("Initialised consumer/producer.")

    def send(self, msg, properties={}):
        self.producer.send(msg, properties)
        __class__.output_metric.inc()

    @staticmethod
    def add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
    ):

        Consumer.add_args(parser, default_input_queue, default_subscriber)

        parser.add_argument(
            '-o', '--output-queue',
            default=default_output_queue,
            help=f'Output queue (default: {default_output_queue})'
        )

