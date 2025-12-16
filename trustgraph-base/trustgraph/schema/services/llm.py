
from dataclasses import dataclass, field

from ..core.topic import topic
from ..core.primitives import Error

############################################################################

# LLM text completion

@dataclass
class TextCompletionRequest:
    system: str = ""
    prompt: str = ""
    streaming: bool = False  # Default false for backward compatibility

@dataclass
class TextCompletionResponse:
    error: Error | None = None
    response: str = ""
    in_token: int = 0
    out_token: int = 0
    model: str = ""
    end_of_stream: bool = False  # Indicates final message in stream

############################################################################

# Embeddings

@dataclass
class EmbeddingsRequest:
    text: str = ""

@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[float]] = field(default_factory=list)

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

