from typing import Dict, Any, Tuple
from ...schema import StructuredQueryRequest, StructuredQueryResponse
from .base import MessageTranslator
import json


class StructuredQueryRequestTranslator(MessageTranslator):
    """Translator for StructuredQueryRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> StructuredQueryRequest:
        return StructuredQueryRequest(
            question=data.get("question", "")
        )
    
    def from_pulsar(self, obj: StructuredQueryRequest) -> Dict[str, Any]:
        return {
            "question": obj.question
        }


class StructuredQueryResponseTranslator(MessageTranslator):
    """Translator for StructuredQueryResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> StructuredQueryResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: StructuredQueryResponse) -> Dict[str, Any]:
        result = {}
        
        # Handle structured query response data
        if obj.data:
            try:
                result["data"] = json.loads(obj.data)
            except json.JSONDecodeError:
                result["data"] = obj.data
        else:
            result["data"] = None
        
        # Handle errors (array of strings)
        if obj.errors:
            result["errors"] = list(obj.errors)
        else:
            result["errors"] = []
        
        # Handle system-level error
        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message
            }
        
        return result
    
    def from_response_with_completion(self, obj: StructuredQueryResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True