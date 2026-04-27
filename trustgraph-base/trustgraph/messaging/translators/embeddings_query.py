from typing import Dict, Any, Tuple
from ...schema import (
    DocumentEmbeddingsRequest, DocumentEmbeddingsResponse,
    GraphEmbeddingsRequest, GraphEmbeddingsResponse,
    RowEmbeddingsRequest, RowEmbeddingsResponse, RowIndexMatch
)
from .base import MessageTranslator
from .primitives import ValueTranslator


class DocumentEmbeddingsRequestTranslator(MessageTranslator):
    """Translator for DocumentEmbeddingsRequest schema objects"""

    def decode(self, data: Dict[str, Any]) -> DocumentEmbeddingsRequest:
        return DocumentEmbeddingsRequest(
            vector=data["vector"],
            limit=int(data.get("limit", 10)),
            collection=data.get("collection", "default")
        )

    def encode(self, obj: DocumentEmbeddingsRequest) -> Dict[str, Any]:
        return {
            "vector": obj.vector,
            "limit": obj.limit,
            "collection": obj.collection
        }


class DocumentEmbeddingsResponseTranslator(MessageTranslator):
    """Translator for DocumentEmbeddingsResponse schema objects"""

    def decode(self, data: Dict[str, Any]) -> DocumentEmbeddingsResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")

    def encode(self, obj: DocumentEmbeddingsResponse) -> Dict[str, Any]:
        result = {}

        if obj.chunks is not None:
            result["chunks"] = [
                {
                    "chunk_id": chunk.chunk_id,
                    "score": chunk.score
                }
                for chunk in obj.chunks
            ]

        return result

    def encode_with_completion(self, obj: DocumentEmbeddingsResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.encode(obj), True


class GraphEmbeddingsRequestTranslator(MessageTranslator):
    """Translator for GraphEmbeddingsRequest schema objects"""

    def decode(self, data: Dict[str, Any]) -> GraphEmbeddingsRequest:
        return GraphEmbeddingsRequest(
            vector=data["vector"],
            limit=int(data.get("limit", 10)),
            collection=data.get("collection", "default")
        )

    def encode(self, obj: GraphEmbeddingsRequest) -> Dict[str, Any]:
        return {
            "vector": obj.vector,
            "limit": obj.limit,
            "collection": obj.collection
        }


class GraphEmbeddingsResponseTranslator(MessageTranslator):
    """Translator for GraphEmbeddingsResponse schema objects"""

    def __init__(self):
        self.value_translator = ValueTranslator()

    def decode(self, data: Dict[str, Any]) -> GraphEmbeddingsResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")

    def encode(self, obj: GraphEmbeddingsResponse) -> Dict[str, Any]:
        result = {}

        if obj.entities is not None:
            result["entities"] = [
                {
                    "entity": self.value_translator.encode(match.entity),
                    "score": match.score
                }
                for match in obj.entities
            ]

        return result

    def encode_with_completion(self, obj: GraphEmbeddingsResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.encode(obj), True


class RowEmbeddingsRequestTranslator(MessageTranslator):
    """Translator for RowEmbeddingsRequest schema objects"""

    def decode(self, data: Dict[str, Any]) -> RowEmbeddingsRequest:
        return RowEmbeddingsRequest(
            vector=data["vector"],
            limit=int(data.get("limit", 10)),
            collection=data.get("collection", "default"),
            schema_name=data.get("schema_name", ""),
            index_name=data.get("index_name")
        )

    def encode(self, obj: RowEmbeddingsRequest) -> Dict[str, Any]:
        result = {
            "vector": obj.vector,
            "limit": obj.limit,
            "collection": obj.collection,
            "schema_name": obj.schema_name,
        }
        if obj.index_name:
            result["index_name"] = obj.index_name
        return result


class RowEmbeddingsResponseTranslator(MessageTranslator):
    """Translator for RowEmbeddingsResponse schema objects"""

    def decode(self, data: Dict[str, Any]) -> RowEmbeddingsResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")

    def encode(self, obj: RowEmbeddingsResponse) -> Dict[str, Any]:
        result = {}

        if obj.error is not None:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message
            }

        if obj.matches is not None:
            result["matches"] = [
                {
                    "index_name": match.index_name,
                    "index_value": match.index_value,
                    "text": match.text,
                    "score": match.score
                }
                for match in obj.matches
            ]

        return result

    def encode_with_completion(self, obj: RowEmbeddingsResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.encode(obj), True
