from typing import Dict, Any, Tuple
from ...schema import ConceptExtractionRequest, ConceptExtractionResponse
from .base import MessageTranslator


class ConceptExtractionRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ConceptExtractionRequest:
        return ConceptExtractionRequest(
            query=data.get("query", ""),
        )

    def encode(self, obj: ConceptExtractionRequest) -> Dict[str, Any]:
        return {
            "query": obj.query,
        }


class ConceptExtractionResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ConceptExtractionResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: ConceptExtractionResponse) -> Dict[str, Any]:
        result = {
            "concepts": list(obj.concepts),
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: ConceptExtractionResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
