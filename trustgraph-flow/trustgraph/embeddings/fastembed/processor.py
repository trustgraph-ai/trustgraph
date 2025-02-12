
"""
Embeddings service, applies an embeddings model selected from HuggingFace.
Input is text, output is embeddings vector.
"""

from ... schema import EmbeddingsRequest, EmbeddingsResponse
from ... schema import embeddings_request_queue, embeddings_response_queue
from ... log_level import LogLevel
from ... base import ConsumerProducer
from fastembed import TextEmbedding
import os

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = embeddings_request_queue
default_output_queue = embeddings_response_queue
default_subscriber = module
default_model="sentence-transformers/all-MiniLM-L6-v2"

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
                "model": model,
            }
        )

        self.embeddings = TextEmbedding(model_name = model)

    async def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        text = v.text
        vecs = self.embeddings.embed([text])

        vecs = [
            v.tolist()
            for v in vecs
        ]

        print("Send response...", flush=True)
        r = EmbeddingsResponse(
            vectors=list(vecs),
            error=None,
        )

        await self.producer.send(r, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'Embeddings model (default: {default_model})'
        )

def run():

    Processor.launch(module, __doc__)

