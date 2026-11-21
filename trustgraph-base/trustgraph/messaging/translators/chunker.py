from typing import Dict, Any, Tuple
from ...schema import ChunkerRequest, ChunkerResponse
from .base import MessageTranslator


class ChunkerRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ChunkerRequest:
        return ChunkerRequest(
            document_id=data.get("document_id", ""),
            chunk_size=data.get("chunk_size", 0),
            chunk_overlap=data.get("chunk_overlap", 0),
        )

    def encode(self, obj: ChunkerRequest) -> Dict[str, Any]:
        return {
            "document_id": obj.document_id,
            "chunk_size": obj.chunk_size,
            "chunk_overlap": obj.chunk_overlap,
        }


class ChunkerResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ChunkerResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: ChunkerResponse) -> Dict[str, Any]:
        result = {
            "document_id": obj.document_id,
            "index": obj.index,
            "char_offset": obj.char_offset,
            "char_length": obj.char_length,
            "end_of_stream": obj.end_of_stream,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: ChunkerResponse
    ) -> Tuple[Dict[str, Any], bool]:
        is_final = getattr(obj, 'end_of_stream', True)
        return self.encode(obj), is_final
