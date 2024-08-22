
"""
Embeddings service, applies an embeddings model selected from HuggingFace.
Input is text, output is embeddings vector.
"""

from langchain_huggingface import HuggingFaceEmbeddings

from ... schema import EmbeddingsRequest, EmbeddingsResponse, Error
from ... schema import embeddings_request_queue, embeddings_response_queue
from ... log_level import LogLevel
from ... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = embeddings_request_queue
default_output_queue = embeddings_response_queue
default_subscriber = module
default_model="all-MiniLM-L6-v2"

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

        self.embeddings = HuggingFaceEmbeddings(model_name=model)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        try:

            text = v.text
            embeds = self.embeddings.embed_documents([text])

            print("Send response...", flush=True)
            r = EmbeddingsResponse(vectors=embeds, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)


        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = EmbeddingsResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)
            

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

    Processor.start(module, __doc__)

