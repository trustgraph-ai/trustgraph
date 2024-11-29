
"""
Wikipedia lookup service.  Fetchs an extract from the Wikipedia page
using the API.
"""

from trustgraph.schema import LookupRequest, LookupResponse, Error
from trustgraph.schema import encyclopedia_lookup_request_queue
from trustgraph.schema import encyclopedia_lookup_response_queue
from trustgraph.log_level import LogLevel
from trustgraph.base import ConsumerProducer
import requests

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = encyclopedia_lookup_request_queue
default_output_queue = encyclopedia_lookup_response_queue
default_subscriber = module
default_url="https://en.wikipedia.org/"

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        url = params.get("url", default_url)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": LookupRequest,
                "output_schema": LookupResponse,
            }
        )

        self.url = url

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling {v.kind} / {v.term}...", flush=True)

        try:

            url = f"{self.url}/api/rest_v1/page/summary/{v.term}"

            resp = Result = requests.get(url).json()
            resp = resp["extract"]

            r = LookupResponse(
                error=None,
                text=resp
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

            return

        except Exception as e:
                
            r = LookupResponse(
                error=Error(
                    type = "lookup-error",
                    message = str(e),
                ),
                text=None,
            )
            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

            return
            

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-u', '--url',
            default=default_url,
            help=f'LLM model (default: {default_url})'
        )

def run():

    Processor.start(module, __doc__)

