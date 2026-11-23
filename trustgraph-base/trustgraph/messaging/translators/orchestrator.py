from typing import Dict, Any, Tuple
from ...schema import OrchestratorRequest, OrchestratorResponse, UserContext
from ...base.serialization import dict_to_dataclass, dataclass_to_dict
from .base import MessageTranslator


class OrchestratorRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> OrchestratorRequest:
        uc = data.get("user-context")
        return OrchestratorRequest(
            run_id=data.get("run-id", ""),
            goal=data.get("goal", ""),
            user_context=dict_to_dataclass(uc, UserContext) if uc else None,
        )

    def encode(self, obj: OrchestratorRequest) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "goal": obj.goal,
        }
        if obj.user_context:
            result["user-context"] = dataclass_to_dict(obj.user_context)
        return result


class OrchestratorResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> OrchestratorResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: OrchestratorResponse) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "plan-id": obj.plan_id,
            "artifacts": obj.artifacts,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: OrchestratorResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
