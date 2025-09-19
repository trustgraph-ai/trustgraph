"""
Collection management service for the librarian
"""

import asyncio
import logging
from datetime import datetime

from .. base import AsyncProcessor, Consumer, Producer
from .. base import ConsumerMetrics, ProducerMetrics
from .. base.cassandra_config import add_cassandra_args, resolve_cassandra_config

from .. schema import CollectionManagementRequest, CollectionManagementResponse, Error
from .. schema import collection_request_queue, collection_response_queue
from .. schema import CollectionMetadata
from .. schema import StorageManagementRequest, StorageManagementResponse
from .. schema import vector_storage_management_topic, object_storage_management_topic, triples_storage_management_topic, storage_management_response_topic

from .. exceptions import RequestError
from .. tables.library import LibraryTableStore

# Module logger
logger = logging.getLogger(__name__)

default_ident = "collection-management"
default_cassandra_host = "cassandra"
keyspace = "librarian"

class Processor(AsyncProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        # Get Cassandra configuration
        cassandra_host = params.get("cassandra_host", default_cassandra_host)
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password
        )

        super(Processor, self).__init__(
            **params | {
                "cassandra_host": ','.join(hosts),
                "cassandra_username": username
            }
        )

        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password

        # Set up metrics
        collection_request_metrics = ConsumerMetrics(
            processor=self.id, flow=None, name="collection-request"
        )
        collection_response_metrics = ProducerMetrics(
            processor=self.id, flow=None, name="collection-response"
        )

        # Set up consumer for collection management requests
        self.collection_request_consumer = Consumer(
            taskgroup=self.taskgroup,
            client=self.pulsar_client,
            flow=None,
            topic=collection_request_queue,
            subscriber=id,
            schema=CollectionManagementRequest,
            handler=self.on_collection_request,
            metrics=collection_request_metrics,
        )

        # Set up producer for collection management responses
        self.collection_response_producer = Producer(
            client=self.pulsar_client,
            topic=collection_response_queue,
            schema=CollectionManagementResponse,
            metrics=collection_response_metrics,
        )

        # Set up producers for storage management requests
        self.vector_storage_producer = Producer(
            client=self.pulsar_client,
            topic=vector_storage_management_topic,
            schema=StorageManagementRequest,
        )

        self.object_storage_producer = Producer(
            client=self.pulsar_client,
            topic=object_storage_management_topic,
            schema=StorageManagementRequest,
        )

        self.triples_storage_producer = Producer(
            client=self.pulsar_client,
            topic=triples_storage_management_topic,
            schema=StorageManagementRequest,
        )

        # Set up consumer for storage management responses
        storage_response_metrics = ConsumerMetrics(
            processor=self.id, flow=None, name="storage-response"
        )

        self.storage_response_consumer = Consumer(
            taskgroup=self.taskgroup,
            client=self.pulsar_client,
            flow=None,
            topic=storage_management_response_topic,
            subscriber=f"{id}-storage",
            schema=StorageManagementResponse,
            handler=self.on_storage_response,
            metrics=storage_response_metrics,
        )

        # Initialize table store
        self.table_store = LibraryTableStore(
            cassandra_host=self.cassandra_host,
            cassandra_username=self.cassandra_username,
            cassandra_password=self.cassandra_password,
            keyspace=keyspace
        )

        # Track pending deletion requests by user+collection
        self.pending_deletions = {}  # (user, collection) -> {responses_pending, responses_received, all_successful, error_messages, deletion_complete}

    async def on_collection_request(self, message):
        """Handle collection management requests"""

        logger.debug(f"Collection request: {message.operation}")

        try:
            if message.operation == "list-collections":
                response = await self.handle_list_collections(message)
            elif message.operation == "update-collection":
                response = await self.handle_update_collection(message)
            elif message.operation == "delete-collection":
                response = await self.handle_delete_collection(message)
            else:
                response = CollectionManagementResponse(
                    success="false",
                    error=Error(
                        type="invalid_operation",
                        message=f"Unknown operation: {message.operation}"
                    ),
                    timestamp=datetime.now().isoformat()
                )

        except Exception as e:
            logger.error(f"Error processing collection request: {e}", exc_info=True)
            response = CollectionManagementResponse(
                success="false",
                error=Error(
                    type="processing_error",
                    message=str(e)
                ),
                timestamp=datetime.now().isoformat()
            )

        await self.collection_response_producer.send(response)

    async def on_storage_response(self, response):
        """Handle storage management responses"""
        logger.debug(f"Received storage response: error={response.error}")

        # Find matching deletion by checking all pending deletions
        # Note: This is simplified correlation - assumes responses come back quickly
        # In production, we'd want better correlation mechanism
        for deletion_key, info in list(self.pending_deletions.items()):
            if info["responses_pending"] > 0:
                # Record this response
                info["responses_received"].append(response)
                info["responses_pending"] -= 1

                # Check if this response indicates failure
                if response.error and response.error.message:
                    info["all_successful"] = False
                    info["error_messages"].append(response.error.message)
                    logger.warning(f"Storage deletion failed for {deletion_key}: {response.error.message}")
                else:
                    logger.debug(f"Storage deletion succeeded for {deletion_key}")

                # If all responses received, signal completion
                if info["responses_pending"] == 0:
                    logger.info(f"All storage responses received for {deletion_key}")
                    info["deletion_complete"].set()

                break  # Only process for first matching deletion

        # For now, we'll correlate by user+collection since we don't have deletion_id in the response
        # This is a simplified approach - in production we'd want better correlation
        for deletion_id, info in list(self.pending_deletions.items()):
            if info["responses_pending"] > 0:
                # Record this response
                info["responses_received"].append(response)
                info["responses_pending"] -= 1

                # Check if this response indicates failure
                if response.error and response.error.message:
                    info["all_successful"] = False
                    info["error_messages"].append(response.error.message)
                    logger.warning(f"Storage deletion failed for {deletion_id}: {response.error.message}")

                # If all responses received, signal completion
                if info["responses_pending"] == 0:
                    logger.info(f"All storage responses received for {deletion_id}")
                    info["deletion_complete"].set()

                break  # Only process for first matching deletion

    async def handle_list_collections(self, message):
        """Handle list collections request"""
        try:
            tag_filter = list(message.tag_filter) if message.tag_filter else None
            collections = await self.table_store.list_collections(message.user, tag_filter)

            collection_metadata = [
                CollectionMetadata(
                    user=coll["user"],
                    collection=coll["collection"],
                    name=coll["name"],
                    description=coll["description"],
                    tags=coll["tags"],
                    created_at=coll["created_at"],
                    updated_at=coll["updated_at"]
                )
                for coll in collections
            ]

            return CollectionManagementResponse(
                success="true",
                collections=collection_metadata,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            raise

    async def handle_update_collection(self, message):
        """Handle update collection request"""
        try:
            # Extract fields for update
            name = message.name if message.name else None
            description = message.description if message.description else None
            tags = list(message.tags) if message.tags else None

            updated_collection = await self.table_store.update_collection(
                message.user, message.collection, name, description, tags
            )

            collection_metadata = CollectionMetadata(
                user=updated_collection["user"],
                collection=updated_collection["collection"],
                name=updated_collection["name"],
                description=updated_collection["description"],
                tags=updated_collection["tags"],
                created_at="",  # Not returned by update
                updated_at=updated_collection["updated_at"]
            )

            return CollectionManagementResponse(
                success="true",
                collections=[collection_metadata],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error updating collection: {e}")
            raise

    async def handle_delete_collection(self, message):
        """Handle delete collection request with cascade to all storage types"""
        try:
            deletion_key = (message.user, message.collection)

            logger.info(f"Starting cascade deletion for {message.user}/{message.collection}")

            # Track this deletion request
            self.pending_deletions[deletion_key] = {
                "responses_pending": 3,  # vector, object, triples
                "responses_received": [],
                "all_successful": True,
                "error_messages": [],
                "deletion_complete": asyncio.Event()
            }

            # Create storage management request
            storage_request = StorageManagementRequest(
                operation="delete-collection",
                user=message.user,
                collection=message.collection
            )

            # Send delete requests to all three storage types
            await self.vector_storage_producer.send(storage_request)
            await self.object_storage_producer.send(storage_request)
            await self.triples_storage_producer.send(storage_request)

            logger.info(f"Storage deletion requests sent for {message.user}/{message.collection}")

            # Wait for all storage responses (with timeout)
            try:
                await asyncio.wait_for(
                    self.pending_deletions[deletion_key]["deletion_complete"].wait(),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for storage responses for {deletion_key}")
                self.pending_deletions[deletion_key]["all_successful"] = False
                self.pending_deletions[deletion_key]["error_messages"].append("Timeout waiting for storage responses")

            # Check if all storage deletions were successful
            deletion_info = self.pending_deletions.pop(deletion_key, {})

            if deletion_info.get("all_successful", False):
                # All storage deletions succeeded, now delete metadata
                await self.table_store.delete_collection_metadata(message.user, message.collection)
                logger.info(f"Successfully completed cascade deletion for {message.user}/{message.collection}")

                return CollectionManagementResponse(
                    success="true",
                    timestamp=datetime.now().isoformat()
                )
            else:
                # Some storage deletions failed
                error_messages = deletion_info.get("error_messages", ["Unknown storage deletion error"])
                error_msg = "; ".join(error_messages)
                logger.error(f"Cascade deletion failed for {deletion_key}: {error_msg}")

                return CollectionManagementResponse(
                    success="false",
                    error=Error(
                        type="storage_deletion_error",
                        message=f"Storage deletion failed: {error_msg}"
                    ),
                    timestamp=datetime.now().isoformat()
                )

        except Exception as e:
            logger.error(f"Error in cascade deletion: {e}")
            return CollectionManagementResponse(
                success="false",
                error=Error(
                    type="deletion_error",
                    message=f"Failed to delete collection: {str(e)}"
                ),
                timestamp=datetime.now().isoformat()
            )

    @staticmethod
    def add_args(parser):
        AsyncProcessor.add_args(parser)
        add_cassandra_args(parser)

def run():
    Processor.launch(default_ident, __doc__)