
import json
from pulsar.schema import JsonSchema

from .. schema import Error
from .. schema import config_request_queue, config_response_queue
from .. schema import config_push_queue
from .. log_level import LogLevel
from .. base import AsyncProcessor, Consumer, Producer

from .. base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics
from . flow_processor import FlowProcessor

class RequestResponseService(FlowProcessor):

    def __init__(self, **params):

        super(RequestResponseService, self).__init__(**params)

        self.response_schema = params.get("responsedrequest_schema")

        # These can be overriden by a derived class
        self.consumer_spec = [
            ("request", params.get("request_schema"), self.on_message)
        ]
        self.producer_spec = [
            ("response", params.get("response_schema"))
        ]

        print("Service initialised.")

    async def on_message(self, message, consumer, flow):
        
        v = message.value()

        # Sender-produced ID
        id = message.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        try:
            resp = await self.on_request(v, consumer, flow)

            print("Send response...", flush=True)

            await flow.producer["response"].send(resp, properties={"id": id})

            return

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Send error response...", flush=True)
            r = self.response_schema(
                error=Error(
                    type="internal-error",
                    message = str(e)
                )
            )

            await flow.producer["response"].send(r, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(module, __doc__)

