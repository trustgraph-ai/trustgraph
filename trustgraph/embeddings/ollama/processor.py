
"""
Embeddings service, applies an embeddings model selected from HuggingFace.
Input is text, output is embeddings vector.
"""
from langchain_community.embeddings import OllamaEmbeddings

from ... schema import EmbeddingsRequest, EmbeddingsResponse
from ... log_level import LogLevel
from ... base import ConsumerProducer

default_input_queue = 'embeddings'
default_output_queue = 'embeddings-response'
default_subscriber = 'embeddings-ollama'
default_model="mxbai-embed-large"
default_ollama = 'http://localhost:11434'

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": EmbeddingsRequest,
                "output_schema": EmbeddingsResponse,
            }
        )

        self.embeddings = OllamaEmbeddings(base_url=ollama, model=model)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        text = v.text
        embeds = self.embeddings.embed_query([text])

        print("Send response...", flush=True)
        r = EmbeddingsResponse(vectors=[embeds])

        self.producer.send(r, properties={"id": id})

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

    Processor.start('embeddings-ollama', __doc__)

