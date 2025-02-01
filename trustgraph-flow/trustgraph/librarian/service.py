
"""
Librarian service, manages documents in collections
"""

from ... schema import xEmbeddingsRequest, EmbeddingsResponse
from ... schema import xembeddings_request_queue, embeddings_response_queue
from ... log_level import LogLevel
from ... base import ConsumerProducer
import os

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = _request_queue
default_output_queue = _response_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)

        model = params.get("model", default_model)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": EmbeddingsRequest,
                "output_schema": EmbeddingsResponse,
            }
        )

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        text = v.text

        print("Send response...", flush=True)
        r = xEmbeddingsResponse(
            error=None,
        )

        self.producer.send(r, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

def run():

    Processor.start(module, __doc__)

