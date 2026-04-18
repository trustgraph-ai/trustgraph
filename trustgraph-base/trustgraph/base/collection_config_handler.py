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
    3. Implement create_collection(workspace, collection, metadata) method
    4. Implement delete_collection(workspace, collection) method
    """

    def __init__(self, **kwargs):
        # Track known collections: {(workspace, collection): metadata_dict}
        self.known_collections: Dict[tuple, dict] = {}
        # Pass remaining kwargs up the inheritance chain
        super().__init__(**kwargs)

    async def on_collection_config(
        self, workspace: str, config: dict, version: int
    ):
        """
        Handle config push messages and extract collection information
        for a single workspace.

        Args:
            workspace: Workspace the config applies to
            config: Configuration dictionary from ConfigPush message
            version: Configuration version number
        """
        logger.info(
            f"Processing collection configuration "
            f"(version {version}, workspace {workspace})"
        )

        # Extract collections from config (treat missing key as empty).
        # Each config key IS the collection name — config is already
        # partitioned by workspace, so no workspace prefix is needed
        # on the key.
        collection_config = config.get("collection", {})

        # Track which collections we've seen in this config
        current_collections: Set[tuple] = set()

        for collection, value_json in collection_config.items():
            try:
                current_collections.add((workspace, collection))

                metadata = json.loads(value_json)

                key = (workspace, collection)
                if key not in self.known_collections:
                    logger.info(
                        f"New collection detected: {workspace}/{collection}"
                    )
                    await self.create_collection(
                        workspace, collection, metadata
                    )
                    self.known_collections[key] = metadata
                else:
                    if self.known_collections[key] != metadata:
                        logger.info(
                            f"Collection metadata updated: "
                            f"{workspace}/{collection}"
                        )
                        self.known_collections[key] = metadata

            except Exception as e:
                logger.error(
                    f"Error processing collection config for "
                    f"{workspace}/{collection}: {e}",
                    exc_info=True,
                )

        # Find collections for THIS workspace that were deleted (in
        # known but not in current). Only compare collections owned by
        # this workspace — other workspaces' collections are not
        # affected by this config update.
        known_for_ws = {
            (w, c) for (w, c) in self.known_collections.keys()
            if w == workspace
        }
        deleted_collections = known_for_ws - current_collections
        for ws, collection in deleted_collections:
            logger.info(f"Collection deleted: {ws}/{collection}")
            try:
                # Remove from known_collections FIRST to immediately
                # reject new writes
                del self.known_collections[(ws, collection)]
                await self.delete_collection(ws, collection)
            except Exception as e:
                logger.error(
                    f"Error deleting collection {ws}/{collection}: {e}",
                    exc_info=True,
                )

        logger.debug(
            f"Collection config processing complete. "
            f"Known collections: {len(self.known_collections)}"
        )

    async def create_collection(
        self, workspace: str, collection: str, metadata: dict,
    ):
        """
        Create a collection in the storage backend.

        Subclasses must implement this method.

        Args:
            workspace: Workspace ID
            collection: Collection ID
            metadata: Collection metadata dictionary
        """
        raise NotImplementedError(
            "Storage service must implement create_collection method"
        )

    async def delete_collection(self, workspace: str, collection: str):
        """
        Delete a collection from the storage backend.

        Subclasses must implement this method.

        Args:
            workspace: Workspace ID
            collection: Collection ID
        """
        raise NotImplementedError(
            "Storage service must implement delete_collection method"
        )

    def collection_exists(self, workspace: str, collection: str) -> bool:
        """
        Check if a collection is known to exist.

        Args:
            workspace: Workspace ID
            collection: Collection ID

        Returns:
            True if collection exists, False otherwise
        """
        return (workspace, collection) in self.known_collections
