from typing import Dict, Any, Tuple
import json
from ...schema import StructuredDataDiagnosisRequest, StructuredDataDiagnosisResponse
from .base import MessageTranslator


class StructuredDataDiagnosisRequestTranslator(MessageTranslator):
    """Translator for StructuredDataDiagnosisRequest schema objects"""

    def to_pulsar(self, data: Dict[str, Any]) -> StructuredDataDiagnosisRequest:
        return StructuredDataDiagnosisRequest(
            operation=data["operation"],
            sample=data["sample"],
            type=data.get("type", ""),
            schema_name=data.get("schema-name", ""),
            options=data.get("options", {})
        )

    def from_pulsar(self, obj: StructuredDataDiagnosisRequest) -> Dict[str, Any]:
        result = {
            "operation": obj.operation,
            "sample": obj.sample,
        }

        # Add optional fields if they exist
        if obj.type:
            result["type"] = obj.type
        if obj.schema_name:
            result["schema-name"] = obj.schema_name
        if obj.options:
            result["options"] = obj.options

        return result


class StructuredDataDiagnosisResponseTranslator(MessageTranslator):
    """Translator for StructuredDataDiagnosisResponse schema objects"""

    def to_pulsar(self, data: Dict[str, Any]) -> StructuredDataDiagnosisResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")

    def from_pulsar(self, obj: StructuredDataDiagnosisResponse) -> Dict[str, Any]:
        result = {
            "operation": obj.operation
        }

        # Add optional response fields if they exist
        if obj.detected_type:
            result["detected-type"] = obj.detected_type
        if obj.confidence is not None:
            result["confidence"] = obj.confidence
        if obj.descriptor:
            # Parse JSON-encoded descriptor
            try:
                result["descriptor"] = json.loads(obj.descriptor)
            except (json.JSONDecodeError, TypeError):
                result["descriptor"] = obj.descriptor
        if obj.metadata:
            result["metadata"] = obj.metadata
        if obj.schema_matches is not None:
            result["schema-matches"] = obj.schema_matches

        return result

    def from_response_with_completion(self, obj: StructuredDataDiagnosisResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True