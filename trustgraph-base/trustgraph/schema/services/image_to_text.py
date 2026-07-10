
from dataclasses import dataclass

from ..core.primitives import Error

############################################################################

# Image to text

@dataclass
class ImageToTextRequest:
    # Image payload: base64-encoded image data
    image: str = ""
    mime_type: str = ""
    prompt: str = ""
    system: str = ""

@dataclass
class ImageToTextResponse:
    error: Error | None = None
    description: str = ""
    in_token: int | None = None
    out_token: int | None = None
    model: str | None = None
