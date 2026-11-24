
from dataclasses import dataclass

from .core.primitives import Error


@dataclass
class RemoteActionRequest:
    run_id: str = ""
    step_id: str = ""
    capability: str = ""
    params: str = ""
    user_context: str = ""


@dataclass
class RemoteActionResponse:
    run_id: str = ""
    step_id: str = ""
    artifacts: str = ""
    error: Error | None = None
