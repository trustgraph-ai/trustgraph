from typing import Dict, Any, Tuple
from ...schema import ClozeRequest, ClozeResponse
from .base import MessageTranslator


class ClozeRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ClozeRequest:
        return ClozeRequest(
            model=data.get("model", ""),
            query=data.get("query", ""),
        )

    def encode(self, obj: ClozeRequest) -> Dict[str, Any]:
        return {
            "model": obj.model,
            "query": obj.query,
        }


class ClozeResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ClozeResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: ClozeResponse) -> Dict[str, Any]:
        result = {
            "label": obj.label,
            "confidence": obj.confidence,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: ClozeResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
