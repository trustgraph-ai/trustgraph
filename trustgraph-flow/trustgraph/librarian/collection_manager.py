"""
Collection management for the librarian - uses config service for storage
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from .. schema import CollectionManagementRequest, CollectionManagementResponse, Error
from .. schema import CollectionMetadata
from .. schema import ConfigRequest, ConfigResponse, ConfigKey, ConfigValue
from .. exceptions import RequestError

# Module logger
logger = logging.getLogger(__name__)

class CollectionManager:
    """Manages collection metadata via config service"""

    def __init__(
        self,
        config_request_producer,
        config_response_consumer,
        taskgroup
    ):
        """
        Initialize the CollectionManager

        Args:
            config_request_producer: Producer for config service requests
            config_response_consumer: Consumer for config service responses
            taskgroup: Task group for async operations
        """
        self.config_request_producer = config_request_producer
        self.config_response_consumer = config_response_consumer
        self.taskgroup = taskgroup

        # Track pending config requests
        self.pending_config_requests = {}

        logger.info("Collection manager initialized with config service backend")

    async def send_config_request(self, request: ConfigRequest) -> ConfigResponse:
        """
        Send config request and wait for response

        Args:
            request: Config service request (without id field)

        Returns:
            ConfigResponse from config service
        """
        # Generate request ID - passed via message properties, not in schema
        request_id = str(uuid.uuid4())

        event = asyncio.Event()
        self.pending_config_requests[request_id] = event

        # Send request with ID in message properties
        await self.config_request_producer.send(request, properties={"id": request_id})
        await event.wait()

        response = self.pending_config_requests.pop(request_id + "_response")
        return response

    async def on_config_response(self, message, consumer, flow):
        """
        Handle config response

        Args:
            message: Pulsar message
            consumer: Consumer instance
            flow: Flow context
        """
        # Get ID from message properties
        response_id = message.properties().get("id")
        if response_id and response_id in self.pending_config_requests:
            response = message.value()
            self.pending_config_requests[response_id + "_response"] = response
            self.pending_config_requests[response_id].set()

    async def ensure_collection_exists(self, user: str, collection: str):
        """
        Ensure a collection exists, creating it if necessary

        Args:
            user: User ID
            collection: Collection ID
        """
        try:
            # Check if collection exists via config service
            request = ConfigRequest(
                operation='get',
                keys=[ConfigKey(type='collection', key=f'{user}:{collection}')]
            )

            response = await self.send_config_request(request)

            # If collection exists, we're done
            if response.values and len(response.values) > 0:
                logger.debug(f"Collection {user}/{collection} already exists")
                return

            # Create new collection with default metadata
            logger.info(f"Auto-creating collection {user}/{collection}")

            metadata = CollectionMetadata(
                user=user,
                collection=collection,
                name=collection,  # Default name to collection ID
                description="",
                tags=[]
            )

            request = ConfigRequest(
                operation='put',
                values=[ConfigValue(
                    type='collection',
                    key=f'{user}:{collection}',
                    value=json.dumps(metadata.to_dict())
                )]
            )

            response = await self.send_config_request(request)

            if response.error:
                raise RuntimeError(f"Config update failed: {response.error.message}")

            logger.info(f"Collection {user}/{collection} auto-created in config service")

        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise e

    async def list_collections(self, request: CollectionManagementRequest) -> CollectionManagementResponse:
        """
        List collections for a user from config service

        Args:
            request: Collection management request

        Returns:
            CollectionManagementResponse with list of collections
        """
        try:
            # Get all collections from config service
            config_request = ConfigRequest(
                operation='getvalues',
                type='collection'
            )

            response = await self.send_config_request(config_request)

            if response.error:
                raise RuntimeError(f"Config query failed: {response.error.message}")

            # Parse collections and filter by user
            collections = []
            for config_value in response.values:
                if ":" in config_value.key:
                    coll_user, coll_name = config_value.key.split(":", 1)
                    if coll_user == request.user:
                        metadata_dict = json.loads(config_value.value)
                        metadata = CollectionMetadata(**metadata_dict)
                        collections.append(metadata)

            # Apply tag filtering if specified
            if request.tag_filter:
                tag_filter_set = set(request.tag_filter)
                collections = [
                    c for c in collections
                    if any(tag in tag_filter_set for tag in c.tags)
                ]

            # Apply limit if specified
            if request.limit and request.limit > 0:
                collections = collections[:request.limit]

            return CollectionManagementResponse(
                error=None,
                collections=collections,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            raise RequestError(f"Failed to list collections: {str(e)}")

    async def update_collection(self, request: CollectionManagementRequest) -> CollectionManagementResponse:
        """
        Update collection metadata via config service (creates if doesn't exist)

        Args:
            request: Collection management request

        Returns:
            CollectionManagementResponse with updated collection
        """
        try:
            # Create metadata from request
            name = request.name if request.name else request.collection
            description = request.description if request.description else ""
            tags = list(request.tags) if request.tags else []

            metadata = CollectionMetadata(
                user=request.user,
                collection=request.collection,
                name=name,
                description=description,
                tags=tags
            )

            # Send put request to config service
            config_request = ConfigRequest(
                operation='put',
                values=[ConfigValue(
                    type='collection',
                    key=f'{request.user}:{request.collection}',
                    value=json.dumps(metadata.to_dict())
                )]
            )

            response = await self.send_config_request(config_request)

            if response.error:
                raise RuntimeError(f"Config update failed: {response.error.message}")

            logger.info(f"Collection {request.user}/{request.collection} updated in config service")

            # Config service will trigger config push automatically
            # Storage services will receive update and create/update collections

            return CollectionManagementResponse(
                error=None,
                collections=[metadata],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error updating collection: {e}")
            raise RequestError(f"Failed to update collection: {str(e)}")

    async def delete_collection(self, request: CollectionManagementRequest) -> CollectionManagementResponse:
        """
        Delete collection via config service

        Args:
            request: Collection management request

        Returns:
            CollectionManagementResponse indicating success or failure
        """
        try:
            logger.info(f"Deleting collection {request.user}/{request.collection}")

            # Send delete request to config service
            config_request = ConfigRequest(
                operation='delete',
                keys=[ConfigKey(type='collection', key=f'{request.user}:{request.collection}')]
            )

            response = await self.send_config_request(config_request)

            if response.error:
                raise RuntimeError(f"Config delete failed: {response.error.message}")

            logger.info(f"Collection {request.user}/{request.collection} deleted from config service")

            # Config service will trigger config push automatically
            # Storage services will receive update and delete collections

            return CollectionManagementResponse(
                error=None,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise RequestError(f"Failed to delete collection: {str(e)}")
