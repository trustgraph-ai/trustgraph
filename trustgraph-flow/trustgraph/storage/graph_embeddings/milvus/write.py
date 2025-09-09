
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

from .... direct.milvus_graph_embeddings import EntityVectors
from .... base import GraphEmbeddingsStoreService

default_ident = "ge-write"
default_store_uri = 'http://localhost:19530'

class Processor(GraphEmbeddingsStoreService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
            }
        )

        self.vecstore = EntityVectors(store_uri)

    async def store_graph_embeddings(self, message):

        for entity in message.entities:

            if entity.entity.value != "" and entity.entity.value is not None:
                for vec in entity.vectors:
                    self.vecstore.insert(
                        vec, entity.entity.value,
                        message.metadata.user,
                        message.metadata.collection
                    )

    @staticmethod
    def add_args(parser):

        GraphEmbeddingsStoreService.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Milvus store URI (default: {default_store_uri})'
        )

def run():

    Processor.launch(default_ident, __doc__)

