
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Action request/response

@dataclass
class ActionRequest:
    run_id: str = ""
    step_id: str = ""
    capability: str = ""
    params: dict[str, str] = field(default_factory=dict)
    input_artifacts: list[dict] = field(default_factory=list)

@dataclass
class ActionResponse:
    error: Error | None = None
    run_id: str = ""
    step_id: str = ""
    artifact_type: str = ""
    artifact: dict = field(default_factory=dict)

action_request_queue = queue('action', cls='request')
action_response_queue = queue('action', cls='response')

############################################################################
