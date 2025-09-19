from typing import Dict, Any, List
from ...schema import CollectionManagementRequest, CollectionManagementResponse, CollectionMetadata, Error
from .base import MessageTranslator


class CollectionManagementRequestTranslator(MessageTranslator):
    """Translator for CollectionManagementRequest schema objects"""

    def to_pulsar(self, data: Dict[str, Any]) -> CollectionManagementRequest:
        return CollectionManagementRequest(
            operation=data.get("operation"),
            user=data.get("user"),
            collection=data.get("collection"),
            timestamp=data.get("timestamp"),
            name=data.get("name"),
            description=data.get("description"),
            tags=data.get("tags"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            tag_filter=data.get("tag_filter"),
            limit=data.get("limit")
        )

    def from_pulsar(self, obj: CollectionManagementRequest) -> Dict[str, Any]:
        result = {}

        if obj.operation is not None:
            result["operation"] = obj.operation
        if obj.user is not None:
            result["user"] = obj.user
        if obj.collection is not None:
            result["collection"] = obj.collection
        if obj.timestamp is not None:
            result["timestamp"] = obj.timestamp
        if obj.name is not None:
            result["name"] = obj.name
        if obj.description is not None:
            result["description"] = obj.description
        if obj.tags is not None:
            result["tags"] = list(obj.tags)
        if obj.created_at is not None:
            result["created_at"] = obj.created_at
        if obj.updated_at is not None:
            result["updated_at"] = obj.updated_at
        if obj.tag_filter is not None:
            result["tag_filter"] = list(obj.tag_filter)
        if obj.limit is not None:
            result["limit"] = obj.limit

        return result


class CollectionManagementResponseTranslator(MessageTranslator):
    """Translator for CollectionManagementResponse schema objects"""

    def to_pulsar(self, data: Dict[str, Any]) -> CollectionManagementResponse:
        # Handle error
        error = None
        if "error" in data and data["error"]:
            error_data = data["error"]
            error = Error(
                type=error_data.get("type"),
                message=error_data.get("message")
            )

        # Handle collections array
        collections = []
        if "collections" in data:
            for coll_data in data["collections"]:
                collections.append(CollectionMetadata(
                    user=coll_data.get("user"),
                    collection=coll_data.get("collection"),
                    name=coll_data.get("name"),
                    description=coll_data.get("description"),
                    tags=coll_data.get("tags"),
                    created_at=coll_data.get("created_at"),
                    updated_at=coll_data.get("updated_at")
                ))

        return CollectionManagementResponse(
            success=data.get("success"),
            error=error,
            timestamp=data.get("timestamp"),
            collections=collections
        )

    def from_pulsar(self, obj: CollectionManagementResponse) -> Dict[str, Any]:
        result = {}

        if obj.success is not None:
            result["success"] = obj.success
        if obj.error is not None:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message
            }
        if obj.timestamp is not None:
            result["timestamp"] = obj.timestamp
        if obj.collections is not None:
            result["collections"] = []
            for coll in obj.collections:
                result["collections"].append({
                    "user": coll.user,
                    "collection": coll.collection,
                    "name": coll.name,
                    "description": coll.description,
                    "tags": list(coll.tags) if coll.tags else [],
                    "created_at": coll.created_at,
                    "updated_at": coll.updated_at
                })

        return result