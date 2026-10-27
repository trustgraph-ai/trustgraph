from typing import Dict, Any, Tuple
from ...schema import FieldExtractionRequest, FieldExtractionResponse
from .base import MessageTranslator


class FieldExtractionRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> FieldExtractionRequest:
        return FieldExtractionRequest(
            state=data.get("state", {}),
            fields=data.get("fields", {}),
        )

    def encode(self, obj: FieldExtractionRequest) -> Dict[str, Any]:
        return {
            "state": obj.state,
            "fields": obj.fields,
        }


class FieldExtractionResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> FieldExtractionResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: FieldExtractionResponse) -> Dict[str, Any]:
        result = {
            "answers": obj.answers,
            "model": obj.model,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: FieldExtractionResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
