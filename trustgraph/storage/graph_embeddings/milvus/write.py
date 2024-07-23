
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

from .... schema import GraphEmbeddings
from .... schema import graph_embeddings_store_queue
from .... log_level import LogLevel
from .... triple_vectors import TripleVectors
from .... base import Consumer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = graph_embeddings_store_queue
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
                "input_schema": GraphEmbeddings,
                "store_uri": store_uri,
            }
        )

        self.vecstore = TripleVectors(store_uri)

    def handle(self, msg):

        v = msg.value()

        if v.entity.value != "":
            for vec in v.vectors:
                self.vecstore.insert(vec, v.entity.value)

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

        parser.add_argument(
            '-t', '--store-uri',
            default="http://milvus:19530",
            help=f'Milvus store URI (default: http://milvus:19530)'
        )

def run():

    Processor.start(module, __doc__)

