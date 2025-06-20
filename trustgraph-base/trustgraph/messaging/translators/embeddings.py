from typing import Dict, Any, Tuple
from ...schema import EmbeddingsRequest, EmbeddingsResponse
from .base import MessageTranslator


class EmbeddingsRequestTranslator(MessageTranslator):
    """Translator for EmbeddingsRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> EmbeddingsRequest:
        return EmbeddingsRequest(
            text=data["text"]
        )
    
    def from_pulsar(self, obj: EmbeddingsRequest) -> Dict[str, Any]:
        return {
            "text": obj.text
        }


class EmbeddingsResponseTranslator(MessageTranslator):
    """Translator for EmbeddingsResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> EmbeddingsResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: EmbeddingsResponse) -> Dict[str, Any]:
        return {
            "vectors": obj.vectors
        }
    
    def from_response_with_completion(self, obj: EmbeddingsResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True