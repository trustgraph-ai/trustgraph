from dataclasses import dataclass, field

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Prompt services, abstract the prompt generation

# extract-definitions:
#   chunk -> definitions
# extract-relationships:
#   chunk -> relationships
# kg-prompt:
#   query, triples -> answer
# document-prompt:
#   query, documents -> answer
# extract-rows
#   schema, chunk -> rows

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

############################################################################