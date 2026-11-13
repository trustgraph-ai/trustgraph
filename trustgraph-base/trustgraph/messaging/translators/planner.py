from typing import Dict, Any, Tuple
from ...schema import PlannerRequest, PlannerResponse, ExecutionPlanStep
from ...base.serialization import dict_to_dataclass, dataclass_to_dict
from ...schema import UserContext
from .base import MessageTranslator


class PlannerRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> PlannerRequest:
        uc = data.get("user-context")
        return PlannerRequest(
            run_id=data.get("run-id", ""),
            goal=data.get("goal", ""),
            user_context=dict_to_dataclass(uc, UserContext) if uc else None,
        )

    def encode(self, obj: PlannerRequest) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "goal": obj.goal,
        }
        if obj.user_context:
            result["user-context"] = dataclass_to_dict(obj.user_context)
        return result


class PlannerResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> PlannerResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: PlannerResponse) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "plan-id": obj.plan_id,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        result["steps"] = [
            {
                "step-id": s.step_id,
                "capability": s.capability,
                "depends-on": s.depends_on,
                "params": s.params,
                "emits": s.emits,
            }
            for s in obj.steps
        ]

        return result

    def encode_with_completion(
        self, obj: PlannerResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
