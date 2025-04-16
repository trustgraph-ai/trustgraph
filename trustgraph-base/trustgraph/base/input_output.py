
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

        ProcessorMetrics(id=self.id).info(
            {
                "subscriber": self.subscriber,
            }
        )

        super(InputOutputProcessor, self).__init__(
            **params | {
                "id": self.id,
            }
        )

        self.on_config(self.on_configuration)

        self.consumers = {}
        self.producers = {}

        # These can be overriden by a derived class
        self.consumer_spec = []
        self.producer_spec = []

# "input", self.input_schema)
#                 "input_schema": Document,
#                 "output_schema": TextDocument,

        print("Service initialised.")

    def register_consumer(self, name, schema, handler):
        self.consumer_spec.append((name, schema, handler))

    def register_producer(self, name, schema):
        self.producer_spec.append((name, schema))

    async def start_flow(self, flow, defn):

        producers = {}

        for spec in self.producer_spec:

            name, schema = spec

            producer_metrics = ProducerMetrics(
                self.id, f"{flow}-{name}"
            )

            producer = self.publish(
                queue = defn[name],
                schema = schema,
                metrics = producer_metrics,
            )

            producers[name] = producer

        consumers = {}

        for spec in self.consumer_spec:

            name, schema, handler = spec

            consumer_metrics = ConsumerMetrics(
                self.id, f"{flow}-{name}"
            )

            consumer = self.subscribe(
                queue = defn[name],
                subscriber = self.subscriber,
                schema = schema,
                handler = handler,
                metrics = consumer_metrics,
            )

            # Consumer handle gets access to producers and other
            # metadata
            consumer.id = self.id
            consumer.name = name
            consumer.flow = flow
            consumer.q = producers

            consumers[name] = consumer

            await consumer.start()

        self.consumers[flow] = consumers
        self.producers[flow] = producers
            
        print("Started flow: ", flow)

    async def stop_flow(self, flow):

        for c in self.consumers[flow]:
            await c.stop()

        del self.consumers[flow]
        del self.producers[flow]

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

