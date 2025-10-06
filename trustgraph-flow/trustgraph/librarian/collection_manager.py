"""
Collection management for the librarian
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from .. schema import CollectionManagementRequest, CollectionManagementResponse, Error
from .. schema import CollectionMetadata
from .. schema import StorageManagementRequest, StorageManagementResponse
from .. exceptions import RequestError
from .. tables.library import LibraryTableStore

# Module logger
logger = logging.getLogger(__name__)

class CollectionManager:
    """Manages collection metadata and coordinates collection operations across storage types"""

    def __init__(
        self,
        cassandra_host,
        cassandra_username,
        cassandra_password,
        keyspace,
        vector_storage_producer=None,
        object_storage_producer=None,
        triples_storage_producer=None,
        storage_response_consumer=None
    ):
        """
        Initialize the CollectionManager

        Args:
            cassandra_host: Cassandra host(s)
            cassandra_username: Cassandra username
            cassandra_password: Cassandra password
            keyspace: Cassandra keyspace for library data
            vector_storage_producer: Producer for vector storage management
            object_storage_producer: Producer for object storage management
            triples_storage_producer: Producer for triples storage management
            storage_response_consumer: Consumer for storage management responses
        """
        self.table_store = LibraryTableStore(
            cassandra_host, cassandra_username, cassandra_password, keyspace
        )

        # Storage management producers
        self.vector_storage_producer = vector_storage_producer
        self.object_storage_producer = object_storage_producer
        self.triples_storage_producer = triples_storage_producer
        self.storage_response_consumer = storage_response_consumer

        # Track pending deletion operations
        self.pending_deletions = {}

        logger.info("Collection manager initialized")

    async def ensure_collection_exists(self, user: str, collection: str):
        """
        Ensure a collection exists, creating it if necessary with broadcast to storage

        Args:
            user: User ID
            collection: Collection ID
        """
        try:
            # Check if collection already exists
            existing = await self.table_store.get_collection(user, collection)
            if existing:
                logger.debug(f"Collection {user}/{collection} already exists")
                return

            # Create new collection with default metadata
            logger.info(f"Auto-creating collection {user}/{collection} from document submission")
            await self.table_store.create_collection(
                user=user,
                collection=collection,
                name=collection,  # Default name to collection ID
                description="",
                tags=set()
            )

            # Broadcast collection creation to all storage backends
            creation_key = (user, collection)
            logger.info(f"Broadcasting create-collection for {creation_key}")

            self.pending_deletions[creation_key] = {
                "responses_pending": 4,  # doc-embeddings, graph-embeddings, object, triples
                "responses_received": [],
                "all_successful": True,
                "error_messages": [],
                "deletion_complete": asyncio.Event()
            }

            storage_request = StorageManagementRequest(
                operation="create-collection",
                user=user,
                collection=collection
            )

            # Send creation requests to all storage types
            if self.vector_storage_producer:
                await self.vector_storage_producer.send(storage_request)
            if self.object_storage_producer:
                await self.object_storage_producer.send(storage_request)
            if self.triples_storage_producer:
                await self.triples_storage_producer.send(storage_request)

            # Wait for all storage creations to complete (with timeout)
            creation_info = self.pending_deletions[creation_key]
            try:
                await asyncio.wait_for(
                    creation_info["deletion_complete"].wait(),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for storage creation responses for {creation_key}")
                creation_info["all_successful"] = False
                creation_info["error_messages"].append("Timeout waiting for storage creation")

            # Check if all creations succeeded
            if not creation_info["all_successful"]:
                error_msg = f"Storage creation failed: {'; '.join(creation_info['error_messages'])}"
                logger.error(error_msg)

                # Clean up metadata on failure
                await self.table_store.delete_collection(user, collection)

                # Clean up tracking
                del self.pending_deletions[creation_key]

                raise RuntimeError(error_msg)

            # Clean up tracking
            del self.pending_deletions[creation_key]
            logger.info(f"Collection {creation_key} auto-created successfully in all storage backends")

        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise e

    async def list_collections(self, request: CollectionManagementRequest) -> CollectionManagementResponse:
        """
        List collections for a user with optional tag filtering

        Args:
            request: Collection management request

        Returns:
            CollectionManagementResponse with list of collections
        """
        try:
            tag_filter = list(request.tag_filter) if request.tag_filter else None
            collections = await self.table_store.list_collections(request.user, tag_filter)

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
                error=None,
                collections=collection_metadata,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            raise RequestError(f"Failed to list collections: {str(e)}")

    async def update_collection(self, request: CollectionManagementRequest) -> CollectionManagementResponse:
        """
        Update collection metadata (creates if doesn't exist)

        Args:
            request: Collection management request

        Returns:
            CollectionManagementResponse with updated collection
        """
        try:
            # Check if collection exists, create if it doesn't
            existing = await self.table_store.get_collection(request.user, request.collection)
            if not existing:
                # Create new collection with provided metadata
                logger.info(f"Creating new collection {request.user}/{request.collection}")

                name = request.name if request.name else request.collection
                description = request.description if request.description else ""
                tags = set(request.tags) if request.tags else set()

                await self.table_store.create_collection(
                    user=request.user,
                    collection=request.collection,
                    name=name,
                    description=description,
                    tags=tags
                )

                # Broadcast collection creation to all storage backends
                creation_key = (request.user, request.collection)
                logger.info(f"Broadcasting create-collection for {creation_key}")

                self.pending_deletions[creation_key] = {
                    "responses_pending": 4,  # doc-embeddings, graph-embeddings, object, triples
                    "responses_received": [],
                    "all_successful": True,
                    "error_messages": [],
                    "deletion_complete": asyncio.Event()
                }

                storage_request = StorageManagementRequest(
                    operation="create-collection",
                    user=request.user,
                    collection=request.collection
                )

                # Send creation requests to all storage types
                if self.vector_storage_producer:
                    await self.vector_storage_producer.send(storage_request)
                if self.object_storage_producer:
                    await self.object_storage_producer.send(storage_request)
                if self.triples_storage_producer:
                    await self.triples_storage_producer.send(storage_request)

                # Wait for all storage creations to complete (with timeout)
                creation_info = self.pending_deletions[creation_key]
                try:
                    await asyncio.wait_for(
                        creation_info["deletion_complete"].wait(),
                        timeout=30.0  # 30 second timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Timeout waiting for storage creation responses for {creation_key}")
                    creation_info["all_successful"] = False
                    creation_info["error_messages"].append("Timeout waiting for storage creation")

                # Check if all creations succeeded
                if not creation_info["all_successful"]:
                    error_msg = f"Storage creation failed: {'; '.join(creation_info['error_messages'])}"
                    logger.error(error_msg)

                    # Clean up metadata on failure
                    await self.table_store.delete_collection(request.user, request.collection)

                    # Clean up tracking
                    del self.pending_deletions[creation_key]

                    return CollectionManagementResponse(
                        error=Error(
                            type="storage_creation_error",
                            message=error_msg
                        ),
                        timestamp=datetime.now().isoformat()
                    )

                # Clean up tracking
                del self.pending_deletions[creation_key]
                logger.info(f"Collection {creation_key} created successfully in all storage backends")

                # Get the newly created collection for response
                created_collection = await self.table_store.get_collection(request.user, request.collection)

                collection_metadata = CollectionMetadata(
                    user=created_collection["user"],
                    collection=created_collection["collection"],
                    name=created_collection["name"],
                    description=created_collection["description"],
                    tags=created_collection["tags"],
                    created_at=created_collection["created_at"],
                    updated_at=created_collection["updated_at"]
                )
            else:
                # Collection exists, update it
                name = request.name if request.name else None
                description = request.description if request.description else None
                tags = list(request.tags) if request.tags else None

                updated_collection = await self.table_store.update_collection(
                    request.user, request.collection, name, description, tags
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
                error=None,
                collections=[collection_metadata],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error updating collection: {e}")
            raise RequestError(f"Failed to update collection: {str(e)}")

    async def delete_collection(self, request: CollectionManagementRequest) -> CollectionManagementResponse:
        """
        Delete collection with cascade to all storage types

        Args:
            request: Collection management request

        Returns:
            CollectionManagementResponse indicating success or failure
        """
        try:
            deletion_key = (request.user, request.collection)

            logger.info(f"Starting cascade deletion for {request.user}/{request.collection}")

            # Track this deletion request
            self.pending_deletions[deletion_key] = {
                "responses_pending": 4,  # doc-embeddings, graph-embeddings, object, triples
                "responses_received": [],
                "all_successful": True,
                "error_messages": [],
                "deletion_complete": asyncio.Event()
            }

            # Create storage management request
            storage_request = StorageManagementRequest(
                operation="delete-collection",
                user=request.user,
                collection=request.collection
            )

            # Send deletion requests to all storage types
            if self.vector_storage_producer:
                await self.vector_storage_producer.send(storage_request)
            if self.object_storage_producer:
                await self.object_storage_producer.send(storage_request)
            if self.triples_storage_producer:
                await self.triples_storage_producer.send(storage_request)

            # Wait for all storage deletions to complete (with timeout)
            deletion_info = self.pending_deletions[deletion_key]
            try:
                await asyncio.wait_for(
                    deletion_info["deletion_complete"].wait(),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for storage deletion responses for {deletion_key}")
                deletion_info["all_successful"] = False
                deletion_info["error_messages"].append("Timeout waiting for storage deletion")

            # Check if all deletions succeeded
            if not deletion_info["all_successful"]:
                error_msg = f"Storage deletion failed: {'; '.join(deletion_info['error_messages'])}"
                logger.error(error_msg)

                # Clean up tracking
                del self.pending_deletions[deletion_key]

                return CollectionManagementResponse(
                    error=Error(
                        type="storage_deletion_error",
                        message=error_msg
                    ),
                    timestamp=datetime.now().isoformat()
                )

            # All storage deletions succeeded, now delete metadata
            logger.info(f"Storage deletions complete, removing metadata for {deletion_key}")
            await self.table_store.delete_collection(request.user, request.collection)

            # Clean up tracking
            del self.pending_deletions[deletion_key]

            return CollectionManagementResponse(
                error=None,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            # Clean up tracking on error
            if deletion_key in self.pending_deletions:
                del self.pending_deletions[deletion_key]
            raise RequestError(f"Failed to delete collection: {str(e)}")

    async def on_storage_response(self, response: StorageManagementResponse):
        """
        Handle storage management responses for deletion tracking

        Args:
            response: Storage management response
        """
        logger.debug(f"Received storage response: error={response.error}")

        # Find matching deletion by checking all pending deletions
        # Note: This is simplified correlation - in production we'd want better correlation
        for deletion_key, info in list(self.pending_deletions.items()):
            if info["responses_pending"] > 0:
                # Record this response
                info["responses_received"].append(response)
                info["responses_pending"] -= 1

                # Check if this response indicates failure
                if response.error and response.error.message:
                    info["all_successful"] = False
                    info["error_messages"].append(response.error.message)
                    logger.warning(f"Storage operation failed for {deletion_key}: {response.error.message}")
                else:
                    logger.debug(f"Storage operation succeeded for {deletion_key}")

                # If all responses received, signal completion
                if info["responses_pending"] == 0:
                    logger.info(f"All storage responses received for {deletion_key}")
                    info["deletion_complete"].set()

                break  # Only process for first matching deletion