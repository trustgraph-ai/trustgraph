from typing import Dict, Any, Tuple, Optional
from ...schema import ObjectsQueryRequest, ObjectsQueryResponse
from .base import MessageTranslator
import json


class ObjectsQueryRequestTranslator(MessageTranslator):
    """Translator for ObjectsQueryRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> ObjectsQueryRequest:
        return ObjectsQueryRequest(
            user=data.get("user", "trustgraph"),
            collection=data.get("collection", "default"),
            query=data.get("query", ""),
            variables=data.get("variables", {}),
            operation_name=data.get("operation_name", None)
        )
    
    def from_pulsar(self, obj: ObjectsQueryRequest) -> Dict[str, Any]:
        result = {
            "user": obj.user,
            "collection": obj.collection,
            "query": obj.query,
            "variables": dict(obj.variables) if obj.variables else {}
        }
        
        if obj.operation_name:
            result["operation_name"] = obj.operation_name
            
        return result


class ObjectsQueryResponseTranslator(MessageTranslator):
    """Translator for ObjectsQueryResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> ObjectsQueryResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: ObjectsQueryResponse) -> Dict[str, Any]:
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
    
    def from_response_with_completion(self, obj: ObjectsQueryResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True