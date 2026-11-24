import json
from typing import Dict, Any, Tuple
from ...schema import ActionRequest, ActionResponse, UserContext
from ...base.serialization import dict_to_dataclass, dataclass_to_dict
from .base import MessageTranslator


class ActionRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ActionRequest:
        uc = data.get("user-context")
        return ActionRequest(
            run_id=data.get("run-id", ""),
            step_id=data.get("step-id", ""),
            capability=data.get("capability", ""),
            params=json.dumps(data.get("params", {})),
            user_context=dict_to_dataclass(uc, UserContext) if uc else None,
        )

    def encode(self, obj: ActionRequest) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "capability": obj.capability,
            "params": json.loads(obj.params) if obj.params else {},
        }
        if obj.user_context:
            result["user-context"] = dataclass_to_dict(obj.user_context)
        return result


class ActionResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ActionResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: ActionResponse) -> Dict[str, Any]:
        artifacts = json.loads(obj.artifacts) if obj.artifacts else {}

        result = {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "artifacts": artifacts,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: ActionResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
