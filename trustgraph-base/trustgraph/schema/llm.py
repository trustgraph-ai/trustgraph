
from dataclasses import dataclass, field

from .core.primitives import Error

############################################################################

# LLM text completion

@dataclass
class TextCompletionRequest:
    system: str = ""
    prompt: str = ""
    streaming: bool = False
    response_format: str | None = None
    schema: dict | None = None

@dataclass
class TextCompletionResponse:
    error: Error | None = None
    response: str = ""
    in_token: int | None = None
    out_token: int | None = None
    model: str | None = None
    end_of_stream: bool = False  # Indicates final message in stream

############################################################################

# Tool request/response

@dataclass
class ToolRequest:
    name: str = ""
    # Parameters are JSON encoded
    parameters: str = ""

@dataclass
class ToolResponse:
    error: Error | None = None
    # Plain text aka "unstructured"
    text: str = ""
    # JSON-encoded object aka "structured"
    object: str = ""

############################################################################

# Prompt services

@dataclass
class PromptRequest:
    id: str = ""

    # JSON encoded values
    terms: dict[str, str] = field(default_factory=dict)

    # Streaming support (default false for backward compatibility)
    streaming: bool = False

@dataclass
class PromptResponse:
    # Error case
    error: Error | None = None

    # Just plain text
    text: str = ""

    # JSON encoded
    object: str = ""

    # Indicates final message in stream
    end_of_stream: bool = False

    # Token usage from the underlying text completion
    in_token: int | None = None
    out_token: int | None = None
    model: str | None = None

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

############################################################################
