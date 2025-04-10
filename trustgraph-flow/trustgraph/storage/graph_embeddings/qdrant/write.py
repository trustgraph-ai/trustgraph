
"""
Accepts entity/vector pairs and writes them to a Qdrant store.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams
import uuid

from .... schema import GraphEmbeddings
from .... schema import graph_embeddings_store_queue
from .... log_level import LogLevel
from .... base import Consumer

module = "ge-write"

default_input_queue = graph_embeddings_store_queue
default_subscriber = module
default_store_uri = 'http://localhost:6333'

class Processor(Consumer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        store_uri = params.get("store_uri", default_store_uri)
        api_key = params.get("api_key", None)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": GraphEmbeddings,
                "store_uri": store_uri,
                "api_key": api_key,
            }
        )

        self.last_collection = None

        self.client = QdrantClient(url=store_uri, api_key=api_key)

    def get_collection(self, dim, user, collection):

        cname = (
            "t_" + user + "_" + collection + "_" + str(dim)
        )

        if cname != self.last_collection:

            if not self.client.collection_exists(cname):

                try:
                    self.client.create_collection(
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

    async def handle(self, msg):

        v = msg.value()

        for entity in v.entities:

            if entity.entity.value == "" or entity.entity.value is None: return

            for vec in entity.vectors:

                dim = len(vec)

                collection = self.get_collection(
                    dim, v.metadata.user, v.metadata.collection
                )

                self.client.upsert(
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

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

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

    Processor.launch(module, __doc__)

