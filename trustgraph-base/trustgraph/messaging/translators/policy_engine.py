from typing import Dict, Any, Tuple
from ...schema import (
    PolicyEngineRequest, PolicyEngineResponse, RedactionDirective,
)
from .base import MessageTranslator


class PolicyEngineRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> PolicyEngineRequest:
        return PolicyEngineRequest(
            run_id=data.get("run-id", ""),
            step_id=data.get("step-id", ""),
            evaluation_type=data.get("evaluation-type", ""),
            subject=data.get("subject", {}),
            principal=data.get("principal", {}),
        )

    def encode(self, obj: PolicyEngineRequest) -> Dict[str, Any]:
        return {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "evaluation-type": obj.evaluation_type,
            "subject": obj.subject,
            "principal": obj.principal,
        }


class PolicyEngineResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> PolicyEngineResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: PolicyEngineResponse) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "verdict": obj.verdict,
            "disclosure": obj.disclosure,
            "boundary-failure": obj.boundary_failure,
            "matched-rules": obj.matched_rules,
            "message": obj.message,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        result["redaction-directives"] = [
            {
                "field": d.field,
                "method": d.method,
                "rule-id": d.rule_id,
                "message": d.message,
            }
            for d in obj.redaction_directives
        ]

        return result

    def encode_with_completion(
        self, obj: PolicyEngineResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
