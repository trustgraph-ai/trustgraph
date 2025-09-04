from typing import Dict, Any, Tuple
from ...schema import QuestionToStructuredQueryRequest, QuestionToStructuredQueryResponse
from .base import MessageTranslator


class QuestionToStructuredQueryRequestTranslator(MessageTranslator):
    """Translator for QuestionToStructuredQueryRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> QuestionToStructuredQueryRequest:
        return QuestionToStructuredQueryRequest(
            question=data.get("question", ""),
            max_results=data.get("max_results", 100)
        )
    
    def from_pulsar(self, obj: QuestionToStructuredQueryRequest) -> Dict[str, Any]:
        return {
            "question": obj.question,
            "max_results": obj.max_results
        }


class QuestionToStructuredQueryResponseTranslator(MessageTranslator):
    """Translator for QuestionToStructuredQueryResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> QuestionToStructuredQueryResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: QuestionToStructuredQueryResponse) -> Dict[str, Any]:
        result = {
            "graphql_query": obj.graphql_query,
            "variables": dict(obj.variables) if obj.variables else {},
            "detected_schemas": list(obj.detected_schemas) if obj.detected_schemas else [],
            "confidence": obj.confidence
        }
        
        # Handle system-level error
        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message
            }
        
        return result
    
    def from_response_with_completion(self, obj: QuestionToStructuredQueryResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True