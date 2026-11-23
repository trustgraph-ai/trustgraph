
from dataclasses import dataclass

from .core.primitives import Error


@dataclass
class RemoteActionRequest:
    run_id: str = ""
    step_id: str = ""
    capability: str = ""
    params: str = ""
    input_artifacts: str = ""
    user_context: str = ""


@dataclass
class RemoteActionResponse:
    run_id: str = ""
    step_id: str = ""
    artifact_type: str = ""
    artifact: str = ""
    error: Error | None = None
