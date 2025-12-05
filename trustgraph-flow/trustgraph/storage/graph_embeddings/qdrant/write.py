
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

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
                "api_key": api_key,
            }
        )



        # Initialize collection config handler


        CollectionConfigHandler.__init__(self)



        # Register for config push notifications


        self.register_config_handler(self.on_collection_config)

        self.qdrant = QdrantClient(url=store_uri, api_key=api_key)

        # Set up storage management if base class attributes are available
        # (they may not be in unit tests)
        if hasattr(self, 'id') and hasattr(self, 'taskgroup') and hasattr(self, 'pulsar_client'):
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
        except Exception as e:
            logger.error(f"Error processing storage management request: {e}", exc_info=True)
            response = StorageManagementResponse(
                error=Error(
                    type="processing_error",
                    message=str(e)
                )
            )
            await self.storage_response_producer.send(response)

    async def create_collection(self, user: str, collection: str, metadata: dict):
        """
        No-op for collection creation - collections are created lazily on first write
        with the correct dimension determined from the actual embeddings.
        """
        try:
            logger.info(f"Collection create request for {user}/{collection} - will be created lazily on first write")
        except Exception as e:
            logger.error(f"Failed to handle create collection request: {e}", exc_info=True)
            response = StorageManagementResponse(
                error=Error(
                    type="creation_error",
                    message=str(e)
                )
            )
            await self.storage_response_producer.send(response)

    async def delete_collection(self, user: str, collection: str):
        """
        Delete all dimension variants of the collection for graph embeddings.
        Since collections are created with dimension suffixes (e.g., t_user_coll_384),
        we need to find and delete all matching collections.
        """
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

