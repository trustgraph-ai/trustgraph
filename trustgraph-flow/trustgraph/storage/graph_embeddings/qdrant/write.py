
"""
Accepts entity/vector pairs and writes them to a Qdrant store.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams
import uuid
import logging

from .... base import GraphEmbeddingsStoreService, CollectionConfigHandler
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "ge-write"

default_store_uri = 'http://localhost:6333'

class Processor(CollectionConfigHandler, GraphEmbeddingsStoreService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)
        api_key = params.get("api_key", None)

        # Initialize collection config handler
        CollectionConfigHandler.__init__(self)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
                "api_key": api_key,
            }
        )

        self.qdrant = QdrantClient(url=store_uri, api_key=api_key)

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config)

    async def store_graph_embeddings(self, message):

        for entity in message.entities:

            if entity.entity.value == "" or entity.entity.value is None: return

            for vec in entity.vectors:

                # Create collection name with dimension suffix for lazy creation
                dim = len(vec)
                collection = (
                    f"t_{message.metadata.user}_{message.metadata.collection}_{dim}"
                )

                # Lazily create collection if it doesn't exist
                if not self.qdrant.collection_exists(collection):
                    logger.info(f"Lazily creating Qdrant collection {collection} with dimension {dim}")
                    self.qdrant.create_collection(
                        collection_name=collection,
                        vectors_config=VectorParams(
                            size=dim,
                            distance=Distance.COSINE
                        )
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

    async def create_collection(self, user: str, collection: str, metadata: dict):
        """
        Create collection via config push - collections are created lazily on first write
        with the correct dimension determined from the actual embeddings.
        """
        try:
            logger.info(f"Collection create request for {user}/{collection} - will be created lazily on first write")

        except Exception as e:
            logger.error(f"Failed to create collection {user}/{collection}: {e}", exc_info=True)
            raise

    async def delete_collection(self, user: str, collection: str):
        """Delete the collection for graph embeddings via config push"""
        try:
            prefix = f"t_{user}_{collection}_"

            # Get all collections and filter for matches
            all_collections = self.qdrant.get_collections().collections
            matching_collections = [
                coll.name for coll in all_collections
                if coll.name.startswith(prefix)
            ]

            if not matching_collections:
                logger.info(f"No collections found matching prefix {prefix}")
            else:
                for collection_name in matching_collections:
                    self.qdrant.delete_collection(collection_name)
                    logger.info(f"Deleted Qdrant collection: {collection_name}")
                logger.info(f"Deleted {len(matching_collections)} collection(s) for {user}/{collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection {user}/{collection}: {e}", exc_info=True)
            raise

def run():

    Processor.launch(default_ident, __doc__)

