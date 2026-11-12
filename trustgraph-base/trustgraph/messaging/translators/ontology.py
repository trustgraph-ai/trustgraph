from typing import Dict, Any, Tuple
from ...schema import OntologyRequest, OntologyResponse, OntologyInfo
from .base import MessageTranslator


class OntologyRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> OntologyRequest:
        return OntologyRequest(
            operation=data.get("operation", ""),
            text=data.get("text", ""),
            top_k=int(data.get("top-k", 10)),
            similarity_threshold=float(
                data.get("similarity-threshold", 0.3)
            ),
        )

    def encode(self, obj: OntologyRequest) -> Dict[str, Any]:
        return {
            "operation": obj.operation,
            "text": obj.text,
            "top-k": obj.top_k,
            "similarity-threshold": obj.similarity_threshold,
        }


class OntologyResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> OntologyResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: OntologyResponse) -> Dict[str, Any]:
        result = {
            "operation": obj.operation,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        if obj.operation == "subset":
            result["ontology-id"] = obj.ontology_id
            result["classes"] = obj.classes
            result["object-properties"] = obj.object_properties
            result["datatype-properties"] = obj.datatype_properties
            result["namespace"] = obj.namespace

        elif obj.operation == "list":
            result["ontologies"] = [
                {
                    "ontology-id": o.ontology_id,
                    "state": o.state,
                    "classes-total": o.classes_total,
                    "properties-total": o.properties_total,
                    "elements-embedded": o.elements_embedded,
                    "error-message": o.error_message,
                }
                for o in obj.ontologies
            ]

        return result

    def encode_with_completion(
        self, obj: OntologyResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
