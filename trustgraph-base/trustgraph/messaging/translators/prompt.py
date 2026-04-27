import json
from typing import Dict, Any, Tuple
from ...schema import PromptRequest, PromptResponse
from .base import MessageTranslator


class PromptRequestTranslator(MessageTranslator):
    """Translator for PromptRequest schema objects"""
    
    def decode(self, data: Dict[str, Any]) -> PromptRequest:
        # Handle both "terms" and "variables" input keys
        terms = data.get("terms", {})
        if "variables" in data:
            # Convert variables to JSON strings as expected by the service
            terms = {
                k: json.dumps(v)
                for k, v in data["variables"].items()
            }

        return PromptRequest(
            id=data.get("id"),
            terms=terms,
            streaming=data.get("streaming", False)
        )
    
    def encode(self, obj: PromptRequest) -> Dict[str, Any]:
        result = {}
        
        if obj.id:
            result["id"] = obj.id
        if obj.terms:
            result["terms"] = obj.terms
        
        return result


class PromptResponseTranslator(MessageTranslator):
    """Translator for PromptResponse schema objects"""
    
    def decode(self, data: Dict[str, Any]) -> PromptResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def encode(self, obj: PromptResponse) -> Dict[str, Any]:
        result = {}

        # Include text field if present (even if empty string)
        if obj.text is not None:
            result["text"] = obj.text
        # Include object field if present
        if obj.object is not None:
            result["object"] = obj.object

        # Always include end_of_stream flag for streaming support
        result["end_of_stream"] = getattr(obj, "end_of_stream", False)

        if obj.in_token is not None:
            result["in_token"] = obj.in_token
        if obj.out_token is not None:
            result["out_token"] = obj.out_token
        if obj.model is not None:
            result["model"] = obj.model

        return result
    
    def encode_with_completion(self, obj: PromptResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        # Check end_of_stream field to determine if this is the final message
        is_final = getattr(obj, 'end_of_stream', True)
        return self.encode(obj), is_final