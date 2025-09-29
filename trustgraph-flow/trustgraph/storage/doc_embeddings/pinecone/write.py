
"""
Accepts document chunks/vector pairs and writes them to a Pinecone store.
"""

from pinecone import Pinecone, ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig

import time
import uuid
import os
import logging

from .... base import DocumentEmbeddingsStoreService
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... schema import StorageManagementRequest, StorageManagementResponse, Error
from .... schema import vector_storage_management_topic, storage_management_response_topic

# Module logger
logger = logging.getLogger(__name__)

default_ident = "de-write"
default_api_key = os.getenv("PINECONE_API_KEY", "not-specified")
default_cloud = "aws"
default_region = "us-east-1"

class Processor(DocumentEmbeddingsStoreService):

    def __init__(self, **params):

        self.url = params.get("url", None)
        self.cloud = params.get("cloud", default_cloud)
        self.region = params.get("region", default_region)
        self.api_key = params.get("api_key", default_api_key)

        if self.api_key is None or self.api_key == "not-specified":
            raise RuntimeError("Pinecone API key must be specified")

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

                dim = len(vec)
                index_name = (
                    "d-" + message.metadata.user + "-" + message.metadata.collection
                )

                if index_name != self.last_index_name:

                    if not self.pinecone.has_index(index_name):

                        try:

                            self.create_index(index_name, dim)

                        except Exception as e:
                            logger.error("Pinecone index creation failed")
                            raise e

                        logger.info(f"Index {index_name} created")

                    self.last_index_name = index_name

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
            index_name = f"d-{message.user}-{message.collection}"

            if self.pinecone.has_index(index_name):
                self.pinecone.delete_index(index_name)
                logger.info(f"Deleted Pinecone index: {index_name}")
            else:
                logger.info(f"Index {index_name} does not exist, nothing to delete")

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

