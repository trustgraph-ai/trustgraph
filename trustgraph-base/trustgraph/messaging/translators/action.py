from typing import Dict, Any, Tuple
from ...schema import ActionRequest, ActionResponse
from .base import MessageTranslator


class ActionRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ActionRequest:
        return ActionRequest(
            run_id=data.get("run-id", ""),
            step_id=data.get("step-id", ""),
            capability=data.get("capability", ""),
            params=data.get("params", {}),
            input_artifacts=data.get("input-artifacts", []),
        )

    def encode(self, obj: ActionRequest) -> Dict[str, Any]:
        return {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "capability": obj.capability,
            "params": obj.params,
            "input-artifacts": obj.input_artifacts,
        }


class ActionResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ActionResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: ActionResponse) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "artifact-type": obj.artifact_type,
            "artifact": obj.artifact,
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
