from typing import Dict, Any, Tuple, Optional
from ...schema import LibrarianRequest, LibrarianResponse, DocumentMetadata, ProcessingMetadata, Criteria
from .base import MessageTranslator
from .metadata import DocumentMetadataTranslator, ProcessingMetadataTranslator


class LibraryRequestTranslator(MessageTranslator):
    """Translator for LibrarianRequest schema objects"""
    
    def __init__(self):
        self.doc_metadata_translator = DocumentMetadataTranslator()
        self.proc_metadata_translator = ProcessingMetadataTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> LibrarianRequest:
        # Document metadata
        doc_metadata = None
        if "document-metadata" in data:
            doc_metadata = self.doc_metadata_translator.to_pulsar(data["document-metadata"])
        
        # Processing metadata
        proc_metadata = None
        if "processing-metadata" in data:
            proc_metadata = self.proc_metadata_translator.to_pulsar(data["processing-metadata"])
        
        # Criteria
        criteria = []
        if "criteria" in data:
            criteria = [
                Criteria(
                    key=c["key"],
                    value=c["value"],
                    operator=c["operator"]
                )
                for c in data["criteria"]
            ]
        
        # Content as bytes
        content = None
        if "content" in data:
            if isinstance(data["content"], str):
                content = data["content"].encode("utf-8")
            else:
                content = data["content"]
        
        return LibrarianRequest(
            operation=data.get("operation"),
            document_id=data.get("document-id"),
            processing_id=data.get("processing-id"),
            document_metadata=doc_metadata,
            processing_metadata=proc_metadata,
            content=content,
            user=data.get("user"),
            collection=data.get("collection"),
            criteria=criteria
        )
    
    def from_pulsar(self, obj: LibrarianRequest) -> Dict[str, Any]:
        result = {}
        
        if obj.operation:
            result["operation"] = obj.operation
        if obj.document_id:
            result["document-id"] = obj.document_id
        if obj.processing_id:
            result["processing-id"] = obj.processing_id
        if obj.document_metadata:
            result["document-metadata"] = self.doc_metadata_translator.from_pulsar(obj.document_metadata)
        if obj.processing_metadata:
            result["processing-metadata"] = self.proc_metadata_translator.from_pulsar(obj.processing_metadata)
        if obj.content:
            result["content"] = obj.content.decode("utf-8") if isinstance(obj.content, bytes) else obj.content
        if obj.user:
            result["user"] = obj.user
        if obj.collection:
            result["collection"] = obj.collection
        if obj.criteria:
            result["criteria"] = [
                {
                    "key": c.key,
                    "value": c.value,
                    "operator": c.operator
                }
                for c in obj.criteria
            ]
        
        return result


class LibraryResponseTranslator(MessageTranslator):
    """Translator for LibrarianResponse schema objects"""
    
    def __init__(self):
        self.doc_metadata_translator = DocumentMetadataTranslator()
        self.proc_metadata_translator = ProcessingMetadataTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> LibrarianResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: LibrarianResponse) -> Dict[str, Any]:
        result = {}
        
        if obj.document_metadata:
            result["document-metadata"] = self.doc_metadata_translator.from_pulsar(obj.document_metadata)
        
        if obj.content:
            result["content"] = obj.content.decode("utf-8") if isinstance(obj.content, bytes) else obj.content
        
        if obj.document_metadatas:
            result["document-metadatas"] = [
                self.doc_metadata_translator.from_pulsar(dm)
                for dm in obj.document_metadatas
            ]
        
        if obj.processing_metadatas:
            result["processing-metadatas"] = [
                self.proc_metadata_translator.from_pulsar(pm)
                for pm in obj.processing_metadatas
            ]
        
        return result
    
    def from_response_with_completion(self, obj: LibrarianResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True