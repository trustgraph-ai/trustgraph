
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue
from .user_context import UserContext

############################################################################

# Execution plan step

@dataclass
class ExecutionPlanStep:
    step_id: str = ""
    capability: str = ""
    depends_on: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)

############################################################################

# Planner request/response

@dataclass
class PlannerRequest:
    run_id: str = ""
    goal: str = ""
    user_context: UserContext | None = None

@dataclass
class PlannerResponse:
    error: Error | None = None
    run_id: str = ""
    plan_id: str = ""
    steps: list[ExecutionPlanStep] = field(default_factory=list)

planner_request_queue = queue('planner', cls='request')
planner_response_queue = queue('planner', cls='response')

############################################################################
