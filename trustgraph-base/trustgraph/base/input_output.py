
import json
from pulsar.schema import JsonSchema

from .. schema import Error
from .. schema import config_request_queue, config_response_queue
from .. schema import config_push_queue
from .. log_level import LogLevel
from .. base import AsyncProcessor, Consumer, Producer

from .. base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics

class InputOutputProcessor(AsyncProcessor):

    def __init__(self, **params):
        
        self.id = params.get("id")
        self.subscriber = params.get("subscriber")
        self.input_schema = params.get("input_schema")
        self.output_schema = params.get("output_schema")

        ProcessorMetrics(id=self.id).info(
            {
                "subscriber": self.subscriber,
                "input_schema": self.input_schema.__name__,
                "output_schema": self.output_schema.__name__,
            }
        )

        super(InputOutputProcessor, self).__init__(
            **params | {
                "id": self.id,
                "input_schema": self.input_schema.__name__,
                "output_schema": self.output_schema.__name__,
            }
        )

        self.on_config(self.on_configuration)

        self.consumers = {}

        # These can be overriden by a derived class
        self.consumer_spec = ("input", self.input_schema)
        self.producer_spec = [
            ("output", self.output_schema)
        ]

        print("Service initialised.")

    async def start_flow(self, flow, defn):

        consumer_tag = self.consumer_spec[0]
        consumer_schema = self.consumer_spec[1]
        consumer_metrics = ConsumerMetrics(self.id, f"{flow}-{consumer_tag}")

        consumer = self.subscribe(
            queue = defn[consumer_tag],
            subscriber = self.subscriber,
            schema = consumer_schema,
            handler = self.on_message,
            metrics = consumer_metrics,
        )

        class Queues:
            pass

        consumer.q = Queues()
        consumer.id = self.id
        consumer.flow = flow

        producers = {}

        for spec in self.producer_spec:

            producer_tag = spec[0]
            producer_schema = spec[1]
            producer_metrics = ProducerMetrics(
                self.id, f"{flow}-{producer_tag}"
            )

            producer = self.publish(
                queue = defn[producer_tag],
                schema = spec[1],
                metrics = producer_metrics,
            )

            setattr(consumer.q, producer_tag, producer)

        self.consumers[flow] = consumer

        await consumer.start()

        print("Started flow: ", flow)

    async def stop_flow(self, flow):
        await self.consumers[flow].stop()
        del self.consumers[flow]

        print("Stopped flow: ", flow, flush=True)

    async def on_configuration(self, config, version):

        print("Got config version", version, flush=True)

        if "flows" not in config: return

        if self.id in config["flows"]:

            flow_config = json.loads(config["flows"][self.id])

            wanted_keys = flow_config.keys()
            current_keys = self.consumers.keys()

            for key in wanted_keys:
                if key not in current_keys:
                    await self.start_flow(key, flow_config[key])

            for key in current_keys:
                if key not in wanted_keys:
                    await self.stop_flow(key)

            print("Handled config update")

    async def start(self):
        await super(InputOutputProcessor, self).start()

    @staticmethod
    def add_args(parser, default_subscriber):

        AsyncProcessor.add_args(parser)

        parser.add_argument(
            '-s', '--subscriber',
            default=default_subscriber,
            help=f'Queue subscriber name (default: {default_subscriber})'
        )

        # parser.add_argument(
        #     '--rate-limit-retry',
        #     type=int,
        #     default=default_rate_limit_retry,
        #     help=f'Rate limit retry (default: {default_rate_limit_retry})'
        # )

        # parser.add_argument(
        #     '--rate-limit-timeout',
        #     type=int,
        #     default=default_rate_limit_timeout,
        #     help=f'Rate limit timeout (default: {default_rate_limit_timeout})'
        # )

def run():

    Processor.launch(module, __doc__)

