from typing import Dict, Any, Tuple
from ...schema import QueryFormulationRequest, QueryFormulationResponse
from ...base.serialization import dict_to_dataclass, dataclass_to_dict
from ...schema import UserContext
from .base import MessageTranslator


class QueryFormulationRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> QueryFormulationRequest:
        uc = data.get("user-context")
        return QueryFormulationRequest(
            run_id=data.get("run-id", ""),
            step_id=data.get("step-id", ""),
            question=data.get("question", ""),
            schema_name=data.get("schema-name", ""),
            user_context=dict_to_dataclass(uc, UserContext) if uc else None,
        )

    def encode(self, obj: QueryFormulationRequest) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "question": obj.question,
            "schema-name": obj.schema_name,
        }
        if obj.user_context:
            result["user-context"] = dataclass_to_dict(obj.user_context)
        return result


class QueryFormulationResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> QueryFormulationResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: QueryFormulationResponse) -> Dict[str, Any]:
        result = {
            "run-id": obj.run_id,
            "step-id": obj.step_id,
            "query-spec": obj.query_spec,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: QueryFormulationResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
