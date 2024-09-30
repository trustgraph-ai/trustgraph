
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

from .... schema import ChunkEmbeddings
from .... schema import chunk_embeddings_ingest_queue
from .... log_level import LogLevel
from .... direct.milvus_doc_embeddings import DocVectors
from .... base import Consumer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = chunk_embeddings_ingest_queue
default_subscriber = module
default_store_uri = 'http://localhost:19530'

class Processor(Consumer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": ChunkEmbeddings,
                "store_uri": store_uri,
            }
        )

        self.vecstore = DocVectors(store_uri)

    def handle(self, msg):

        v = msg.value()

        chunk = v.chunk.decode("utf-8")

        if v.chunk != "" and v.chunk is not None:
            for vec in v.vectors:
                self.vecstore.insert(vec, chunk)

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Milvus store URI (default: {default_store_uri})'
        )

def run():

    Processor.start(module, __doc__)

