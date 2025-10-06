
"""
Accepts entity/vector pairs and writes them to a Pinecone store.
"""

from pinecone import Pinecone, ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig

import time
import uuid
import os
import logging

from .... base import GraphEmbeddingsStoreService
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... schema import StorageManagementRequest, StorageManagementResponse, Error
from .... schema import vector_storage_management_topic, storage_management_response_topic

# Module logger
logger = logging.getLogger(__name__)

default_ident = "ge-write"
default_api_key = os.getenv("PINECONE_API_KEY", "not-specified")
default_cloud = "aws"
default_region = "us-east-1"

class Processor(GraphEmbeddingsStoreService):

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

    async def store_graph_embeddings(self, message):

        index_name = (
            "t-" + message.metadata.user + "-" + message.metadata.collection
        )

        # Validate collection exists before accepting writes
        if not self.pinecone.has_index(index_name):
            error_msg = (
                f"Collection {message.metadata.collection} does not exist. "
                f"Create it first with tg-set-collection."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        for entity in message.entities:

            if entity.entity.value == "" or entity.entity.value is None:
                continue

            for vec in entity.vectors:

                index = self.pinecone.Index(index_name)

                # Generate unique ID for each vector
                vector_id = str(uuid.uuid4())

                records = [
                    {
                        "id": vector_id,
                        "values": vec,
                        "metadata": { "entity": entity.entity.value },
                    }
                ]

                index.upsert(
                    vectors = records,
                )

    @staticmethod
    def add_args(parser):

        GraphEmbeddingsStoreService.add_args(parser)

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
        """Create a Pinecone index for graph embeddings"""
        try:
            index_name = f"t-{request.user}-{request.collection}"

            if self.pinecone.has_index(index_name):
                logger.info(f"Pinecone index {index_name} already exists")
            else:
                # Create with default dimension - will need to be recreated if dimension doesn't match
                self.create_index(index_name, dim=384)
                logger.info(f"Created Pinecone index: {index_name}")

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
        """Delete the collection for graph embeddings"""
        try:
            index_name = f"t-{request.user}-{request.collection}"

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
            logger.info(f"Successfully deleted collection {request.user}/{request.collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

def run():

    Processor.launch(default_ident, __doc__)

