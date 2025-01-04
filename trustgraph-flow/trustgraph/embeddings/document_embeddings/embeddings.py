
"""
Document embeddings, calls the embeddings service to get embeddings for a
chunk of text.  Input is chunk of text plus metadata.
Output is chunk plus embedding.
"""

from ... schema import Chunk, ChunkEmbeddings, DocumentEmbeddings
from ... schema import chunk_ingest_queue
from ... schema import document_embeddings_store_queue
from ... schema import embeddings_request_queue, embeddings_response_queue
from ... clients.embeddings_client import EmbeddingsClient
from ... log_level import LogLevel
from ... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = chunk_ingest_queue
default_output_queue = document_embeddings_store_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        emb_request_queue = params.get(
            "embeddings_request_queue", embeddings_request_queue
        )
        emb_response_queue = params.get(
            "embeddings_response_queue", embeddings_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "embeddings_request_queue": emb_request_queue,
                "embeddings_response_queue": emb_response_queue,
                "subscriber": subscriber,
                "input_schema": Chunk,
                "output_schema": DocumentEmbeddings,
            }
        )

        self.embeddings = EmbeddingsClient(
            pulsar_host=self.pulsar_host,
            input_queue=emb_request_queue,
            output_queue=emb_response_queue,
            subscriber=module + "-emb",
        )

    def handle(self, msg):

        v = msg.value()
        print(f"Indexing {v.metadata.id}...", flush=True)

        try:

            vectors = self.embeddings.request(v.chunk)

            embeds = [
                ChunkEmbeddings(
                    chunk=v.chunk,
                    vectors=vectors,
                )
            ]

            r = DocumentEmbeddings(
                metadata=v.metadata,
                chunks=embeds,
            )

            self.producer.send(r)

        except Exception as e:
            print("Exception:", e, flush=True)

            # Retry
            raise e

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '--embeddings-request-queue',
            default=embeddings_request_queue,
            help=f'Embeddings request queue (default: {embeddings_request_queue})',
        )

        parser.add_argument(
            '--embeddings-response-queue',
            default=embeddings_response_queue,
            help=f'Embeddings request queue (default: {embeddings_response_queue})',
        )

def run():

    Processor.start(module, __doc__)

