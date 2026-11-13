
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Redaction directive — describes what to redact when verdict is FILTER

@dataclass
class RedactionDirective:
    field: str = ""
    method: str = ""  # strip, mask, generalise, synthetic-replace
    rule_id: str = ""
    message: str = ""

############################################################################

# Policy engine request/response

@dataclass
class PolicyEngineRequest:
    run_id: str = ""
    step_id: str = ""
    evaluation_type: str = ""  # plan-preflight, step-ingress, step-egress, artifact-egress
    subject: dict = field(default_factory=dict)
    principal: dict = field(default_factory=dict)

@dataclass
class PolicyEngineResponse:
    error: Error | None = None
    run_id: str = ""
    step_id: str = ""
    verdict: str = "ALLOW"
    disclosure: str = "SILENT"
    boundary_failure: bool = False
    matched_rules: list[str] = field(default_factory=list)
    redaction_directives: list[RedactionDirective] = field(default_factory=list)
    message: str = ""

policy_engine_request_queue = queue('policy', cls='request')
policy_engine_response_queue = queue('policy', cls='response')

############################################################################
