
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from . producer import Producer
from . metrics import ProducerMetrics
from trustgraph.schema import AuditEvent, audit_events_queue

logger = logging.getLogger(__name__)


class AuditPublisher:

    def __init__(self, backend, component_name, processor_id=None):
        self.component_name = component_name
        self.producer = Producer(
            backend=backend,
            topic=audit_events_queue,
            schema=AuditEvent,
            metrics=ProducerMetrics(
                processor=processor_id or component_name,
                flow=None,
                name="audit-events",
            ),
        )

    async def emit(self, event_type, payload):
        event = AuditEvent(
            schema_version=1,
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            producer=self.component_name,
            payload_json=json.dumps(payload),
        )

        try:
            await self.producer.send(event)
        except Exception as e:
            logger.warning(f"Failed to emit audit event: {e}")
