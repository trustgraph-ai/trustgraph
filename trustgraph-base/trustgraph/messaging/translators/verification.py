from typing import Dict, Any, Tuple
from ...schema import VerificationRequest, VerificationResponse, Violation
from .base import MessageTranslator


class VerificationRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> VerificationRequest:
        return VerificationRequest(
            run_id=data.get("run-id", ""),
            step_id=data.get("step-id", ""),
            expected_type=data.get("expected-type", ""),
            artifact=data.get("artifact", {}),
            shape=data.get("shape", ""),
        )

    def encode(self, obj: VerificationRequest) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "expected-type": obj.expected_type,
            "artifact": obj.artifact,
        }
        if obj.shape:
            result["shape"] = obj.shape
        return result


class VerificationResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> VerificationResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: VerificationResponse) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "valid": obj.valid,
            "tier": obj.tier,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        result["violations"] = [
            {
                "field": v.field,
                "message": v.message,
                "severity": v.severity,
            }
            for v in obj.violations
        ]

        return result

    def encode_with_completion(
        self, obj: VerificationResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
