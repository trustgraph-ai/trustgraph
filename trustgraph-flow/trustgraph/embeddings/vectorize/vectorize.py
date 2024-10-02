
"""
Vectorizer, calls the embeddings service to get embeddings for a chunk.
Input is text chunk, output is chunk and vectors.
"""

from ... schema import Chunk, ChunkEmbeddings
from ... schema import chunk_ingest_queue, chunk_embeddings_ingest_queue
from ... schema import embeddings_request_queue, embeddings_response_queue
from ... clients.embeddings_client import EmbeddingsClient
from ... log_level import LogLevel
from ... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = chunk_ingest_queue
default_output_queue = chunk_embeddings_ingest_queue
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
                "output_schema": ChunkEmbeddings,
            }
        )

        self.embeddings = EmbeddingsClient(
            pulsar_host=self.pulsar_host,
            input_queue=emb_request_queue,
            output_queue=emb_response_queue,
            subscriber=module + "-emb",
        )

    def emit(self, metadata, chunk, vectors):

        r = ChunkEmbeddings(metadata=metadata, chunk=chunk, vectors=vectors)
        self.producer.send(r)

    def handle(self, msg):

        v = msg.value()
        print(f"Indexing {v.metadata.id}...", flush=True)

        chunk = v.chunk.decode("utf-8")

        try:

            vectors = self.embeddings.request(chunk)

            self.emit(
                metadata=v.metadata,
                chunk=chunk.encode("utf-8"),
                vectors=vectors
            )

        except Exception as e:
            print("Exception:", e, flush=True)

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

