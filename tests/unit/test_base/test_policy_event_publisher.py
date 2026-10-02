"""
Tests for the PolicyEventPublisher.

Verifies envelope construction, single event type, node IRI batching,
request_id correlation, user context serialisation, and failure
suppression.
"""

import json
import pytest
from unittest.mock import AsyncMock

from trustgraph.base.policy_event_publisher import (
    PolicyEventPublisher, NODE_IRI_CAP,
)
from trustgraph.schema import PolicyEvent, policy_events_queue
from trustgraph.schema.user_context import (
    UserContext, Assignment, Entitlement, OverrideAuthority, Delegation,
)


TG_POL = "https://trustgraph.ai/ontology/policy/"


class TestPolicyEventPublisherInit:

    def test_queue_is_notify_class(self):
        assert policy_events_queue == "notify:tg:policy-events"

    def test_creates_with_component_name(self):
        pub = PolicyEventPublisher(
            component_name="test-component",
        )
        assert pub.component_name == "test-component"


class TestPolicyEventPublisherEmit:

    @pytest.fixture
    def publisher(self):
        pub = PolicyEventPublisher(
            component_name="test-svc",
        )
        pub._handle = AsyncMock()
        return pub

    @pytest.mark.asyncio
    async def test_emit_sends_structured_envelope(self, publisher):
        await publisher.emit("policy.evaluation", {"test": True})

        publisher._handle.send.assert_called_once()
        event = publisher._handle.send.call_args[0][0]

        assert isinstance(event, PolicyEvent)
        assert event.schema_version == 1
        assert event.event_type == "policy.evaluation"
        assert event.producer == "test-svc"
        assert event.event_id != ""
        assert event.timestamp != ""

    @pytest.mark.asyncio
    async def test_emit_serializes_payload_as_json(self, publisher):
        payload = {"policy_uri": "http://example.org/p1"}
        await publisher.emit("policy.evaluation", payload)

        event = publisher._handle.send.call_args[0][0]
        decoded = json.loads(event.payload_json)
        assert decoded == payload

    @pytest.mark.asyncio
    async def test_emit_swallows_send_failure(self, publisher):
        publisher._handle.send.side_effect = RuntimeError("down")
        await publisher.emit("policy.evaluation", {"key": "value"})


class FakeEvaluation:
    def __init__(self, node_iri, policy_uri, policy_label,
                 determination, blocks=True, reason=""):
        self.node_iri = node_iri
        self.policy_uri = policy_uri
        self.policy_label = policy_label
        self.determination = determination
        self.blocks = blocks
        self.reason = reason


