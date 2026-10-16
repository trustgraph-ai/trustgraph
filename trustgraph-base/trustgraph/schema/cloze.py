
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Cloze model service

@dataclass
class ClozeRequest:
    model: str = ""
    query: str = ""

@dataclass
class ClozeResponse:
    error: Error | None = None
    label: str = ""
    confidence: float = 0.0

############################################################################

# Queue definitions

cloze_request_queue = queue('cloze', cls='request')
cloze_response_queue = queue('cloze', cls='response')
