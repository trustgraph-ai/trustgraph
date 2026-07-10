from typing import Dict, Any, Tuple
from ...schema import TextCompletionRequest, TextCompletionResponse
from .base import MessageTranslator


class TextCompletionRequestTranslator(MessageTranslator):
    """Translator for TextCompletionRequest schema objects"""

    def decode(self, data: Dict[str, Any]) -> TextCompletionRequest:
        return TextCompletionRequest(
            system=data["system"],
            prompt=data["prompt"],
            streaming=data.get("streaming", False),
            response_format=data.get("response_format"),
            schema=data.get("schema"),
        )

    def encode(self, obj: TextCompletionRequest) -> Dict[str, Any]:
        result = {
            "system": obj.system,
            "prompt": obj.prompt,
        }
        if obj.response_format is not None:
            result["response_format"] = obj.response_format
        if obj.schema is not None:
            result["schema"] = obj.schema
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

        # Always include end_of_stream flag for streaming support
        result["end_of_stream"] = getattr(obj, "end_of_stream", False)

        return result
    
    def encode_with_completion(self, obj: TextCompletionResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        # Check end_of_stream field to determine if this is the final message
        is_final = getattr(obj, 'end_of_stream', True)
        return self.encode(obj), is_final