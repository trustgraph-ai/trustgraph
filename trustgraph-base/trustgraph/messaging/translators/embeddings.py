from typing import Dict, Any, Tuple
from ...schema import EmbeddingsRequest, EmbeddingsResponse
from .base import MessageTranslator


class EmbeddingsRequestTranslator(MessageTranslator):
    """Translator for EmbeddingsRequest schema objects"""

    def decode(self, data: Dict[str, Any]) -> EmbeddingsRequest:
        return EmbeddingsRequest(
            texts=data["texts"]
        )

    def encode(self, obj: EmbeddingsRequest) -> Dict[str, Any]:
        return {
            "texts": obj.texts
        }


class EmbeddingsResponseTranslator(MessageTranslator):
    """Translator for EmbeddingsResponse schema objects"""
    
    def decode(self, data: Dict[str, Any]) -> EmbeddingsResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def encode(self, obj: EmbeddingsResponse) -> Dict[str, Any]:
        return {
            "vectors": obj.vectors
        }
    
    def encode_with_completion(self, obj: EmbeddingsResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.encode(obj), True