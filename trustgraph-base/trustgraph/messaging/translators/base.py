from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from pulsar.schema import Record


class Translator(ABC):
    """Base class for bidirectional Pulsar ↔ dict translation"""
    
    @abstractmethod
    def to_pulsar(self, data: Dict[str, Any]) -> Record:
        """Convert dict to Pulsar schema object"""
        pass
    
    @abstractmethod  
    def from_pulsar(self, obj: Record) -> Dict[str, Any]:
        """Convert Pulsar schema object to dict"""
        pass


class MessageTranslator(Translator):
    """For complete request/response message translation"""
    
    def from_response_with_completion(self, obj: Record) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final) - for streaming responses"""
        return self.from_pulsar(obj), True


def handle_optional_fields(obj: Record, fields: list) -> Dict[str, Any]:
    """Helper to extract optional fields from Pulsar object"""
    result = {}
    for field in fields:
        value = getattr(obj, field, None)
        if value is not None:
            result[field] = value
    return result