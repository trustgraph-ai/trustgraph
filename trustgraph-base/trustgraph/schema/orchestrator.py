
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue
from .user_context import UserContext

############################################################################

# Orchestrator request/response (external interface)

@dataclass
class OrchestratorRequest:
    run_id: str = ""
    goal: str = ""
    user_context: UserContext | None = None

@dataclass
class OrchestratorResponse:
    error: Error | None = None
    run_id: str = ""
    plan_id: str = ""
    artifacts: dict = field(default_factory=dict)

orchestrator_request_queue = queue('orchestrator', cls='request')
orchestrator_response_queue = queue('orchestrator', cls='response')

############################################################################

# Execution state — self-invocation message.
# Complex fields are JSON strings to avoid nested dataclass
# serialisation issues with Pulsar's Avro schema.

@dataclass
class ExecutionState:
    run_id: str = ""
    plan_id: str = ""
    response_id: str = ""
    steps: str = ""
    step_statuses: str = ""
    step_results: str = ""
    user_context: str = ""

execution_state_queue = queue('orchestrator-state', cls='flow')

############################################################################
