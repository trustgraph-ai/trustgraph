
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Field extraction service

@dataclass
class FieldExtractionRequest:
    state: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)

@dataclass
class FieldExtractionResponse:
    error: Error | None = None
    answers: dict = field(default_factory=dict)
    model: str = ""

############################################################################

# Queue definitions

field_extraction_request_queue = queue('field-extraction', cls='request')
field_extraction_response_queue = queue('field-extraction', cls='response')
