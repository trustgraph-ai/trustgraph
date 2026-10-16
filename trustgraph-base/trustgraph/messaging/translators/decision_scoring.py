from typing import Dict, Any, Tuple
from ...schema import DecisionScoringRequest, DecisionScoringResponse
from .base import MessageTranslator


class DecisionScoringRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> DecisionScoringRequest:
        return DecisionScoringRequest(
            state=data.get("state", {}),
            questions=data.get("questions", {}),
        )

    def encode(self, obj: DecisionScoringRequest) -> Dict[str, Any]:
        return {
            "state": obj.state,
            "questions": obj.questions,
        }


class DecisionScoringResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> DecisionScoringResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: DecisionScoringResponse) -> Dict[str, Any]:
        result = {
            "answers": obj.answers,
            "model": obj.model,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: DecisionScoringResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
