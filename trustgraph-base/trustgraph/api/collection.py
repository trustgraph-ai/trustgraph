import datetime
import logging

from . types import CollectionMetadata
from . exceptions import *

logger = logging.getLogger(__name__)

class Collection:

    def __init__(self, api):
        self.api = api

    def request(self, request):
        return self.api.request(f"collection-management", request)

    def list_collections(self, user, tag_filter=None):

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

        input = {
            "operation": "delete-collection",
            "user": user,
            "collection": collection,
        }

        object = self.request(input)

        return {}