
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

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = graph_embeddings_store_queue
default_subscriber = module
default_store_uri = 'http://localhost:6333'

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

        self.last_collection = None
        self.last_dim = None

        self.client = QdrantClient(url=store_uri)

    def handle(self, msg):

        v = msg.value()

        if v.entity.value == "" or v.entity.value is None: return

        for vec in v.vectors:

            dim = len(vec)
            collection = (
                "t_" + v.metadata.user + "_" + v.metadata.collection +
                str(dim)
            )

            if dim != self.last_dim:

                if not self.client.collection_exists(collection):

                    try:
                        self.client.create_collection(
                            collection_name=collection,
                            vectors_config=VectorParams(
                                size=dim, distance=Distance.DOT
                            ),
                        )
                    except Exception as e:
                        print("Qdrant collection creation failed")
                        raise e

                self.last_collection = collection
                self.last_dim = dim

            self.client.upsert(
                collection_name=collection,
                points=[
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vec,
                        payload={
                            "entity": v.entity.value,
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

def run():

    Processor.start(module, __doc__)

