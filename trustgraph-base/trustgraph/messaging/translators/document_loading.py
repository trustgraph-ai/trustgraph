import base64
from typing import Dict, Any
from ...schema import Document, TextDocument, Chunk, DocumentEmbeddings, ChunkEmbeddings
from .base import SendTranslator
from .metadata import DocumentMetadataTranslator
from .primitives import SubgraphTranslator


class DocumentTranslator(SendTranslator):
    """Translator for Document schema objects (PDF docs etc.)"""
    
    def __init__(self):
        self.subgraph_translator = SubgraphTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> Document:
        metadata = data.get("metadata", [])
        
        # Handle base64 content validation
        doc = base64.b64decode(data["data"])
        
        from ...schema import Metadata
        return Document(
            metadata=Metadata(
                id=data.get("id"),
                metadata=self.subgraph_translator.to_pulsar(metadata) if metadata else [],
                user=data.get("user", "trustgraph"),
                collection=data.get("collection", "default"),
            ),
            data=base64.b64encode(doc).decode("utf-8")
        )
    
    def from_pulsar(self, obj: Document) -> Dict[str, Any]:
        result = {
            "data": obj.data
        }
        
        if obj.metadata:
            metadata_dict = {}
            if obj.metadata.id:
                metadata_dict["id"] = obj.metadata.id
            if obj.metadata.user:
                metadata_dict["user"] = obj.metadata.user
            if obj.metadata.collection:
                metadata_dict["collection"] = obj.metadata.collection
            if obj.metadata.metadata:
                metadata_dict["metadata"] = self.subgraph_translator.from_pulsar(obj.metadata.metadata)
                
            result["metadata"] = metadata_dict
            
        return result


class TextDocumentTranslator(SendTranslator):
    """Translator for TextDocument schema objects"""
    
    def __init__(self):
        self.subgraph_translator = SubgraphTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> TextDocument:
        metadata = data.get("metadata", [])
        charset = data.get("charset", "utf-8")
        
        # Text is base64 encoded in input
        text = base64.b64decode(data["text"]).decode(charset)
        
        from ...schema import Metadata
        return TextDocument(
            metadata=Metadata(
                id=data.get("id"),
                metadata=self.subgraph_translator.to_pulsar(metadata) if metadata else [],
                user=data.get("user", "trustgraph"),
                collection=data.get("collection", "default"),
            ),
            text=text.encode("utf-8")
        )
    
    def from_pulsar(self, obj: TextDocument) -> Dict[str, Any]:
        result = {
            "text": obj.text.decode("utf-8") if isinstance(obj.text, bytes) else obj.text
        }
        
        if obj.metadata:
            metadata_dict = {}
            if obj.metadata.id:
                metadata_dict["id"] = obj.metadata.id
            if obj.metadata.user:
                metadata_dict["user"] = obj.metadata.user
            if obj.metadata.collection:
                metadata_dict["collection"] = obj.metadata.collection
            if obj.metadata.metadata:
                metadata_dict["metadata"] = self.subgraph_translator.from_pulsar(obj.metadata.metadata)
                
            result["metadata"] = metadata_dict
            
        return result


class ChunkTranslator(SendTranslator):
    """Translator for Chunk schema objects"""
    
    def __init__(self):
        self.subgraph_translator = SubgraphTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> Chunk:
        metadata = data.get("metadata", [])
        
        from ...schema import Metadata
        return Chunk(
            metadata=Metadata(
                id=data.get("id"),
                metadata=self.subgraph_translator.to_pulsar(metadata) if metadata else [],
                user=data.get("user", "trustgraph"),
                collection=data.get("collection", "default"),
            ),
            chunk=data["chunk"].encode("utf-8") if isinstance(data["chunk"], str) else data["chunk"]
        )
    
    def from_pulsar(self, obj: Chunk) -> Dict[str, Any]:
        result = {
            "chunk": obj.chunk.decode("utf-8") if isinstance(obj.chunk, bytes) else obj.chunk
        }
        
        if obj.metadata:
            metadata_dict = {}
            if obj.metadata.id:
                metadata_dict["id"] = obj.metadata.id
            if obj.metadata.user:
                metadata_dict["user"] = obj.metadata.user
            if obj.metadata.collection:
                metadata_dict["collection"] = obj.metadata.collection
            if obj.metadata.metadata:
                metadata_dict["metadata"] = self.subgraph_translator.from_pulsar(obj.metadata.metadata)
                
            result["metadata"] = metadata_dict
            
        return result


class DocumentEmbeddingsTranslator(SendTranslator):
    """Translator for DocumentEmbeddings schema objects"""
    
    def __init__(self):
        self.subgraph_translator = SubgraphTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> DocumentEmbeddings:
        metadata = data.get("metadata", {})
        
        chunks = [
            ChunkEmbeddings(
                chunk=chunk["chunk"].encode("utf-8") if isinstance(chunk["chunk"], str) else chunk["chunk"],
                vectors=chunk["vectors"]
            )
            for chunk in data.get("chunks", [])
        ]
        
        from ...schema import Metadata
        return DocumentEmbeddings(
            metadata=Metadata(
                id=metadata.get("id"),
                metadata=self.subgraph_translator.to_pulsar(metadata.get("metadata", [])),
                user=metadata.get("user", "trustgraph"),
                collection=metadata.get("collection", "default"),
            ),
            chunks=chunks
        )
    
    def from_pulsar(self, obj: DocumentEmbeddings) -> Dict[str, Any]:
        result = {
            "chunks": [
                {
                    "chunk": chunk.chunk.decode("utf-8") if isinstance(chunk.chunk, bytes) else chunk.chunk,
                    "vectors": chunk.vectors
                }
                for chunk in obj.chunks
            ]
        }
        
        if obj.metadata:
            metadata_dict = {}
            if obj.metadata.id:
                metadata_dict["id"] = obj.metadata.id
            if obj.metadata.user:
                metadata_dict["user"] = obj.metadata.user
            if obj.metadata.collection:
                metadata_dict["collection"] = obj.metadata.collection
            if obj.metadata.metadata:
                metadata_dict["metadata"] = self.subgraph_translator.from_pulsar(obj.metadata.metadata)
                
            result["metadata"] = metadata_dict
            
        return result