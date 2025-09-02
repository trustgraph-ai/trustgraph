from typing import Dict, Any, Tuple
from ...schema import (
    DocumentEmbeddingsRequest, DocumentEmbeddingsResponse,
    GraphEmbeddingsRequest, GraphEmbeddingsResponse
)
from .base import MessageTranslator
from .primitives import ValueTranslator


class DocumentEmbeddingsRequestTranslator(MessageTranslator):
    """Translator for DocumentEmbeddingsRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> DocumentEmbeddingsRequest:
        return DocumentEmbeddingsRequest(
            vectors=data["vectors"],
            limit=int(data.get("limit", 10)),
            user=data.get("user", "trustgraph"),
            collection=data.get("collection", "default")
        )
    
    def from_pulsar(self, obj: DocumentEmbeddingsRequest) -> Dict[str, Any]:
        return {
            "vectors": obj.vectors,
            "limit": obj.limit,
            "user": obj.user,
            "collection": obj.collection
        }


class DocumentEmbeddingsResponseTranslator(MessageTranslator):
    """Translator for DocumentEmbeddingsResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> DocumentEmbeddingsResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: DocumentEmbeddingsResponse) -> Dict[str, Any]:
        result = {}
        
        if obj.chunks:
            result["chunks"] = [
                chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                for chunk in obj.chunks
            ]
        
        return result
    
    def from_response_with_completion(self, obj: DocumentEmbeddingsResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True


class GraphEmbeddingsRequestTranslator(MessageTranslator):
    """Translator for GraphEmbeddingsRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> GraphEmbeddingsRequest:
        return GraphEmbeddingsRequest(
            vectors=data["vectors"],
            limit=int(data.get("limit", 10)),
            user=data.get("user", "trustgraph"),
            collection=data.get("collection", "default")
        )
    
    def from_pulsar(self, obj: GraphEmbeddingsRequest) -> Dict[str, Any]:
        return {
            "vectors": obj.vectors,
            "limit": obj.limit,
            "user": obj.user,
            "collection": obj.collection
        }


class GraphEmbeddingsResponseTranslator(MessageTranslator):
    """Translator for GraphEmbeddingsResponse schema objects"""
    
    def __init__(self):
        self.value_translator = ValueTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> GraphEmbeddingsResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: GraphEmbeddingsResponse) -> Dict[str, Any]:
        result = {}
        
        if obj.entities:
            result["entities"] = [
                self.value_translator.from_pulsar(entity)
                for entity in obj.entities
            ]
        
        return result
    
    def from_response_with_completion(self, obj: GraphEmbeddingsResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True