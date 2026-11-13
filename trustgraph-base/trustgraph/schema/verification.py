
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Verification violation

@dataclass
class Violation:
    field: str = ""
    message: str = ""
    severity: str = ""  # "error" or "warning"

############################################################################

# Verification request/response

@dataclass
class VerificationRequest:
    run_id: str = ""
    step_id: str = ""
    expected_type: str = ""
    artifact: dict = field(default_factory=dict)
    shape: str = ""

@dataclass
class VerificationResponse:
    error: Error | None = None
    run_id: str = ""
    step_id: str = ""
    valid: bool = False
    tier: int = 0
    violations: list[Violation] = field(default_factory=list)

verification_request_queue = queue('verification', cls='request')
verification_response_queue = queue('verification', cls='response')

############################################################################
