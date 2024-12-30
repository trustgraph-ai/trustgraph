
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

from .... schema import GraphEmbeddings
from .... schema import graph_embeddings_store_queue
from .... log_level import LogLevel
from .... direct.milvus_graph_embeddings import EntityVectors
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

        self.vecstore = EntityVectors(store_uri)

    def handle(self, msg):

        v = msg.value()

        for entity in v.entities:

            if entity.entity.value != "" and entity.entity.value is not None:
                for vec in entity.vectors:
                    self.vecstore.insert(vec, entity.entity.value)

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

