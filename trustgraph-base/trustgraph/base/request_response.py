
from pulsar.schema import JsonSchema

from .. schema import Error
from .. schema import config_request_queue, config_response_queue
from .. schema import config_push_queue
from .. log_level import LogLevel
from .. base import AsyncProcessor, Consumer, Producer

from .. base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics

class RequestResponseProcessor(AsyncProcessor):

    def __init__(self, **params):
        
        id = params.get("id")
        self.subscriber = params.get("subscriber")
        self.request_schema = params.get("request_schema")
        self.response_schema = params.get("response_schema")

        ProcessorMetrics(id=id).info(
            {
                "subscriber": self.subscriber,
                "request_schema": self.request_schema.__name__,
                "response_schema": self.response_schema.__name__,
            }
        )

        super(Processor, self).__init__(
            **params | {
                "request_schema": self.request_schema.__name__,
                "response_schema": self.response_schema.__name__,
            }
        )

        self.on_config(self.on_configuration)

        self.subs = {}
        self.pubs = {}

        print("Service initialised.")

    async def start_handler(self, flow, defn):

        request_metrics = ConsumerMetrics(self.id, flow)
        response_metrics = ProducerMetrics(self.id, flow)

        self.subs[flow] = self.subscribe(
            queue = defn["input"]
            subscriber = subscriber,
            schema = self.request_schema,
            handler = self.on_message,
            metrics = request_metrics,
        )
        
        self.pubs[flow] = self.publish(
            queue = defn["output"],
            schema = self.response_schema,
            metrics = response_metrics,
        )

        self.subs[flow].start()

        print("Started flow for", flow)

    async def on_configuration(self, config, version):

        if "flows" not in config: return

        if self.id in config["flows"]:

            wanted_keys = config["flows"][self.id].keys()
            current_keys = self.subs.keys()

            for key in wanted_keys:
                if key not in current_keys:
                    self.start_handler(key, config["flows"][key])

            for key in current_keys:
                if key not in wanted_keys:
                    self.stop_handler(key, config["flows"][key])

            print("Handled config update")

    async def start(self):

        await self.request_sub.start()
        
    async def on_message(self, msg, consumer):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling {id}...", flush=True)

            consumer.acknowledge(msg)

        except Exception as e:
            
            resp = "error"

            await self.response_pub.send(resp, properties={"id": id})

            consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        AsyncProcessor.add_args(parser)

def run():

    Processor.launch(module, __doc__)

