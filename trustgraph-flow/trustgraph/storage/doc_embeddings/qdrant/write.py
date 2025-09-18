
"""
Accepts entity/vector pairs and writes them to a Qdrant store.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams
import uuid
import logging

from .... base import DocumentEmbeddingsStoreService
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... schema import StorageManagementRequest, StorageManagementResponse, Error
from .... schema import vector_storage_management_topic, storage_management_response_topic

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

        # Set up storage management if base class attributes are available
        # (they may not be in unit tests)
        if hasattr(self, 'id') and hasattr(self, 'taskgroup') and hasattr(self, 'pulsar_client'):
            # Set up metrics for storage management
            storage_request_metrics = ConsumerMetrics(
                processor=self.id, flow=None, name="storage-request"
            )
            storage_response_metrics = ProducerMetrics(
                processor=self.id, flow=None, name="storage-response"
            )

            # Set up consumer for storage management requests
            self.storage_request_consumer = Consumer(
                taskgroup=self.taskgroup,
                client=self.pulsar_client,
                flow=None,
                topic=vector_storage_management_topic,
                subscriber=f"{self.id}-storage",
                schema=StorageManagementRequest,
                handler=self.on_storage_management,
                metrics=storage_request_metrics,
            )

            # Set up producer for storage management responses
            self.storage_response_producer = Producer(
                client=self.pulsar_client,
                topic=storage_management_response_topic,
                schema=StorageManagementResponse,
                metrics=storage_response_metrics,
            )

    async def store_document_embeddings(self, message):

        for emb in message.chunks:

            chunk = emb.chunk.decode("utf-8")
            if chunk == "": return

            for vec in emb.vectors:

                dim = len(vec)
                collection = (
                    "d_" + message.metadata.user + "_" +
                    message.metadata.collection
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

    async def on_storage_management(self, message):
        """Handle storage management requests"""
        logger.info(f"Storage management request: {message.operation} for {message.user}/{message.collection}")

        try:
            if message.operation == "delete-collection":
                await self.handle_delete_collection(message)
            else:
                response = StorageManagementResponse(
                    error=Error(
                        type="invalid_operation",
                        message=f"Unknown operation: {message.operation}"
                    )
                )
                await self.storage_response_producer.send(response)

        except Exception as e:
            logger.error(f"Error processing storage management request: {e}", exc_info=True)
            response = StorageManagementResponse(
                error=Error(
                    type="processing_error",
                    message=str(e)
                )
            )
            await self.storage_response_producer.send(response)

    async def handle_delete_collection(self, message):
        """Delete the collection for document embeddings"""
        try:
            collection_name = f"d_{message.user}_{message.collection}"

            if self.qdrant.collection_exists(collection_name):
                self.qdrant.delete_collection(collection_name)
                logger.info(f"Deleted Qdrant collection: {collection_name}")
            else:
                logger.info(f"Collection {collection_name} does not exist, nothing to delete")

            # Send success response
            response = StorageManagementResponse(
                error=None  # No error means success
            )
            await self.storage_response_producer.send(response)
            logger.info(f"Successfully deleted collection {message.user}/{message.collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

def run():

    Processor.launch(default_ident, __doc__)

