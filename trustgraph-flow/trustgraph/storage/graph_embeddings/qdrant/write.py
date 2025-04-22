
"""
Accepts entity/vector pairs and writes them to a Qdrant store.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams
import uuid

from .... base import GraphEmbeddingsStoreService

default_ident = "ge-write"

default_store_uri = 'http://localhost:6333'

class Processor(GraphEmbeddingsStoreService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)
        api_key = params.get("api_key", None)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
                "api_key": api_key,
            }
        )

        self.last_collection = None

        self.qdrant = QdrantClient(url=store_uri, api_key=api_key)

    def get_collection(self, dim, user, collection):

        cname = (
            "t_" + user + "_" + collection + "_" + str(dim)
        )

        if cname != self.last_collection:

            if not self.qdrant.collection_exists(cname):

                try:
                    self.qdrant.create_collection(
                        collection_name=cname,
                        vectors_config=VectorParams(
                            size=dim, distance=Distance.COSINE
                        ),
                    )
                except Exception as e:
                    print("Qdrant collection creation failed")
                    raise e

            self.last_collection = cname

        return cname

    async def store_graph_embeddings(self, message):

        for entity in message.entities:

            if entity.entity.value == "" or entity.entity.value is None: return

            for vec in entity.vectors:

                dim = len(vec)

                collection = self.get_collection(
                    dim, message.metadata.user, message.metadata.collection
                )

                self.qdrant.upsert(
                    collection_name=collection,
                    points=[
                        PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vec,
                            payload={
                                "entity": entity.entity.value,
                            }
                        )
                    ]
                )

    @staticmethod
    def add_args(parser):

        GraphEmbeddingsStoreService.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Qdrant store URI (default: {default_store_uri})'
        )
        
        parser.add_argument(
            '-k', '--api-key',
            default=None,
            help=f'Qdrant API key'
        )

def run():

    Processor.launch(default_ident, __doc__)

