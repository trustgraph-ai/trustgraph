from typing import Dict, Any, Tuple
from ...schema import FlowRequest, FlowResponse
from .base import MessageTranslator


class FlowRequestTranslator(MessageTranslator):
    """Translator for FlowRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> FlowRequest:
        return FlowRequest(
            operation=data.get("operation"),
            blueprint_name=data.get("blueprint-name"),
            blueprint_definition=data.get("blueprint-definition"),
            description=data.get("description"),
            flow_id=data.get("flow-id"),
            parameters=data.get("parameters")
        )
    
    def from_pulsar(self, obj: FlowRequest) -> Dict[str, Any]:
        result = {}

        if obj.operation is not None:
            result["operation"] = obj.operation
        if obj.blueprint_name is not None:
            result["blueprint-name"] = obj.blueprint_name
        if obj.blueprint_definition is not None:
            result["blueprint-definition"] = obj.blueprint_definition
        if obj.description is not None:
            result["description"] = obj.description
        if obj.flow_id is not None:
            result["flow-id"] = obj.flow_id
        if obj.parameters is not None:
            result["parameters"] = obj.parameters

        return result


class FlowResponseTranslator(MessageTranslator):
    """Translator for FlowResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> FlowResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: FlowResponse) -> Dict[str, Any]:
        result = {}

        if obj.blueprint_names is not None:
            result["blueprint-names"] = obj.blueprint_names
        if obj.flow_ids is not None:
            result["flow-ids"] = obj.flow_ids
        if obj.blueprint_definition is not None:
            result["blueprint-definition"] = obj.blueprint_definition
        if obj.flow is not None:
            result["flow"] = obj.flow
        if obj.description is not None:
            result["description"] = obj.description
        if obj.parameters is not None:
            result["parameters"] = obj.parameters

        return result
    
    def from_response_with_completion(self, obj: FlowResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True
