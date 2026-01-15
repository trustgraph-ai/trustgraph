"""
TrustGraph Collection Management

This module provides interfaces for managing data collections in TrustGraph.
Collections provide logical grouping and isolation for documents and knowledge
graph data.
"""

import datetime
import logging

from . types import CollectionMetadata
from . exceptions import *

logger = logging.getLogger(__name__)

class Collection:
    """
    Collection management client.

    Provides methods for managing data collections, including listing,
    updating metadata, and deleting collections. Collections organize
    documents and knowledge graph data into logical groupings for
    isolation and access control.
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

    def list_collections(self, user, tag_filter=None):
        """
        List all collections for a user.

        Retrieves metadata for all collections owned by the specified user,
        with optional filtering by tags.

        Args:
            user: User identifier
            tag_filter: Optional list of tags to filter collections (default: None)

        Returns:
            list[CollectionMetadata]: List of collection metadata objects

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            collection = api.collection()

            # List all collections
            all_colls = collection.list_collections(user="trustgraph")
            for coll in all_colls:
                print(f"{coll.collection}: {coll.name}")
                print(f"  Description: {coll.description}")
                print(f"  Tags: {', '.join(coll.tags)}")

            # List collections with specific tags
            research_colls = collection.list_collections(
                user="trustgraph",
                tag_filter=["research", "published"]
            )
            ```
        """

        input = {
            "operation": "list-collections",
            "user": user,
        }

        if tag_filter:
            input["tag_filter"] = tag_filter

        object = self.request(input)

        try:
            # Handle case where collections might be None or missing
            if object is None or "collections" not in object:
                return []

            collections = object.get("collections", [])
            if collections is None:
                return []

            return [
                CollectionMetadata(
                    user = v["user"],
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

    def update_collection(self, user, collection, name=None, description=None, tags=None):
        """
        Update collection metadata.

        Updates the name, description, and/or tags for an existing collection.
        Only provided fields are updated; others remain unchanged.

        Args:
            user: User identifier
            collection: Collection identifier
            name: New collection name (optional)
            description: New collection description (optional)
            tags: New list of tags (optional)

        Returns:
            CollectionMetadata: Updated collection metadata, or None if not found

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            collection_api = api.collection()

            # Update collection metadata
            updated = collection_api.update_collection(
                user="trustgraph",
                collection="default",
                name="Default Collection",
                description="Main data collection for general use",
                tags=["default", "production"]
            )

            # Update only specific fields
            updated = collection_api.update_collection(
                user="trustgraph",
                collection="research",
                description="Updated description"
            )
            ```
        """

        input = {
            "operation": "update-collection",
            "user": user,
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
                    user = v["user"],
                    collection = v["collection"],
                    name = v["name"],
                    description = v["description"],
                    tags = v["tags"]
                )
            return None
        except Exception as e:
            logger.error("Failed to parse collection update response", exc_info=True)
            raise ProtocolException(f"Response not formatted correctly")

    def delete_collection(self, user, collection):
        """
        Delete a collection.

        Removes a collection and all its associated data from the system.

        Args:
            user: User identifier
            collection: Collection identifier to delete

        Returns:
            dict: Empty response object

        Example:
            ```python
            collection_api = api.collection()

            # Delete a collection
            collection_api.delete_collection(
                user="trustgraph",
                collection="old-collection"
            )
            ```
        """

        input = {
            "operation": "delete-collection",
            "user": user,
            "collection": collection,
        }

        object = self.request(input)

        return {}