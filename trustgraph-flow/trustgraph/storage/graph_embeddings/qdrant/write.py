
"""
Accepts entity/vector pairs and writes them to a Qdrant store.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams
import uuid
import logging

from .... base import GraphEmbeddingsStoreService
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... schema import StorageManagementRequest, StorageManagementResponse, Error
from .... schema import vector_storage_management_topic, storage_management_response_topic

# Module logger
logger = logging.getLogger(__name__)

default_ident = "ge-write"

default_store_uri = 'http://localhost:6333'

class Processor(GraphEmbeddingsStoreService):

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
        """
        No-op for collection creation - collections are created lazily on first write
        with the correct dimension determined from the actual embeddings.
        """
        try:
            logger.info(f"Collection create request for {request.user}/{request.collection} - will be created lazily on first write")

            # Send success response
            response = StorageManagementResponse(error=None)
            await self.storage_response_producer.send(response)

        except Exception as e:
            logger.error(f"Failed to handle create collection request: {e}", exc_info=True)
            response = StorageManagementResponse(
                error=Error(
                    type="creation_error",
                    message=str(e)
                )
            )
            await self.storage_response_producer.send(response)

    async def handle_delete_collection(self, request):
        """
        Delete all dimension variants of the collection for graph embeddings.
        Since collections are created with dimension suffixes (e.g., t_user_coll_384),
        we need to find and delete all matching collections.
        """
        try:
            prefix = f"t_{request.user}_{request.collection}_"

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
                logger.info(f"Deleted {len(matching_collections)} collection(s) for {request.user}/{request.collection}")

            # Send success response
            response = StorageManagementResponse(
                error=None  # No error means success
            )
            await self.storage_response_producer.send(response)

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

def run():

    Processor.launch(default_ident, __doc__)

