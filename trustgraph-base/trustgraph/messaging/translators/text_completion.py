from typing import Dict, Any, Tuple
from ...schema import TextCompletionRequest, TextCompletionResponse, ModelInfo
from .base import MessageTranslator


class TextCompletionRequestTranslator(MessageTranslator):
    """Translator for TextCompletionRequest schema objects"""

    def decode(self, data: Dict[str, Any]) -> TextCompletionRequest:
        return TextCompletionRequest(
            operation=data.get("operation", "completion"),
            system=data.get("system", ""),
            prompt=data.get("prompt", ""),
            streaming=data.get("streaming", False),
            response_format=data.get("response_format"),
            schema=data.get("schema"),
        )

    def encode(self, obj: TextCompletionRequest) -> Dict[str, Any]:
        result = {
            "operation": obj.operation,
            "system": obj.system,
            "prompt": obj.prompt,
        }
        if obj.response_format is not None:
            result["response_format"] = obj.response_format
        if obj.schema is not None:
            result["schema"] = obj.schema
        return result


def _encode_model_info(m: ModelInfo) -> Dict[str, Any]:
    result: Dict[str, Any] = {"id": m.id}
    if m.name is not None:
        result["name"] = m.name
    if m.owned_by is not None:
        result["owned_by"] = m.owned_by
    if m.created is not None:
        result["created"] = m.created
    if m.description is not None:
        result["description"] = m.description
    if m.context_length is not None:
        result["context_length"] = m.context_length
    if m.max_output_length is not None:
        result["max_output_length"] = m.max_output_length
    if m.input_modalities:
        result["input_modalities"] = m.input_modalities
    if m.output_modalities:
        result["output_modalities"] = m.output_modalities
    if m.supported_features:
        result["supported_features"] = m.supported_features
    if m.input_price is not None:
        result["input_price"] = m.input_price
    if m.output_price is not None:
        result["output_price"] = m.output_price
    if m.family is not None:
        result["family"] = m.family
    if m.parameter_size is not None:
        result["parameter_size"] = m.parameter_size
    if m.quantization is not None:
        result["quantization"] = m.quantization
    if m.format is not None:
        result["format"] = m.format
    return result


class TextCompletionResponseTranslator(MessageTranslator):
    """Translator for TextCompletionResponse schema objects"""

    def decode(self, data: Dict[str, Any]) -> TextCompletionResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")

    def encode(self, obj: TextCompletionResponse) -> Dict[str, Any]:
        result = {"response": obj.response}

        if obj.in_token is not None:
            result["in_token"] = obj.in_token
        if obj.out_token is not None:
            result["out_token"] = obj.out_token
        if obj.model is not None:
            result["model"] = obj.model

        result["end_of_stream"] = getattr(obj, "end_of_stream", False)

        if obj.models:
            result["models"] = [_encode_model_info(m) for m in obj.models]

        return result

    def encode_with_completion(self, obj: TextCompletionResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        is_final = getattr(obj, 'end_of_stream', True)
        return self.encode(obj), is_final