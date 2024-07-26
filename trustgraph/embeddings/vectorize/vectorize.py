
"""
Vectorizer, calls the embeddings service to get embeddings for a chunk.
Input is text chunk, output is chunk and vectors.
"""

from ... schema import Chunk, ChunkEmbeddings
from ... schema import chunk_ingest_queue, chunk_embeddings_ingest_queue
from ... embeddings_client import EmbeddingsClient
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

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": Chunk,
                "output_schema": ChunkEmbeddings,
            }
        )

        self.embeddings = EmbeddingsClient(
            pulsar_host=self.pulsar_host,
            subscriber=module + "-emb",
        )

    def emit(self, source, chunk, vectors):

        r = ChunkEmbeddings(source=source, chunk=chunk, vectors=vectors)
        self.producer.send(r)

    def handle(self, msg):

        v = msg.value()
        print(f"Indexing {v.source.id}...", flush=True)

        chunk = v.chunk.decode("utf-8")

        try:

            vectors = self.embeddings.request(chunk)

            self.emit(
                source=v.source,
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

def run():

    Processor.start(module, __doc__)

