"""
Collection management for the librarian - uses config service for storage
"""

import asyncio
import dataclasses
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

def metadata_to_dict(metadata: CollectionMetadata) -> dict:
    """Convert CollectionMetadata to dictionary for JSON serialization"""
    return {
        'collection': metadata.collection,
        'name': metadata.name,
        'description': metadata.description,
        'tags': list(metadata.tags)
    }

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

    async def ensure_collection_exists(self, workspace: str, collection: str):
        """
        Ensure a collection exists, creating it if necessary

        Args:
            workspace: Workspace ID
            collection: Collection ID
        """
        try:
            # Check if collection exists via config service
            request = ConfigRequest(
                operation='get',
                workspace=workspace,
                keys=[ConfigKey(type='collection', key=collection)]
            )

            response = await self.send_config_request(request)

            # Validate response
            if not response.values or len(response.values) == 0:
                raise Exception(f"Invalid response from config service when checking collection {workspace}/{collection}")

            # Check if collection exists (value not None means it exists)
            if response.values[0].value is not None:
                logger.debug(f"Collection {workspace}/{collection} already exists")
                return

            # Collection doesn't exist (value is None), proceed to create
            # Create new collection with default metadata
            logger.info(f"Auto-creating collection {workspace}/{collection}")

            metadata = CollectionMetadata(
                collection=collection,
                name=collection,  # Default name to collection ID
                description="",
                tags=[]
            )

            request = ConfigRequest(
                operation='put',
                workspace=workspace,
                values=[ConfigValue(
                    type='collection',
                    key=collection,
                    value=json.dumps(metadata_to_dict(metadata))
                )]
            )

            response = await self.send_config_request(request)

            if response.error:
                raise RuntimeError(f"Config update failed: {response.error.message}")

            logger.info(f"Collection {workspace}/{collection} auto-created in config service")

        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise e

    async def list_collections(self, request, workspace):
        try:
            config_request = ConfigRequest(
                operation='getvalues',
                workspace=workspace,
                type='collection'
            )

            response = await self.send_config_request(config_request)

            if response.error:
                raise RuntimeError(f"Config query failed: {response.error.message}")

            # Every value in this workspace is a collection.
            # Filter to fields the current schema knows about — older
            # persisted values may carry fields that have since been
            # dropped (e.g. `user` from the pre-workspace-refactor era).
            known_fields = {f.name for f in dataclasses.fields(CollectionMetadata)}
            collections = []
            for config_value in response.values:
                metadata_dict = json.loads(config_value.value)
                metadata_dict = {
                    k: v for k, v in metadata_dict.items() if k in known_fields
                }
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

    async def update_collection(self, request, workspace):
        try:
            name = request.name if request.name else request.collection
            description = request.description if request.description else ""
            tags = list(request.tags) if request.tags else []

            metadata = CollectionMetadata(
                collection=request.collection,
                name=name,
                description=description,
                tags=tags
            )

            config_request = ConfigRequest(
                operation='put',
                workspace=workspace,
                values=[ConfigValue(
                    type='collection',
                    key=request.collection,
                    value=json.dumps(metadata_to_dict(metadata))
                )]
            )

            response = await self.send_config_request(config_request)

            if response.error:
                raise RuntimeError(f"Config update failed: {response.error.message}")

            logger.info(f"Collection {workspace}/{request.collection} updated in config service")

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

    async def delete_collection(self, request, workspace):
        try:
            logger.info(f"Deleting collection {workspace}/{request.collection}")

            config_request = ConfigRequest(
                operation='delete',
                workspace=workspace,
                keys=[ConfigKey(type='collection', key=request.collection)]
            )

            response = await self.send_config_request(config_request)

            if response.error:
                raise RuntimeError(f"Config delete failed: {response.error.message}")

            logger.info(f"Collection {workspace}/{request.collection} deleted from config service")

            # Config service will trigger config push automatically
            # Storage services will receive update and delete collections

            return CollectionManagementResponse(
                error=None,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise RequestError(f"Failed to delete collection: {str(e)}")