class TestEmitEvaluations:

    @pytest.fixture
    def publisher(self):
        pub = PolicyEventPublisher(
            component_name="policy-svc",
        )
        pub._handle = AsyncMock()
        return pub

    @pytest.fixture
    def user_context(self):
        return UserContext(
            user_id="user:alice",
            roles=["analyst"],
            organisational_units=["ou:finance"],
        )

    @pytest.mark.asyncio
    async def test_groups_by_policy_and_determination(
        self, publisher, user_context,
    ):
        evals = [
            FakeEvaluation(
                "n:1", "pol:A", "Policy A",
                f"{TG_POL}Filtered", True, "Not assigned.",
            ),
            FakeEvaluation(
                "n:2", "pol:A", "Policy A",
                f"{TG_POL}Filtered", True, "Not assigned.",
            ),
            FakeEvaluation(
                "n:3", "pol:B", "Policy B",
                f"{TG_POL}Violation", True, "Security barrier.",
            ),
        ]

        await publisher.emit_evaluations(
            evaluations=evals,
            user_context=user_context,
            collection="default",
        )

        assert publisher._handle.send.call_count == 2

        events = [
            json.loads(call[0][0].payload_json)
            for call in publisher._handle.send.call_args_list
        ]

        filtered_events = [
            e for e in events
            if e["determination"] == f"{TG_POL}Filtered"
        ]
        violation_events = [
            e for e in events
            if e["determination"] == f"{TG_POL}Violation"
        ]

        assert len(filtered_events) == 1
        assert filtered_events[0]["node_count"] == 2
        assert set(filtered_events[0]["node_iris"]) == {"n:1", "n:2"}
        assert filtered_events[0]["blocks"] is True

        assert len(violation_events) == 1
        assert violation_events[0]["node_count"] == 1

    @pytest.mark.asyncio
    async def test_all_events_use_policy_evaluation_type(
        self, publisher, user_context,
    ):
        evals = [
            FakeEvaluation(
                "n:1", "pol:A", "A",
                f"{TG_POL}SensitiveAccess", False, "Logged.",
            ),
            FakeEvaluation(
                "n:2", "pol:B", "B",
                f"{TG_POL}Filtered", True, "Not assigned.",
            ),
            FakeEvaluation(
                "n:3", "pol:C", "C",
                f"{TG_POL}Violation", True, "Security barrier.",
            ),
        ]

        await publisher.emit_evaluations(
            evaluations=evals,
            user_context=user_context,
        )

        event_types = [
            call[0][0].event_type
            for call in publisher._handle.send.call_args_list
        ]

        assert all(t == "policy.evaluation" for t in event_types)

    @pytest.mark.asyncio
    async def test_node_iris_capped(self, publisher, user_context):
        evals = [
            FakeEvaluation(
                f"n:{i}", "pol:A", "A",
                f"{TG_POL}Filtered", True, "Not assigned.",
            )
            for i in range(150)
        ]

        await publisher.emit_evaluations(
            evaluations=evals,
            user_context=user_context,
        )

        event = json.loads(
            publisher._handle.send.call_args[0][0].payload_json
        )
        assert len(event["node_iris"]) == NODE_IRI_CAP
        assert event["node_count"] == 150

    @pytest.mark.asyncio
    async def test_includes_request_id(self, publisher, user_context):
        evals = [
            FakeEvaluation(
                "n:1", "pol:A", "A",
                f"{TG_POL}Filtered", True, "Not assigned.",
            ),
        ]

        await publisher.emit_evaluations(
            evaluations=evals,
            user_context=user_context,
            request_id="req-abc-123",
        )

        event = json.loads(
            publisher._handle.send.call_args[0][0].payload_json
        )
        assert event["request_id"] == "req-abc-123"

    @pytest.mark.asyncio
    async def test_includes_blocks_and_reason(
        self, publisher, user_context,
    ):
        evals = [
            FakeEvaluation(
                "n:1", "pol:A", "A",
                f"{TG_POL}SensitiveAccess", False, "Access logged.",
            ),
        ]

        await publisher.emit_evaluations(
            evaluations=evals,
            user_context=user_context,
        )

        event = json.loads(
            publisher._handle.send.call_args[0][0].payload_json
        )
        assert event["blocks"] is False
        assert event["reason"] == "Access logged."

    @pytest.mark.asyncio
    async def test_includes_query_context(self, publisher, user_context):
        evals = [
            FakeEvaluation(
                "n:1", "pol:A", "A",
                f"{TG_POL}Filtered", True, "Not assigned.",
            ),
        ]

        await publisher.emit_evaluations(
            evaluations=evals,
            user_context=user_context,
            query_s="http://example.org/s",
            query_p="http://example.org/p",
            query_o=None,
            collection="my-col",
            graph="urn:graph:test",
            workspace="ws-1",
        )

        event = json.loads(
            publisher._handle.send.call_args[0][0].payload_json
        )
        assert event["query_s"] == "http://example.org/s"
        assert event["query_p"] == "http://example.org/p"
        assert event["query_o"] is None
        assert event["collection"] == "my-col"
        assert event["graph"] == "urn:graph:test"
        assert event["workspace"] == "ws-1"

    @pytest.mark.asyncio
    async def test_serialises_user_context(self, publisher):
        ctx = UserContext(
            user_id="user:bob",
            roles=["admin", "analyst"],
            organisational_units=["ou:hq"],
            assignments=[
                Assignment(
                    resource="res:proj1",
                    scope="read",
                ),
            ],
            entitlements=[
                Entitlement(
                    resource_scope="PublicCatalog",
                    access_level="read",
                ),
            ],
            override_authorities=[
                OverrideAuthority(
                    policy_area="ExportControl",
                ),
            ],
            delegation=Delegation(
                delegator_id="user:alice",
                scope="full",
            ),
        )

        evals = [
            FakeEvaluation(
                "n:1", "pol:A", "A",
                f"{TG_POL}SensitiveAccess", False, "Logged.",
            ),
        ]

        await publisher.emit_evaluations(
            evaluations=evals,
            user_context=ctx,
        )

        event = json.loads(
            publisher._handle.send.call_args[0][0].payload_json
        )
        uc = event["user_context"]
        assert uc["user_id"] == "user:bob"
        assert uc["roles"] == ["admin", "analyst"]
        assert len(uc["assignments"]) == 1
        assert uc["assignments"][0]["resource"] == "res:proj1"
        assert len(uc["entitlements"]) == 1
        assert len(uc["override_authorities"]) == 1
        assert uc["delegation"]["delegator_id"] == "user:alice"
