from typing import Dict, Any, Tuple
from ...schema import DocumentRagQuery, DocumentRagResponse, GraphRagQuery, GraphRagResponse
from .base import MessageTranslator


class DocumentRagRequestTranslator(MessageTranslator):
    """Translator for DocumentRagQuery schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
        return DocumentRagQuery(
            query=data["query"],
            user=data.get("user", "trustgraph"),
            collection=data.get("collection", "default"),
            doc_limit=int(data.get("doc-limit", 20))
        )
    
    def from_pulsar(self, obj: DocumentRagQuery) -> Dict[str, Any]:
        return {
            "query": obj.query,
            "user": obj.user,
            "collection": obj.collection,
            "doc-limit": obj.doc_limit
        }


class DocumentRagResponseTranslator(MessageTranslator):
    """Translator for DocumentRagResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: DocumentRagResponse) -> Dict[str, Any]:
        return {
            "response": obj.response
        }
    
    def from_response_with_completion(self, obj: DocumentRagResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True


class GraphRagRequestTranslator(MessageTranslator):
    """Translator for GraphRagQuery schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> GraphRagQuery:
        return GraphRagQuery(
            query=data["query"],
            user=data.get("user", "trustgraph"),
            collection=data.get("collection", "default"),
            entity_limit=int(data.get("entity-limit", 50)),
            triple_limit=int(data.get("triple-limit", 30)),
            max_subgraph_size=int(data.get("max-subgraph-size", 1000)),
            max_path_length=int(data.get("max-path-length", 2))
        )
    
    def from_pulsar(self, obj: GraphRagQuery) -> Dict[str, Any]:
        return {
            "query": obj.query,
            "user": obj.user,
            "collection": obj.collection,
            "entity-limit": obj.entity_limit,
            "triple-limit": obj.triple_limit,
            "max-subgraph-size": obj.max_subgraph_size,
            "max-path-length": obj.max_path_length
        }


class GraphRagResponseTranslator(MessageTranslator):
    """Translator for GraphRagResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> GraphRagResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: GraphRagResponse) -> Dict[str, Any]:
        return {
            "response": obj.response
        }
    
    def from_response_with_completion(self, obj: GraphRagResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True