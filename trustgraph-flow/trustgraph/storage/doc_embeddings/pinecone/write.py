
"""
Accepts document chunks/vector pairs and writes them to a Pinecone store.
"""

from pinecone import Pinecone, ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig

import time
import uuid
import os
import logging

from .... base import DocumentEmbeddingsStoreService, CollectionConfigHandler
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "de-write"
default_api_key = os.getenv("PINECONE_API_KEY", "not-specified")
default_cloud = "aws"
default_region = "us-east-1"

class Processor(CollectionConfigHandler, DocumentEmbeddingsStoreService):

    def __init__(self, **params):

        self.url = params.get("url", None)
        self.cloud = params.get("cloud", default_cloud)
        self.region = params.get("region", default_region)
        self.api_key = params.get("api_key", default_api_key)

        if self.api_key is None or self.api_key == "not-specified":
            raise RuntimeError("Pinecone API key must be specified")

        # Initialize collection config handler
        CollectionConfigHandler.__init__(self)

        if self.url:

            self.pinecone = PineconeGRPC(
                api_key = self.api_key,
                host = self.url
            )

        else:

            self.pinecone = Pinecone(api_key = self.api_key)

        super(Processor, self).__init__(
            **params | {
                "url": self.url,
                "cloud": self.cloud,
                "region": self.region,
                "api_key": self.api_key,
            }
        )

        self.last_index_name = None

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config)

    def create_index(self, index_name, dim):

        self.pinecone.create_index(
            name = index_name,
            dimension = dim,
            metric = "cosine",
            spec = ServerlessSpec(
                cloud = self.cloud,
                region = self.region,
            )
        )

        for i in range(0, 1000):

            if self.pinecone.describe_index(
                    index_name
            ).status["ready"]:
                break

            time.sleep(1)

        if not self.pinecone.describe_index(
                index_name
        ).status["ready"]:
            raise RuntimeError(
                "Gave up waiting for index creation"
            )

    async def store_document_embeddings(self, message):

        for emb in message.chunks:

            if emb.chunk is None or emb.chunk == b"": continue

            chunk = emb.chunk.decode("utf-8")
            if chunk == "": continue

            for vec in emb.vectors:

                # Create index name with dimension suffix for lazy creation
                dim = len(vec)
                index_name = (
                    f"d-{message.metadata.user}-{message.metadata.collection}-{dim}"
                )

                # Lazily create index if it doesn't exist
                if not self.pinecone.has_index(index_name):
                    logger.info(f"Lazily creating Pinecone index {index_name} with dimension {dim}")
                    self.create_index(index_name, dim)

                index = self.pinecone.Index(index_name)

                # Generate unique ID for each vector
                vector_id = str(uuid.uuid4())

                records = [
                    {
                        "id": vector_id,
                        "values": vec,
                        "metadata": { "doc": chunk },
                    }
                ]

                index.upsert(
                    vectors = records,
                )

    @staticmethod
    def add_args(parser):

        DocumentEmbeddingsStoreService.add_args(parser)

        parser.add_argument(
            '-a', '--api-key',
            default=default_api_key,
            help='Pinecone API key. (default from PINECONE_API_KEY)'
        )

        parser.add_argument(
            '-u', '--url',
            help='Pinecone URL.  If unspecified, serverless is used'
        )

        parser.add_argument(
            '--cloud',
            default=default_cloud,
            help=f'Pinecone cloud, (default: {default_cloud}'
        )

        parser.add_argument(
            '--region',
            default=default_region,
            help=f'Pinecone region, (default: {default_region}'
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
        No-op for collection creation - indexes are created lazily on first write
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
        Delete all dimension variants of the index for document embeddings.
        Since indexes are created with dimension suffixes (e.g., d-user-coll-384),
        we need to find and delete all matching indexes.
        """
        try:
            prefix = f"d-{request.user}-{request.collection}-"

            # Get all indexes and filter for matches
            all_indexes = self.pinecone.list_indexes()
            matching_indexes = [
                idx.name for idx in all_indexes
                if idx.name.startswith(prefix)
            ]

            if not matching_indexes:
                logger.info(f"No indexes found matching prefix {prefix}")
            else:
                for index_name in matching_indexes:
                    self.pinecone.delete_index(index_name)
                    logger.info(f"Deleted Pinecone index: {index_name}")
                logger.info(f"Deleted {len(matching_indexes)} index(es) for {request.user}/{request.collection}")

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

