"""
Handler for storage services to process collection configuration from config push
"""

import json
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)

class CollectionConfigHandler:
    """
    Handles collection configuration from config push messages for storage services.

    Storage services should:
    1. Inherit from this class along with their service base class
    2. Call register_config_handler(self.on_collection_config) in __init__
    3. Implement create_collection(user, collection, metadata) method
    4. Implement delete_collection(user, collection) method
    """

    def __init__(self, **kwargs):
        # Track known collections: {(user, collection): metadata_dict}
        self.known_collections: Dict[tuple, dict] = {}
        # Pass remaining kwargs up the inheritance chain
        super().__init__(**kwargs)

    async def on_collection_config(self, config: dict, version: int):
        """
        Handle config push messages and extract collection information

        Args:
            config: Configuration dictionary from ConfigPush message
            version: Configuration version number
        """
        logger.info(f"Processing collection configuration (version {version})")

        # Extract collections from config (treat missing key as empty)
        collection_config = config.get("collection", {})

        # Track which collections we've seen in this config
        current_collections: Set[tuple] = set()

        # Process each collection in the config
        for key, value_json in collection_config.items():
            try:
                # Parse user:collection key
                if ":" not in key:
                    logger.warning(f"Invalid collection key format (expected user:collection): {key}")
                    continue

                user, collection = key.split(":", 1)
                current_collections.add((user, collection))

                # Parse metadata
                metadata = json.loads(value_json)

                # Check if this is a new collection or updated
                collection_key = (user, collection)
                if collection_key not in self.known_collections:
                    logger.info(f"New collection detected: {user}/{collection}")
                    await self.create_collection(user, collection, metadata)
                    self.known_collections[collection_key] = metadata
                else:
                    # Collection already exists, update metadata if changed
                    if self.known_collections[collection_key] != metadata:
                        logger.info(f"Collection metadata updated: {user}/{collection}")
                        # Most storage services don't need to do anything for metadata updates
                        # They just need to know the collection exists
                        self.known_collections[collection_key] = metadata

            except Exception as e:
                logger.error(f"Error processing collection config for key {key}: {e}", exc_info=True)

        # Find collections that were deleted (in known but not in current)
        deleted_collections = set(self.known_collections.keys()) - current_collections
        for user, collection in deleted_collections:
            logger.info(f"Collection deleted: {user}/{collection}")
            try:
                await self.delete_collection(user, collection)
                del self.known_collections[(user, collection)]
            except Exception as e:
                logger.error(f"Error deleting collection {user}/{collection}: {e}", exc_info=True)

        logger.debug(f"Collection config processing complete. Known collections: {len(self.known_collections)}")

    async def create_collection(self, user: str, collection: str, metadata: dict):
        """
        Create a collection in the storage backend.

        Subclasses must implement this method.

        Args:
            user: User ID
            collection: Collection ID
            metadata: Collection metadata dictionary
        """
        raise NotImplementedError("Storage service must implement create_collection method")

    async def delete_collection(self, user: str, collection: str):
        """
        Delete a collection from the storage backend.

        Subclasses must implement this method.

        Args:
            user: User ID
            collection: Collection ID
        """
        raise NotImplementedError("Storage service must implement delete_collection method")

    def collection_exists(self, user: str, collection: str) -> bool:
        """
        Check if a collection is known to exist

        Args:
            user: User ID
            collection: Collection ID

        Returns:
            True if collection exists, False otherwise
        """
        return (user, collection) in self.known_collections
