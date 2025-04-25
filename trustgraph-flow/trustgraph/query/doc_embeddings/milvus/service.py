
"""
Document embeddings query service.  Input is vector, output is an array
of chunks
"""

from .... direct.milvus_doc_embeddings import DocVectors
from .... schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse
from .... schema import Error, Value
from .... schema import document_embeddings_request_queue
from .... schema import document_embeddings_response_queue
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = document_embeddings_request_queue
default_output_queue = document_embeddings_response_queue
default_subscriber = module
default_store_uri = 'http://localhost:19530'

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": DocumentEmbeddingsRequest,
                "output_schema": DocumentEmbeddingsResponse,
                "store_uri": store_uri,
            }
        )

        self.vecstore = DocVectors(store_uri)

    async def handle(self, msg):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling input {id}...", flush=True)

            chunks = []

            for vec in v.vectors:

                resp = self.vecstore.search(vec, limit=v.limit)

                for r in resp:
                    chunk = r["entity"]["doc"]
                    chunk = chunk.encode("utf-8")
                    chunks.append(chunk)

            print("Send response...", flush=True)
            r = DocumentEmbeddingsResponse(documents=chunks, error=None)
            await self.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = DocumentEmbeddingsResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                documents=None,
            )

            await self.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Milvus store URI (default: {default_store_uri})'
        )

def run():

    Processor.launch(module, __doc__)

