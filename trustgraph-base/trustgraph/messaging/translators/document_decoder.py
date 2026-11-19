from typing import Dict, Any, Tuple
from ...schema import DocumentDecoderRequest, DocumentDecoderResponse
from .base import MessageTranslator


class DocumentDecoderRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> DocumentDecoderRequest:
        return DocumentDecoderRequest(
            document_id=data.get("document_id", ""),
            mode=data.get("mode", "page"),
        )

    def encode(self, obj: DocumentDecoderRequest) -> Dict[str, Any]:
        return {
            "document_id": obj.document_id,
            "mode": obj.mode,
        }


class DocumentDecoderResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> DocumentDecoderResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: DocumentDecoderResponse) -> Dict[str, Any]:
        result = {
            "document_id": obj.document_id,
            "page": obj.page,
            "section_type": obj.section_type,
            "end_of_stream": obj.end_of_stream,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: DocumentDecoderResponse
    ) -> Tuple[Dict[str, Any], bool]:
        is_final = getattr(obj, 'end_of_stream', True)
        return self.encode(obj), is_final
