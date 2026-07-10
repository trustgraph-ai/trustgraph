import base64
from typing import Dict, Any, Tuple
from ...schema import ImageToTextRequest, ImageToTextResponse
from .base import MessageTranslator


class ImageToTextRequestTranslator(MessageTranslator):
    """Translator for ImageToTextRequest schema objects"""

    def decode(self, data: Dict[str, Any]) -> ImageToTextRequest:
        # Base64 content validation only.  The image field carries
        # base64 text end-to-end: raw binary can't ride the JSON wire
        # format, and the payload passes through unchanged
        base64.b64decode(data["image"], validate=True)

        return ImageToTextRequest(
            image=data["image"],
            mime_type=data["mime_type"],
            prompt=data.get("prompt", ""),
            system=data.get("system", ""),
        )

    def encode(self, obj: ImageToTextRequest) -> Dict[str, Any]:
        return {
            "image": obj.image,
            "mime_type": obj.mime_type,
            "prompt": obj.prompt,
            "system": obj.system,
        }


class ImageToTextResponseTranslator(MessageTranslator):
    """Translator for ImageToTextResponse schema objects"""

    def decode(self, data: Dict[str, Any]) -> ImageToTextResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")

    def encode(self, obj: ImageToTextResponse) -> Dict[str, Any]:
        result = {"description": obj.description}

        if obj.in_token is not None:
            result["in_token"] = obj.in_token
        if obj.out_token is not None:
            result["out_token"] = obj.out_token
        if obj.model is not None:
            result["model"] = obj.model

        return result

    def encode_with_completion(self, obj: ImageToTextResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final).  Image-to-text is non-streaming."""
        return self.encode(obj), True
