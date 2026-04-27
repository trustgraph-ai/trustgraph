"""
TrustGraph Collection Management

This module provides interfaces for managing data collections in TrustGraph.
Collections provide logical grouping within a workspace.
"""

import logging

from . types import CollectionMetadata
from . exceptions import *

logger = logging.getLogger(__name__)

class Collection:
    """
    Collection management client.

    Provides methods for managing data collections within the configured
    workspace, including listing, updating metadata, and deleting
    collections.
    """

    def __init__(self, api):
        """
        Initialize Collection client.

        Args:
            api: Parent Api instance for making requests
        """
        self.api = api

    def request(self, request):
        """
        Make a collection-scoped API request.

        Args:
            request: Request payload dictionary

        Returns:
            dict: Response object
        """
        return self.api.request(f"collection-management", request)

    def list_collections(self, tag_filter=None):
        """
        List all collections in this workspace.

        Args:
            tag_filter: Optional list of tags to filter collections

        Returns:
            list[CollectionMetadata]: List of collection metadata objects
        """

        input = {
            "operation": "list-collections",
            "workspace": self.api.workspace,
        }

        if tag_filter:
            input["tag_filter"] = tag_filter

        object = self.request(input)

        try:
            if object is None or "collections" not in object:
                return []

            collections = object.get("collections", [])
            if collections is None:
                return []

            return [
                CollectionMetadata(
                    collection = v["collection"],
                    name = v["name"],
                    description = v["description"],
                    tags = v["tags"]
                )
                for v in collections
            ]
        except Exception as e:
            logger.error("Failed to parse collection list response", exc_info=True)
            raise ProtocolException(f"Response not formatted correctly")

    def update_collection(self, collection, name=None, description=None, tags=None):
        """
        Update collection metadata.

        Args:
            collection: Collection identifier
            name: New collection name (optional)
            description: New collection description (optional)
            tags: New list of tags (optional)

        Returns:
            CollectionMetadata: Updated collection metadata, or None if not found
        """

        input = {
            "operation": "update-collection",
            "workspace": self.api.workspace,
            "collection": collection,
        }

        if name is not None:
            input["name"] = name
        if description is not None:
            input["description"] = description
        if tags is not None:
            input["tags"] = tags

        object = self.request(input)

        try:
            if "collections" in object and object["collections"]:
                v = object["collections"][0]
                return CollectionMetadata(
                    collection = v["collection"],
                    name = v["name"],
                    description = v["description"],
                    tags = v["tags"]
                )
            return None
        except Exception as e:
            logger.error("Failed to parse collection update response", exc_info=True)
            raise ProtocolException(f"Response not formatted correctly")

    def delete_collection(self, collection):
        """
        Delete a collection.

        Args:
            collection: Collection identifier to delete

        Returns:
            dict: Empty response object
        """

        input = {
            "operation": "delete-collection",
            "workspace": self.api.workspace,
            "collection": collection,
        }

        self.request(input)

        return {}
