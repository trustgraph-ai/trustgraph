
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Decision scoring service

@dataclass
class DecisionScoringRequest:
    state: dict = field(default_factory=dict)
    questions: dict = field(default_factory=dict)

@dataclass
class DecisionScoringResponse:
    error: Error | None = None
    answers: dict = field(default_factory=dict)
    model: str = ""

############################################################################

# Queue definitions

decision_scoring_request_queue = queue('decision-scoring', cls='request')
decision_scoring_response_queue = queue('decision-scoring', cls='response')
