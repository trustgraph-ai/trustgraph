from typing import Dict, Any, Tuple, Optional
from ...schema import RowsQueryRequest, RowsQueryResponse
from .base import MessageTranslator
import json


class RowsQueryRequestTranslator(MessageTranslator):
    """Translator for RowsQueryRequest schema objects"""

    def decode(self, data: Dict[str, Any]) -> RowsQueryRequest:
        return RowsQueryRequest(
            collection=data.get("collection", "default"),
            query=data.get("query", ""),
            variables=data.get("variables", {}),
            operation_name=data.get("operation_name", None)
        )

    def encode(self, obj: RowsQueryRequest) -> Dict[str, Any]:
        result = {
            "collection": obj.collection,
            "query": obj.query,
            "variables": dict(obj.variables) if obj.variables else {}
        }

        if obj.operation_name:
            result["operation_name"] = obj.operation_name

        return result


class RowsQueryResponseTranslator(MessageTranslator):
    """Translator for RowsQueryResponse schema objects"""

    def decode(self, data: Dict[str, Any]) -> RowsQueryResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")

    def encode(self, obj: RowsQueryResponse) -> Dict[str, Any]:
        result = {}

        # Handle GraphQL response data
        if obj.data:
            try:
                result["data"] = json.loads(obj.data)
            except json.JSONDecodeError:
                result["data"] = obj.data
        else:
            result["data"] = None

        # Handle GraphQL errors
        if obj.errors:
            result["errors"] = []
            for error in obj.errors:
                error_dict = {
                    "message": error.message
                }
                if error.path:
                    error_dict["path"] = list(error.path)
                if error.extensions:
                    error_dict["extensions"] = dict(error.extensions)
                result["errors"].append(error_dict)

        # Handle extensions
        if obj.extensions:
            result["extensions"] = dict(obj.extensions)

        # Handle system-level error
        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message
            }

        return result

    def encode_with_completion(self, obj: RowsQueryResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.encode(obj), True
