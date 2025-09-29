
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

import logging

from .... direct.milvus_doc_embeddings import DocVectors
from .... base import DocumentEmbeddingsStoreService
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... schema import StorageManagementRequest, StorageManagementResponse, Error
from .... schema import vector_storage_management_topic, storage_management_response_topic

# Module logger
logger = logging.getLogger(__name__)

default_ident = "de-write"
default_store_uri = 'http://localhost:19530'

class Processor(DocumentEmbeddingsStoreService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
            }
        )

        self.vecstore = DocVectors(store_uri)

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
        await self.storage_request_consumer.start()
        await self.storage_response_producer.start()

    async def store_document_embeddings(self, message):

        for emb in message.chunks:

            if emb.chunk is None or emb.chunk == b"": continue
            
            chunk = emb.chunk.decode("utf-8")
            if chunk == "": continue

            for vec in emb.vectors:
                self.vecstore.insert(
                    vec, chunk, 
                    message.metadata.user, 
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

    async def on_storage_management(self, message, consumer, flow):
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
            self.vecstore.delete_collection(message.user, message.collection)

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

