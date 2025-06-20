from typing import Dict, Any, Tuple
from ...schema import TextCompletionRequest, TextCompletionResponse
from .base import MessageTranslator


class TextCompletionRequestTranslator(MessageTranslator):
    """Translator for TextCompletionRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> TextCompletionRequest:
        return TextCompletionRequest(
            system=data["system"],
            prompt=data["prompt"]
        )
    
    def from_pulsar(self, obj: TextCompletionRequest) -> Dict[str, Any]:
        return {
            "system": obj.system,
            "prompt": obj.prompt
        }


class TextCompletionResponseTranslator(MessageTranslator):
    """Translator for TextCompletionResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> TextCompletionResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: TextCompletionResponse) -> Dict[str, Any]:
        result = {"response": obj.response}
        
        if obj.in_token:
            result["in_token"] = obj.in_token
        if obj.out_token:
            result["out_token"] = obj.out_token
        if obj.model:
            result["model"] = obj.model
            
        return result
    
    def from_response_with_completion(self, obj: TextCompletionResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True