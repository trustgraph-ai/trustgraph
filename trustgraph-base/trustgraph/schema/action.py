
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue
from .user_context import UserContext

############################################################################

# Action request/response

@dataclass
class ActionRequest:
    run_id: str = ""
    step_id: str = ""
    capability: str = ""
    params: str = ""
    user_context: UserContext | None = None

@dataclass
class ActionResponse:
    error: Error | None = None
    run_id: str = ""
    step_id: str = ""
    artifacts: str = ""

action_request_queue = queue('action', cls='request')
action_response_queue = queue('action', cls='response')

############################################################################
