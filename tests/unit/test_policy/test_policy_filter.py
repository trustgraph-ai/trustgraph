"""
Tests for the PolicyFilter determination handling.

Verifies that Notify passes data through (with callback),
while Filtered and Violation block nodes.
"""

import pytest
from unittest.mock import AsyncMock

from trustgraph.policy.policy_filter import (
    PolicyFilter, PolicyEvaluation, LoadedPolicy,
)
from trustgraph.schema import Triple, Term, IRI, LITERAL, UserContext


def make_triple(s_iri, p_iri, o_val):
    return Triple(
        s=Term(type=IRI, iri=s_iri),
        p=Term(type=IRI, iri=p_iri),
        o=Term(type=LITERAL, value=o_val),
    )


def make_iri_triple(s_iri, p_iri, o_iri):
    return Triple(
        s=Term(type=IRI, iri=s_iri),
        p=Term(type=IRI, iri=p_iri),
        o=Term(type=IRI, iri=o_iri),
    )


class TestPolicyEvaluation:

    def test_includes_policy_uri(self):
        ev = PolicyEvaluation(
            node_iri="http://example.org/n1",
            policy_uri="http://example.org/pol1",
            policy_label="Test Policy",
            determination="Filtered",
        )
        assert ev.policy_uri == "http://example.org/pol1"
        assert ev.node_iri == "http://example.org/n1"
        assert ev.policy_label == "Test Policy"
        assert ev.determination == "Filtered"


class TestDeterminationHandling:

    @pytest.fixture
    def user_context(self):
        return UserContext(user_id="user:test", roles=["analyst"])

    @pytest.fixture
    def triples(self):
        return [
            make_triple("http://ex.org/a", "http://ex.org/name", "Alice"),
            make_triple("http://ex.org/b", "http://ex.org/name", "Bob"),
            make_triple("http://ex.org/c", "http://ex.org/name", "Carol"),
        ]

    def _make_filter(self, determination_map, on_evaluation=None):
        """Create a PolicyFilter with pre-loaded policies.

        determination_map: dict of {node_iri: determination_string}
        """

        async def query_fn(s, p, o, collection, g=""):
            return []

        pf = PolicyFilter(
            query_fn=query_fn,
            on_evaluation=on_evaluation,
        )

        policy = LoadedPolicy(
            uri="http://ex.org/test-policy",
            label="Test Policy",
            determination="Filtered",
            order=0,
            sparql_select="SELECT ?this WHERE { ?this ?p ?o }",
            prefixes={},
        )
        pf._policies = [policy]
        pf._required_predicates = set()

        original_evaluate = pf._evaluate_node

        async def mock_evaluate(node_iri, collection, context_graph):
            if node_iri in determination_map:
                return PolicyEvaluation(
                    node_iri=node_iri,
                    policy_uri="http://ex.org/test-policy",
                    policy_label="Test Policy",
                    determination=determination_map[node_iri],
                )
            return None

        pf._evaluate_node = mock_evaluate
        return pf

    @pytest.mark.asyncio
    async def test_notify_passes_through(self, triples, user_context):
        pf = self._make_filter({
            "http://ex.org/a": "Notify",
        })

        result = await pf.apply(triples, "default", user_context)
        s_iris = [t.s.iri for t in result]

        assert "http://ex.org/a" in s_iris
        assert "http://ex.org/b" in s_iris
        assert "http://ex.org/c" in s_iris

    @pytest.mark.asyncio
    async def test_filtered_blocks_node(self, triples, user_context):
        pf = self._make_filter({
            "http://ex.org/b": "Filtered",
        })

        result = await pf.apply(triples, "default", user_context)
        s_iris = [t.s.iri for t in result]

        assert "http://ex.org/a" in s_iris
        assert "http://ex.org/b" not in s_iris
        assert "http://ex.org/c" in s_iris

    @pytest.mark.asyncio
    async def test_violation_blocks_node(self, triples, user_context):
        pf = self._make_filter({
            "http://ex.org/a": "Violation",
        })

        result = await pf.apply(triples, "default", user_context)
        s_iris = [t.s.iri for t in result]

        assert "http://ex.org/a" not in s_iris
        assert "http://ex.org/b" in s_iris

    @pytest.mark.asyncio
    async def test_notify_fires_callback(self, triples, user_context):
        callbacks = []

        async def on_eval(ev):
            callbacks.append(ev)

        pf = self._make_filter(
            {"http://ex.org/a": "Notify"},
            on_evaluation=on_eval,
        )

        await pf.apply(triples, "default", user_context)

        assert len(callbacks) == 1
        assert callbacks[0].determination == "Notify"
        assert callbacks[0].node_iri == "http://ex.org/a"

    @pytest.mark.asyncio
    async def test_filtered_fires_callback(self, triples, user_context):
        callbacks = []

        async def on_eval(ev):
            callbacks.append(ev)

        pf = self._make_filter(
            {"http://ex.org/b": "Filtered"},
            on_evaluation=on_eval,
        )

        await pf.apply(triples, "default", user_context)

        assert len(callbacks) == 1
        assert callbacks[0].determination == "Filtered"

    @pytest.mark.asyncio
    async def test_no_policies_returns_all(self, triples, user_context):
        async def query_fn(s, p, o, collection, g=""):
            return []

        pf = PolicyFilter(query_fn=query_fn)
        pf._policies = []

        result = await pf.apply(triples, "default", user_context)
        assert len(result) == len(triples)

    @pytest.mark.asyncio
    async def test_mixed_determinations(self, triples, user_context):
        callbacks = []

        async def on_eval(ev):
            callbacks.append(ev)

        pf = self._make_filter(
            {
                "http://ex.org/a": "Notify",
                "http://ex.org/b": "Filtered",
                "http://ex.org/c": "Violation",
            },
            on_evaluation=on_eval,
        )

        result = await pf.apply(triples, "default", user_context)
        s_iris = [t.s.iri for t in result]

        assert "http://ex.org/a" in s_iris
        assert "http://ex.org/b" not in s_iris
        assert "http://ex.org/c" not in s_iris

        assert len(callbacks) == 3
        determinations = {c.determination for c in callbacks}
        assert determinations == {"Notify", "Filtered", "Violation"}
