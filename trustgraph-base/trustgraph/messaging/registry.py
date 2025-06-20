from typing import Dict, List, Union
from .translators.base import MessageTranslator


class TranslatorRegistry:
    """Registry for service translators"""
    
    _request_translators: Dict[str, MessageTranslator] = {}
    _response_translators: Dict[str, MessageTranslator] = {}
    
    @classmethod
    def register_request(cls, service_name: str, translator: MessageTranslator):
        """Register a request translator for a service"""
        cls._request_translators[service_name] = translator
    
    @classmethod
    def register_response(cls, service_name: str, translator: MessageTranslator):
        """Register a response translator for a service"""
        cls._response_translators[service_name] = translator
    
    @classmethod
    def register_service(cls, service_name: str, request_translator: MessageTranslator, 
                        response_translator: MessageTranslator):
        """Register both request and response translators for a service"""
        cls.register_request(service_name, request_translator)
        cls.register_response(service_name, response_translator)
    
    @classmethod
    def get_request_translator(cls, service_name: str) -> MessageTranslator:
        """Get request translator for a service"""
        if service_name not in cls._request_translators:
            raise KeyError(f"No request translator registered for service: {service_name}")
        return cls._request_translators[service_name]
    
    @classmethod
    def get_response_translator(cls, service_name: str) -> MessageTranslator:
        """Get response translator for a service"""
        if service_name not in cls._response_translators:
            raise KeyError(f"No response translator registered for service: {service_name}")
        return cls._response_translators[service_name]
    
    @classmethod
    def list_services(cls) -> List[str]:
        """List all registered services"""
        return sorted(set(cls._request_translators.keys()) | set(cls._response_translators.keys()))
    
    @classmethod
    def has_service(cls, service_name: str) -> bool:
        """Check if a service is registered"""
        return (service_name in cls._request_translators or 
                service_name in cls._response_translators)