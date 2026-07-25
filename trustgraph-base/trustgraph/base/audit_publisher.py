
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from . producer import Producer
from . metrics import ProducerMetrics
from trustgraph.schema import AuditEvent, audit_events_queue

logger = logging.getLogger(__name__)


class AuditPublisher:

    def __init__(self, component_name, processor_id=None, backend=None):
        self.component_name = component_name
        self._handle = None

        if backend is not None:
            self._legacy_producer = Producer(
                backend=backend,
                topic=audit_events_queue,
                schema=AuditEvent,
                metrics=ProducerMetrics(
                    processor=processor_id or component_name,
                    producer="audit-events",
                ),
            )
        else:
            self._legacy_producer = None

    async def start(self, sender_pool=None):
        if sender_pool is not None:
            self._handle = await sender_pool.add_producer(
                topic=audit_events_queue,
                schema=AuditEvent,
            )

    async def stop(self):
        if self._handle:
            await self._handle.unregister()

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
            if self._handle:
                await self._handle.send(event)
            elif self._legacy_producer:
                await self._legacy_producer.send(event)
        except Exception as e:
            logger.warning(f"Failed to emit audit event: {e}")
