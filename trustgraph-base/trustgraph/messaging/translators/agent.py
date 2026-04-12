from typing import Dict, Any, Tuple
from ...schema import AgentRequest, AgentResponse
from .base import MessageTranslator
from .primitives import TripleTranslator


class AgentRequestTranslator(MessageTranslator):
    """Translator for AgentRequest schema objects"""
    
    def decode(self, data: Dict[str, Any]) -> AgentRequest:
        return AgentRequest(
            question=data["question"],
            state=data.get("state", None),
            group=data.get("group", None),
            history=data.get("history", []),
            user=data.get("user", "trustgraph"),
            collection=data.get("collection", "default"),
            streaming=data.get("streaming", False),
            session_id=data.get("session_id", ""),
            conversation_id=data.get("conversation_id", ""),
            pattern=data.get("pattern", ""),
            task_type=data.get("task_type", ""),
            framing=data.get("framing", ""),
            correlation_id=data.get("correlation_id", ""),
            parent_session_id=data.get("parent_session_id", ""),
            subagent_goal=data.get("subagent_goal", ""),
            expected_siblings=data.get("expected_siblings", 0),
        )

    def encode(self, obj: AgentRequest) -> Dict[str, Any]:
        return {
            "question": obj.question,
            "state": obj.state,
            "group": obj.group,
            "history": obj.history,
            "user": obj.user,
            "collection": getattr(obj, "collection", "default"),
            "streaming": getattr(obj, "streaming", False),
            "session_id": getattr(obj, "session_id", ""),
            "conversation_id": getattr(obj, "conversation_id", ""),
            "pattern": getattr(obj, "pattern", ""),
            "task_type": getattr(obj, "task_type", ""),
            "framing": getattr(obj, "framing", ""),
            "correlation_id": getattr(obj, "correlation_id", ""),
            "parent_session_id": getattr(obj, "parent_session_id", ""),
            "subagent_goal": getattr(obj, "subagent_goal", ""),
            "expected_siblings": getattr(obj, "expected_siblings", 0),
        }


class AgentResponseTranslator(MessageTranslator):
    """Translator for AgentResponse schema objects"""

    def __init__(self):
        self.triple_translator = TripleTranslator()

    def decode(self, data: Dict[str, Any]) -> AgentResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")

    def encode(self, obj: AgentResponse) -> Dict[str, Any]:
        result = {}

        if obj.chunk_type:
            result["chunk_type"] = obj.chunk_type
        if obj.content:
            result["content"] = obj.content
        result["end_of_message"] = getattr(obj, "end_of_message", False)
        result["end_of_dialog"] = getattr(obj, "end_of_dialog", False)

        if getattr(obj, "message_id", ""):
            result["message_id"] = obj.message_id

        # Include explainability fields if present
        explain_id = getattr(obj, "explain_id", None)
        if explain_id:
            result["explain_id"] = explain_id

        explain_graph = getattr(obj, "explain_graph", None)
        if explain_graph is not None:
            result["explain_graph"] = explain_graph

        # Include explain_triples for explain messages
        explain_triples = getattr(obj, "explain_triples", [])
        if explain_triples:
            result["explain_triples"] = [
                self.triple_translator.encode(t) for t in explain_triples
            ]

        # Always include error if present
        if hasattr(obj, 'error') and obj.error and obj.error.message:
            result["error"] = {"message": obj.error.message, "code": obj.error.code}

        return result

    def encode_with_completion(self, obj: AgentResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        is_final = getattr(obj, 'end_of_dialog', False)
        return self.encode(obj), is_final