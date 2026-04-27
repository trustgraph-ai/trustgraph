
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

import logging

from .... direct.milvus_doc_embeddings import DocVectors
from .... base import DocumentEmbeddingsStoreService, CollectionConfigHandler
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "doc-embeddings-write"
default_store_uri = 'http://localhost:19530'

class Processor(CollectionConfigHandler, DocumentEmbeddingsStoreService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
            }
        )

        self.vecstore = DocVectors(store_uri)

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config, types=["collection"])

    async def store_document_embeddings(self, workspace, message):

        for emb in message.chunks:

            chunk_id = emb.chunk_id
            if chunk_id == "":
                continue

            vec = emb.vector
            if vec:
                self.vecstore.insert(
                    vec, chunk_id,
                    workspace,
                    message.metadata.collection
                )

    @staticmethod
    def add_args(parser):

        DocumentEmbeddingsStoreService.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Milvus store URI (default: {default_store_uri})'
        )

    async def create_collection(self, workspace: str, collection: str, metadata: dict):
        """
        Create collection via config push - collections are created lazily on first write
        with the correct dimension determined from the actual embeddings.
        """
        try:
            logger.info(f"Collection create request for {workspace}/{collection} - will be created lazily on first write")
            self.vecstore.create_collection(workspace, collection)

        except Exception as e:
            logger.error(f"Failed to create collection {workspace}/{collection}: {e}", exc_info=True)
            raise

    async def delete_collection(self, workspace: str, collection: str):
        """Delete the collection for document embeddings via config push"""
        try:
            self.vecstore.delete_collection(workspace, collection)
            logger.info(f"Successfully deleted collection {workspace}/{collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection {workspace}/{collection}: {e}", exc_info=True)
            raise

def run():

    Processor.launch(default_ident, __doc__)

