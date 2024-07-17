
"""
Embeddings service, applies an embeddings model selected from HuggingFace.
Input is text, output is embeddings vector.
"""

from langchain_huggingface import HuggingFaceEmbeddings

from ... schema import EmbeddingsRequest, EmbeddingsResponse
from ... log_level import LogLevel
from ... base import ConsumerProducer

default_input_queue = 'embeddings'
default_output_queue = 'embeddings-response'
default_subscriber = 'embeddings-hf'
default_model="all-MiniLM-L6-v2"

class Processor(ConsumerProducer):

    def __init__(
            self,
            pulsar_host=None,
            input_queue=default_input_queue,
            output_queue=default_output_queue,
            subscriber=default_subscriber,
            log_level=LogLevel.INFO,
            model=default_model,
    ):

        super(Processor, self).__init__(
            pulsar_host=pulsar_host,
            log_level=log_level,
            input_queue=input_queue,
            output_queue=output_queue,
            subscriber=subscriber,
            input_schema=EmbeddingsRequest,
            output_schema=EmbeddingsResponse,
        )

        self.embeddings = HuggingFaceEmbeddings(model_name=model)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        text = v.text
        embeds = self.embeddings.embed_documents([text])

        print("Send response...", flush=True)
        r = EmbeddingsResponse(vectors=embeds)
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
            default="all-MiniLM-L6-v2",
            help=f'LLM model (default: all-MiniLM-L6-v2)'
        )

def run():

    Processor.start("embeddings-hf", __doc__)

