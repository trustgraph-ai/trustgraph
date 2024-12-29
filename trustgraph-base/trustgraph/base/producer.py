
from pulsar.schema import JsonSchema
from prometheus_client import Info, Counter

from . base_processor import BaseProcessor

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
            chunking_enabled=True,
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
