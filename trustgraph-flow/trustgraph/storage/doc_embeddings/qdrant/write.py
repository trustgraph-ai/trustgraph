
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

    async def start(self):
        """Start the processor and its storage management consumer"""
        await super().start()
        if hasattr(self, 'storage_request_consumer'):
            await self.storage_request_consumer.start()
        if hasattr(self, 'storage_response_producer'):
            await self.storage_response_producer.start()

    async def store_document_embeddings(self, message):

        # Validate collection exists before accepting writes
        collection = (
            "d_" + message.metadata.user + "_" +
            message.metadata.collection
        )

        if not self.qdrant.collection_exists(collection):
            error_msg = (
                f"Collection {message.metadata.collection} does not exist. "
                f"Create it first with tg-set-collection."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        for emb in message.chunks:

            chunk = emb.chunk.decode("utf-8")
            if chunk == "": return

            for vec in emb.vectors:

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

    async def on_storage_management(self, message, consumer, flow):
        """Handle storage management requests"""
        request = message.value()
        logger.info(f"Storage management request: {request.operation} for {request.user}/{request.collection}")

        try:
            if request.operation == "create-collection":
                await self.handle_create_collection(request)
            elif request.operation == "delete-collection":
                await self.handle_delete_collection(request)
            else:
                response = StorageManagementResponse(
                    error=Error(
                        type="invalid_operation",
                        message=f"Unknown operation: {request.operation}"
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

    async def handle_create_collection(self, request):
        """Create a Qdrant collection for document embeddings"""
        try:
            collection_name = f"d_{request.user}_{request.collection}"

            if self.qdrant.collection_exists(collection_name):
                logger.info(f"Qdrant collection {collection_name} already exists")
            else:
                # Create collection with default dimension (will be recreated with correct dim on first write if needed)
                # Using a placeholder dimension - actual dimension determined by first embedding
                self.qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=384,  # Default dimension, common for many models
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {collection_name}")

            # Send success response
            response = StorageManagementResponse(error=None)
            await self.storage_response_producer.send(response)

        except Exception as e:
            logger.error(f"Failed to create collection: {e}", exc_info=True)
            response = StorageManagementResponse(
                error=Error(
                    type="creation_error",
                    message=str(e)
                )
            )
            await self.storage_response_producer.send(response)

    async def handle_delete_collection(self, request):
        """Delete the collection for document embeddings"""
        try:
            collection_name = f"d_{request.user}_{request.collection}"

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
            logger.info(f"Successfully deleted collection {request.user}/{request.collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

def run():

    Processor.launch(default_ident, __doc__)

