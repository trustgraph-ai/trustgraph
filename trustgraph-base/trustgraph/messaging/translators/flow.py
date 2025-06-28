from typing import Dict, Any, Tuple
from ...schema import FlowRequest, FlowResponse
from .base import MessageTranslator


class FlowRequestTranslator(MessageTranslator):
    """Translator for FlowRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> FlowRequest:
        return FlowRequest(
            operation=data.get("operation"),
            class_name=data.get("class-name"),
            class_definition=data.get("class-definition"),
            description=data.get("description"),
            flow_id=data.get("flow-id")
        )
    
    def from_pulsar(self, obj: FlowRequest) -> Dict[str, Any]:
        result = {}
        
        if obj.operation:
            result["operation"] = obj.operation
        if obj.class_name:
            result["class-name"] = obj.class_name
        if obj.class_definition:
            result["class-definition"] = obj.class_definition
        if obj.description:
            result["description"] = obj.description
        if obj.flow_id:
            result["flow-id"] = obj.flow_id
        
        return result


class FlowResponseTranslator(MessageTranslator):
    """Translator for FlowResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> FlowResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: FlowResponse) -> Dict[str, Any]:
        result = {}
        
        if obj.class_names:
            result["class-names"] = obj.class_names
        if obj.flow_ids:
            result["flow-ids"] = obj.flow_ids
        if obj.class_definition:
            result["class-definition"] = obj.class_definition
        if obj.flow:
            result["flow"] = obj.flow
        if obj.description:
            result["description"] = obj.description
        
        return result
    
    def from_response_with_completion(self, obj: FlowResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True