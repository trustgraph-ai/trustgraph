from typing import Dict, Any, Tuple
from ...schema import AgentRequest, AgentResponse
from .base import MessageTranslator


class AgentRequestTranslator(MessageTranslator):
    """Translator for AgentRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> AgentRequest:
        return AgentRequest(
            question=data["question"],
            state=data.get("state", ""),
            group=data.get("group", []),
            history=data.get("history", []),
            user=data.get("user", "trustgraph")
        )
    
    def from_pulsar(self, obj: AgentRequest) -> Dict[str, Any]:
        return {
            "question": obj.question,
            "state": obj.state,
            "group": obj.group,
            "history": obj.history,
            "user": obj.user
        }


class AgentResponseTranslator(MessageTranslator):
    """Translator for AgentResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> AgentResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: AgentResponse) -> Dict[str, Any]:
        result = {}
        if obj.answer:
            result["answer"] = obj.answer
        if obj.thought:
            result["thought"] = obj.thought  
        if obj.observation:
            result["observation"] = obj.observation
        return result
    
    def from_response_with_completion(self, obj: AgentResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), (obj.answer is not None)