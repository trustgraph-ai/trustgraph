
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue
from .user_context import UserContext

############################################################################

# Query formulation request/response

@dataclass
class QueryFormulationRequest:
    run_id: str = ""
    step_id: str = ""
    mode: str = "formulate"
    question: str = ""
    schema_name: str = ""
    query_spec: str = ""
    user_context: UserContext | None = None

@dataclass
class QueryFormulationResponse:
    error: Error | None = None
    run_id: str = ""
    step_id: str = ""
    query_spec: str = ""  # JSON-encoded QuerySpecArtifact

query_formulation_request_queue = queue('query-formulation', cls='request')
query_formulation_response_queue = queue('query-formulation', cls='response')

############################################################################
