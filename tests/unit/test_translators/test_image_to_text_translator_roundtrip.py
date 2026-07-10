"""
Round-trip unit tests for ImageToTextRequestTranslator and
ImageToTextResponseTranslator.

The image field carries base64 text end-to-end (raw binary can't ride
the JSON wire format), so the request decode is THE validation point
for image payloads entering the system: invalid base64 must be
rejected at the gateway, before anything is queued.

Image-to-text is non-streaming, so encode_with_completion must always
report the response as final.
"""

import base64

import pytest

from trustgraph.messaging.translators.image_to_text import (
    ImageToTextRequestTranslator,
    ImageToTextResponseTranslator,
)
from trustgraph.schema import (
    ImageToTextRequest,
    ImageToTextResponse,
)


IMAGE_BYTES = b"\x89PNG\r\n\x1a\nfake-image-payload"
IMAGE_B64 = base64.b64encode(IMAGE_BYTES).decode("utf-8")


@pytest.fixture
def request_translator():
    return ImageToTextRequestTranslator()


@pytest.fixture
def response_translator():
    return ImageToTextResponseTranslator()


class TestImageToTextRequestTranslator:

    def test_decode_full_request(self, request_translator):
        decoded = request_translator.decode({
            "image": IMAGE_B64,
            "mime_type": "image/png",
            "prompt": "What is shown here?",
            "system": "You are an art critic",
        })

        assert isinstance(decoded, ImageToTextRequest)
        assert decoded.image == IMAGE_B64
        assert decoded.mime_type == "image/png"
        assert decoded.prompt == "What is shown here?"
        assert decoded.system == "You are an art critic"

    def test_decode_defaults_optional_fields(self, request_translator):
        """prompt/system are optional; the backend supplies the default prompt."""
        decoded = request_translator.decode({
            "image": IMAGE_B64,
            "mime_type": "image/jpeg",
        })

        assert decoded.prompt == ""
        assert decoded.system == ""

    def test_decode_rejects_invalid_base64(self, request_translator):
        with pytest.raises(ValueError):
            request_translator.decode({
                "image": "this is !!! not *** base64",
                "mime_type": "image/png",
            })

    def test_roundtrip_is_lossless(self, request_translator):
        request = ImageToTextRequest(
            image=IMAGE_B64,
            mime_type="image/png",
            prompt="Describe this image",
            system="Be terse",
        )

        encoded = request_translator.encode(request)
        decoded = request_translator.decode(encoded)

        assert decoded.image == IMAGE_B64
        assert decoded.mime_type == "image/png"
        assert decoded.prompt == "Describe this image"
        assert decoded.system == "Be terse"


class TestImageToTextResponseTranslator:

    def test_encode_full_response(self, response_translator):
        response = ImageToTextResponse(
            error=None,
            description="A cat sitting on a mat",
            in_token=100,
            out_token=20,
            model="test-model",
        )

        encoded = response_translator.encode(response)

        assert encoded == {
            "description": "A cat sitting on a mat",
            "in_token": 100,
            "out_token": 20,
            "model": "test-model",
        }

    def test_encode_omits_absent_token_fields(self, response_translator):
        response = ImageToTextResponse(description="A dog")

        encoded = response_translator.encode(response)

        assert encoded == {"description": "A dog"}

    def test_encode_with_completion_always_final(self, response_translator):
        """Image-to-text is non-streaming: every response is final."""
        response = ImageToTextResponse(description="A dog")

        result, is_final = response_translator.encode_with_completion(response)

        assert result == {"description": "A dog"}
        assert is_final is True

    def test_decode_not_implemented(self, response_translator):
        with pytest.raises(NotImplementedError):
            response_translator.decode({"description": "A dog"})
