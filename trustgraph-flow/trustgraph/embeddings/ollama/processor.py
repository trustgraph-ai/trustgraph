
"""
Embeddings service, applies an embeddings model hosted on a local Ollama.
Input is text, output is embeddings vector.
"""

from ... schema import EmbeddingsRequest, EmbeddingsResponse
from ... schema import embeddings_request_queue, embeddings_response_queue
from ... log_level import LogLevel
from ... base import ConsumerProducer
from ollama import Client
import os

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = embeddings_request_queue
default_output_queue = embeddings_response_queue
default_subscriber = module
default_model="mxbai-embed-large"
default_ollama = os.getenv("OLLAMA_HOST", 'http://localhost:11434')

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)

        ollama = params.get("ollama", default_ollama)
        model = params.get("model", default_model)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": EmbeddingsRequest,
                "output_schema": EmbeddingsResponse,
                "ollama": ollama,
                "model": model,
            }
        )

        self.client = Client(host=ollama)
        self.model = model

    async def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        text = v.text
        embeds = self.client.embed(
            model = self.model,
            input = text
        )

        print("Send response...", flush=True)
        r = EmbeddingsResponse(
            vectors=embeds.embeddings,
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

        parser.add_argument(
            '-r', '--ollama',
            default=default_ollama,
            help=f'ollama (default: {default_ollama})'
        )

def run():

    Processor.launch(module, __doc__)

