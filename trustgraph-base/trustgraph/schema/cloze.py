
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Cloze model service

@dataclass
class ClozeRequest:
    operation: str = "predict"  # "predict" or "list-models"
    model: str = ""
    query: str = ""

@dataclass
class ClozeModelInfo:
    name: str = ""
    state: str = ""  # "ready" or "training"
    labels: list[str] = field(default_factory=list)
    accuracy: float | None = None
    train_size: int | None = None
    test_size: int | None = None

@dataclass
class ClozeResponse:
    error: Error | None = None
    label: str = ""
    confidence: float = 0.0
    models: list[ClozeModelInfo] = field(default_factory=list)

############################################################################

# Queue definitions

cloze_request_queue = queue('cloze', cls='request')
cloze_response_queue = queue('cloze', cls='response')
