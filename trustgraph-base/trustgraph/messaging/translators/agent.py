from typing import Dict, Any, Tuple
from ...schema import AgentRequest, AgentResponse
from .base import MessageTranslator


class AgentRequestTranslator(MessageTranslator):
    """Translator for AgentRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> AgentRequest:
        return AgentRequest(
            question=data["question"],
            state=data.get("state", None),
            group=data.get("group", None),
            history=data.get("history", []),
            user=data.get("user", "trustgraph"),
            streaming=data.get("streaming", False)
        )

    def from_pulsar(self, obj: AgentRequest) -> Dict[str, Any]:
        return {
            "question": obj.question,
            "state": obj.state,
            "group": obj.group,
            "history": obj.history,
            "user": obj.user,
            "streaming": getattr(obj, "streaming", False)
        }


class AgentResponseTranslator(MessageTranslator):
    """Translator for AgentResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> AgentResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: AgentResponse) -> Dict[str, Any]:
        result = {}

        # Check if this is a streaming response (has chunk_type)
        if hasattr(obj, 'chunk_type') and obj.chunk_type:
            result["chunk_type"] = obj.chunk_type
            if obj.content:
                result["content"] = obj.content
            result["end_of_message"] = getattr(obj, "end_of_message", False)
            result["end_of_dialog"] = getattr(obj, "end_of_dialog", False)
        else:
            # Legacy format (non-streaming)
            if obj.answer:
                result["answer"] = obj.answer
            if obj.thought:
                result["thought"] = obj.thought
            if obj.observation:
                result["observation"] = obj.observation
            # Include completion flags for legacy format too
            result["end_of_message"] = getattr(obj, "end_of_message", False)
            result["end_of_dialog"] = getattr(obj, "end_of_dialog", False)

        # Always include error if present
        if hasattr(obj, 'error') and obj.error and obj.error.message:
            result["error"] = {"message": obj.error.message, "code": obj.error.code}

        return result

    def from_response_with_completion(self, obj: AgentResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        # For streaming responses, check end_of_dialog
        if hasattr(obj, 'chunk_type') and obj.chunk_type:
            is_final = getattr(obj, 'end_of_dialog', False)
        else:
            # For legacy responses, check if answer is present
            is_final = (obj.answer is not None)

        return self.from_pulsar(obj), is_final