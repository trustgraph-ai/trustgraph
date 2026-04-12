import json
from typing import Dict, Any, Tuple
from ...schema import ToolRequest, ToolResponse
from .base import MessageTranslator

class ToolRequestTranslator(MessageTranslator):
    """Translator for ToolRequest schema objects"""
    
    def decode(self, data: Dict[str, Any]) -> ToolRequest:
        # Handle both "name" and "parameters" input keys
        name = data.get("name", "")
        if "parameters" in data:
            parameters = json.dumps(data["parameters"])
        else:
            parameters = None
        
        return ToolRequest(
            name = name,
            parameters = parameters,
        )
    
    def encode(self, obj: ToolRequest) -> Dict[str, Any]:
        result = {}
        
        if obj.name:
            result["name"] = obj.name
        if obj.parameters is not None:
            result["parameters"] = json.loads(obj.parameters)
        
        return result

class ToolResponseTranslator(MessageTranslator):
    """Translator for ToolResponse schema objects"""
    
    def decode(self, data: Dict[str, Any]) -> ToolResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def encode(self, obj: ToolResponse) -> Dict[str, Any]:

        result = {}
        
        if obj.text:
            result["text"] = obj.text
        if obj.object:
            result["object"] = json.loads(obj.object)
        
        return result
    
    def encode_with_completion(self, obj: ToolResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.encode(obj), True
