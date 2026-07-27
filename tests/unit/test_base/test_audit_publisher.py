"""
Tests for the AuditPublisher utility.

Verifies envelope construction, fire-and-forget semantics, and
failure suppression.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.base.audit_publisher import AuditPublisher
from trustgraph.schema import AuditEvent, audit_events_queue


class TestAuditPublisherInit:

    def test_queue_is_notify_class(self):
        assert audit_events_queue == "notify:tg:audit-events"

    def test_creates_with_component_name(self):
        pub = AuditPublisher(
            component_name="test-component",
        )
        assert pub.component_name == "test-component"


class TestAuditPublisherEmit:

    @pytest.fixture
    def publisher(self):
        pub = AuditPublisher(
            component_name="test-svc",
        )
        pub._handle = AsyncMock()
        return pub

    @pytest.mark.asyncio
    async def test_emit_sends_structured_envelope(self, publisher):
        await publisher.emit("gateway.request", {"path": "/test"})

        publisher._handle.send.assert_called_once()
        event = publisher._handle.send.call_args[0][0]

        assert isinstance(event, AuditEvent)
        assert event.schema_version == 1
        assert event.event_type == "gateway.request"
        assert event.producer == "test-svc"
        assert event.event_id != ""
        assert event.timestamp != ""

    @pytest.mark.asyncio
    async def test_emit_serializes_payload_as_json(self, publisher):
        payload = {"method": "POST", "status_code": 200}
        await publisher.emit("gateway.request", payload)

        event = publisher._handle.send.call_args[0][0]
        decoded = json.loads(event.payload_json)
        assert decoded == payload

    @pytest.mark.asyncio
    async def test_emit_generates_unique_event_ids(self, publisher):
        await publisher.emit("test.a", {})
        await publisher.emit("test.b", {})

        ids = [
            call[0][0].event_id
            for call in publisher._handle.send.call_args_list
        ]
        assert ids[0] != ids[1]

    @pytest.mark.asyncio
    async def test_emit_swallows_send_failure(self, publisher):
        publisher._handle.send.side_effect = RuntimeError("pub/sub down")
        await publisher.emit("test.event", {"key": "value"})

    @pytest.mark.asyncio
    async def test_emit_timestamp_is_utc_iso(self, publisher):
        await publisher.emit("test.event", {})

        event = publisher._handle.send.call_args[0][0]
        assert "T" in event.timestamp
        assert "+" in event.timestamp or "Z" in event.timestamp
