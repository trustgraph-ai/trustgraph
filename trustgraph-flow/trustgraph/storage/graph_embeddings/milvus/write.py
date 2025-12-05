
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

import logging

from .... direct.milvus_graph_embeddings import EntityVectors
from .... base import GraphEmbeddingsStoreService, CollectionConfigHandler
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "ge-write"
default_store_uri = 'http://localhost:19530'

class Processor(CollectionConfigHandler, GraphEmbeddingsStoreService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)

        # Initialize collection config handler
        CollectionConfigHandler.__init__(self)

        # Initialize service base class
        GraphEmbeddingsStoreService.__init__(
            self,
            **params | {
                "store_uri": store_uri,
            }
        )

        self.vecstore = EntityVectors(store_uri)

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config)

    async def store_graph_embeddings(self, message):

        # Validate collection exists before accepting writes
        if not self.collection_exists(message.metadata.user, message.metadata.collection):
            error_msg = (
                f"Collection {message.metadata.collection} does not exist. "
                f"Create it first via collection management API."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

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

    async def create_collection(self, user: str, collection: str, metadata: dict):
        """
        Create collection via config push - collections are created lazily on first write
        with the correct dimension determined from the actual embeddings.
        """
        try:
            logger.info(f"Collection create request for {user}/{collection} - will be created lazily on first write")
            self.vecstore.create_collection(user, collection)

        except Exception as e:
            logger.error(f"Failed to create collection {user}/{collection}: {e}", exc_info=True)
            raise

    async def delete_collection(self, user: str, collection: str):
        """Delete the collection for graph embeddings via config push"""
        try:
            self.vecstore.delete_collection(user, collection)
            logger.info(f"Successfully deleted collection {user}/{collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection {user}/{collection}: {e}", exc_info=True)
            raise

def run():

    Processor.launch(default_ident, __doc__)

