
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

        print("alsdkjasdlasdjkL")

        ProcessorMetrics(id=self.id).info(
            {
                "subscriber": self.subscriber,
                "input_schema": self.input_schema.__name__,
                "output_schema": self.output_schema.__name__,
            }
        )

        print("ASD")
        super(InputOutputProcessor, self).__init__(
            **params | {
                "id": self.id,
                "input_schema": self.input_schema.__name__,
                "output_schema": self.output_schema.__name__,
            }
        )

        print("alsdkj")
        self.on_config(self.on_configuration)

        self.subs = {}
        self.pubs = {}

        print("Service initialised.")

    async def start_handler(self, flow, defn):

        input_metrics = ConsumerMetrics(self.id, flow)
        output_metrics = ProducerMetrics(self.id, flow)

        self.subs[flow] = self.subscribe(
            queue = defn["input"],
            subscriber = self.subscriber,
            schema = self.input_schema,
            handler = self.on_message,
            metrics = input_metrics,
        )
        
        self.pubs[flow] = self.publish(
            queue = defn["output"],
            schema = self.output_schema,
            metrics = output_metrics,
        )

        await self.subs[flow].start()

        print("Started flow for", flow)

    async def stop_handler(self, flow):
        print("Stopping ", flow, flush=True)
        await self.subs[flow].stop()
        del self.subs[flow]
        del self.pubs[flow]
        

    async def on_configuration(self, config, version):

        print("Got config version", version)

        if "flows" not in config: return

        if self.id in config["flows"]:

            flow_config = json.loads(config["flows"][self.id])

            wanted_keys = flow_config.keys()
            current_keys = self.subs.keys()

            for key in wanted_keys:
                if key not in current_keys:
                    await self.start_handler(key, flow_config[key])

            for key in current_keys:
                if key not in wanted_keys:
                    await self.stop_handler(key)

            print("Handled config update")

    async def start(self):

        print("INPUT OUTPU START")
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

