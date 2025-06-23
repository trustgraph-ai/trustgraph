from typing import Dict, Any, Optional
from ...schema import DocumentMetadata, ProcessingMetadata
from .base import Translator
from .primitives import SubgraphTranslator


class DocumentMetadataTranslator(Translator):
    """Translator for DocumentMetadata schema objects"""
    
    def __init__(self):
        self.subgraph_translator = SubgraphTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> DocumentMetadata:
        metadata = data.get("metadata", [])
        return DocumentMetadata(
            id=data.get("id"),
            time=data.get("time"),
            kind=data.get("kind"),
            title=data.get("title"),
            comments=data.get("comments"),
            metadata=self.subgraph_translator.to_pulsar(metadata) if metadata is not None else [],
            user=data.get("user"),
            tags=data.get("tags")
        )
    
    def from_pulsar(self, obj: DocumentMetadata) -> Dict[str, Any]:
        result = {}
        
        if obj.id:
            result["id"] = obj.id
        if obj.time:
            result["time"] = obj.time
        if obj.kind:
            result["kind"] = obj.kind
        if obj.title:
            result["title"] = obj.title
        if obj.comments:
            result["comments"] = obj.comments
        if obj.metadata is not None:
            result["metadata"] = self.subgraph_translator.from_pulsar(obj.metadata)
        if obj.user:
            result["user"] = obj.user
        if obj.tags is not None:
            result["tags"] = obj.tags
            
        return result


class ProcessingMetadataTranslator(Translator):
    """Translator for ProcessingMetadata schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> ProcessingMetadata:
        return ProcessingMetadata(
            id=data.get("id"),
            document_id=data.get("document-id"),
            time=data.get("time"),
            flow=data.get("flow"),
            user=data.get("user"),
            collection=data.get("collection"),
            tags=data.get("tags")
        )
    
    def from_pulsar(self, obj: ProcessingMetadata) -> Dict[str, Any]:
        result = {}
        
        if obj.id:
            result["id"] = obj.id
        if obj.document_id:
            result["document-id"] = obj.document_id
        if obj.time:
            result["time"] = obj.time
        if obj.flow:
            result["flow"] = obj.flow
        if obj.user:
            result["user"] = obj.user
        if obj.collection:
            result["collection"] = obj.collection
        if obj.tags is not None:
            result["tags"] = obj.tags
            
        return result
