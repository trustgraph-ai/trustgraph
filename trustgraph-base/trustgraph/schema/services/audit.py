
from dataclasses import dataclass, field

from ..core.topic import queue

############################################################################

# Audit events — see docs/tech-specs/audit-events.md for the full spec.
#
# Transport: notify-class pub/sub (fire-and-forget, per-subscriber
# delivery).  Producers are the API gateway and the IAM service.
# Consumers are optional enterprise components.


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
