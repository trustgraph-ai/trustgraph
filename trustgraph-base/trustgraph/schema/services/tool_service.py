
from dataclasses import dataclass

from ..core.primitives import Error


@dataclass
class ToolServiceRequest:
    """Request to a dynamically configured tool service."""
    # User context for multi-tenancy
    user: str = ""
    # Config values (collection, etc.) as JSON
    config: str = ""
    # Arguments from LLM as JSON
    arguments: str = ""


@dataclass
class ToolServiceResponse:
    """Response from a tool service."""
    error: Error | None = None
    # Response text (the observation)
    response: str = ""
    # End of stream marker for streaming responses
    end_of_stream: bool = False
