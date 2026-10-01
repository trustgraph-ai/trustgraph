
from dataclasses import dataclass, field

from .core.topic import queue

############################################################################

# Policy events — see docs/tech-specs/policy-audit-events.md for spec.

@dataclass
class PolicyEvent:
    schema_version: int = 1
    event_id: str = ""
    event_type: str = ""
    timestamp: str = ""
    producer: str = ""
    payload_json: str = ""


policy_events_queue = queue('policy-events', cls='notify')

############################################################################
