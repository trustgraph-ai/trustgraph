
from dataclasses import dataclass, field

from .core.topic import queue

############################################################################

# Audit events — see docs/tech-specs/audit-events.md for the full spec.

@dataclass
class AuditEvent:
    schema_version: int = 1
    event_id: str = ""
    event_type: str = ""
    timestamp: str = ""
    producer: str = ""
    payload_json: str = ""


audit_events_queue = queue('audit-events', cls='notify')

############################################################################
