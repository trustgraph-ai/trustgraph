
"""
Accepts entity/vector pairs and writes them to a Qdrant store.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams
import uuid
import logging

from .... base import DocumentEmbeddingsStoreService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "de-write"

default_store_uri = 'http://localhost:6333'

class Processor(DocumentEmbeddingsStoreService):

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

    async def store_document_embeddings(self, message):

        for emb in message.chunks:

            chunk = emb.chunk.decode("utf-8")
            if chunk == "": return

            for vec in emb.vectors:

                dim = len(vec)
                collection = (
                    "d_" + message.metadata.user + "_" +
                    message.metadata.collection + "_" +
                    str(dim)
                )

                if collection != self.last_collection:

                    if not self.qdrant.collection_exists(collection):

                        try:
                            self.qdrant.create_collection(
                                collection_name=collection,
                                vectors_config=VectorParams(
                                    size=dim, distance=Distance.COSINE
                                ),
                            )
                        except Exception as e:
                            logger.error("Qdrant collection creation failed")
                            raise e

                    self.last_collection = collection

                self.qdrant.upsert(
                    collection_name=collection,
                    points=[
                        PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vec,
                            payload={
                                "doc": chunk,
                            }
                        )
                    ]
                )

    @staticmethod
    def add_args(parser):

        DocumentEmbeddingsStoreService.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Qdrant URI (default: {default_store_uri})'
        )
        
        parser.add_argument(
            '-k', '--api-key',
            default=None,
            help=f'Qdrant API key (default: None)'
        )

def run():

    Processor.launch(default_ident, __doc__)

