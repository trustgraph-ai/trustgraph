"""
Tests for the PolicyFilter determination handling.

Verifies that blocks=True removes nodes, blocks=False passes them
through, callbacks fire for all determinations, enforcement mode
(load_policies/has_policies), and caching.
"""

import time
import pytest
from unittest.mock import AsyncMock

from trustgraph.policy.policy_filter import (
    PolicyFilter, PolicyEvaluation, LoadedPolicy,
    QueryCache, SparqlCache,
)
from trustgraph.schema import Triple, Term, IRI, LITERAL, UserContext


TG_POL = "https://trustgraph.ai/ontology/policy/"


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

    def test_fields(self):
        ev = PolicyEvaluation(
            node_iri="http://example.org/n1",
            policy_uri="http://example.org/pol1",
            policy_label="Test Policy",
            determination=f"{TG_POL}Filtered",
            blocks=True,
            reason="Subject not assigned.",
        )
        assert ev.policy_uri == "http://example.org/pol1"
        assert ev.node_iri == "http://example.org/n1"
        assert ev.policy_label == "Test Policy"
        assert ev.determination == f"{TG_POL}Filtered"
        assert ev.blocks is True
        assert ev.reason == "Subject not assigned."

    def test_defaults(self):
        ev = PolicyEvaluation(
            node_iri="http://example.org/n1",
            policy_uri="http://example.org/pol1",
            policy_label="Test",
            determination=f"{TG_POL}Violation",
        )
        assert ev.blocks is True
        assert ev.reason == ""


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

    def _make_filter(self, evaluation_map, on_evaluation=None):
        """Create a PolicyFilter with pre-loaded policies.

        evaluation_map: dict of {node_iri: (determination, blocks, reason)}
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
            order=0,
            sparql_select="SELECT ?this WHERE { ?this ?p ?o }",
            target_prefixes={},
            sparql_construct="CONSTRUCT { } WHERE { }",
            construct_prefixes={},
        )
        pf._policies = [policy]
        pf._required_predicates = set()

        async def mock_evaluate(node_iri, collection, context_graph, graph=None):
            if node_iri in evaluation_map:
                det, blocks, reason = evaluation_map[node_iri]
                return PolicyEvaluation(
                    node_iri=node_iri,
                    policy_uri="http://ex.org/test-policy",
                    policy_label="Test Policy",
                    determination=det,
                    blocks=blocks,
                    reason=reason,
                )
            return None

        pf._evaluate_node = mock_evaluate
        return pf

    @pytest.mark.asyncio
    async def test_non_blocking_passes_through(
        self, triples, user_context,
    ):
        pf = self._make_filter({
            "http://ex.org/a": (
                f"{TG_POL}SensitiveAccess", False, "Logged.",
            ),
        })

        result = await pf.apply(triples, "default", user_context)
        s_iris = [t.s.iri for t in result]

        assert "http://ex.org/a" in s_iris
        assert "http://ex.org/b" in s_iris
        assert "http://ex.org/c" in s_iris

    @pytest.mark.asyncio
    async def test_blocking_filtered_removes_node(
        self, triples, user_context,
    ):
        pf = self._make_filter({
            "http://ex.org/b": (
                f"{TG_POL}Filtered", True, "Not assigned.",
            ),
        })

        result = await pf.apply(triples, "default", user_context)
        s_iris = [t.s.iri for t in result]

        assert "http://ex.org/a" in s_iris
        assert "http://ex.org/b" not in s_iris
        assert "http://ex.org/c" in s_iris

    @pytest.mark.asyncio
    async def test_blocking_violation_removes_node(
        self, triples, user_context,
    ):
        pf = self._make_filter({
            "http://ex.org/a": (
                f"{TG_POL}Violation", True, "Security barrier.",
            ),
        })

        result = await pf.apply(triples, "default", user_context)
        s_iris = [t.s.iri for t in result]

        assert "http://ex.org/a" not in s_iris
        assert "http://ex.org/b" in s_iris

    @pytest.mark.asyncio
    async def test_non_blocking_fires_callback(
        self, triples, user_context,
    ):
        callbacks = []

        async def on_eval(ev):
            callbacks.append(ev)

        pf = self._make_filter(
            {"http://ex.org/a": (
                f"{TG_POL}SensitiveAccess", False, "Logged.",
            )},
            on_evaluation=on_eval,
        )

        await pf.apply(triples, "default", user_context)

        assert len(callbacks) == 1
        assert callbacks[0].determination == f"{TG_POL}SensitiveAccess"
        assert callbacks[0].blocks is False
        assert callbacks[0].reason == "Logged."
        assert callbacks[0].node_iri == "http://ex.org/a"

    @pytest.mark.asyncio
    async def test_blocking_fires_callback(self, triples, user_context):
        callbacks = []

        async def on_eval(ev):
            callbacks.append(ev)

        pf = self._make_filter(
            {"http://ex.org/b": (
                f"{TG_POL}Filtered", True, "Not assigned.",
            )},
            on_evaluation=on_eval,
        )

        await pf.apply(triples, "default", user_context)

        assert len(callbacks) == 1
        assert callbacks[0].determination == f"{TG_POL}Filtered"
        assert callbacks[0].blocks is True

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
                "http://ex.org/a": (
                    f"{TG_POL}SensitiveAccess", False, "Logged.",
                ),
                "http://ex.org/b": (
                    f"{TG_POL}Filtered", True, "Not assigned.",
                ),
                "http://ex.org/c": (
                    f"{TG_POL}Violation", True, "Security barrier.",
                ),
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
        assert determinations == {
            f"{TG_POL}SensitiveAccess",
            f"{TG_POL}Filtered",
            f"{TG_POL}Violation",
        }

    @pytest.mark.asyncio
    async def test_custom_determination_iri(self, triples, user_context):
        callbacks = []

        async def on_eval(ev):
            callbacks.append(ev)

        custom_iri = "http://myorg.com/policy/AuditRequired"
        pf = self._make_filter(
            {"http://ex.org/a": (custom_iri, False, "Audit logged.")},
            on_evaluation=on_eval,
        )

        result = await pf.apply(triples, "default", user_context)
        s_iris = [t.s.iri for t in result]

        assert "http://ex.org/a" in s_iris
        assert len(callbacks) == 1
        assert callbacks[0].determination == custom_iri
        assert callbacks[0].blocks is False


class TestEnforcementMode:

    @pytest.mark.asyncio
    async def test_has_policies_false_before_load(self):
        async def query_fn(s, p, o, collection, g=""):
            return []

        pf = PolicyFilter(query_fn=query_fn)
        assert pf.has_policies() is False

    @pytest.mark.asyncio
    async def test_has_policies_false_when_none_exist(self):
        async def query_fn(s, p, o, collection, g=""):
            return []

        pf = PolicyFilter(query_fn=query_fn)
        await pf.load_policies("default")
        assert pf.has_policies() is False

    @pytest.mark.asyncio
    async def test_has_policies_true_when_loaded(self):
        async def query_fn(s, p, o, collection, g=""):
            return []

        pf = PolicyFilter(query_fn=query_fn)
        pf._policies = [
            LoadedPolicy(
                uri="http://ex.org/p1", label="P1", order=0,
                sparql_select="SELECT ?this WHERE { ?this ?p ?o }",
                target_prefixes={},
                sparql_construct="CONSTRUCT { } WHERE { }",
                construct_prefixes={},
            ),
        ]
        assert pf.has_policies() is True

    @pytest.mark.asyncio
    async def test_load_policies_idempotent(self):
        call_count = 0

        async def query_fn(s, p, o, collection, g=""):
            nonlocal call_count
            call_count += 1
            return []

        pf = PolicyFilter(query_fn=query_fn)
        await pf.load_policies("default")
        await pf.load_policies("default")

        assert call_count == 1


class TestQueryCache:

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        call_count = 0

        async def query_fn(s, p, o, collection, g=""):
            nonlocal call_count
            call_count += 1
            return [make_triple("http://ex.org/a", "http://ex.org/p", "v")]

        cache = QueryCache(query_fn, ttl=30)
        s = Term(type=IRI, iri="http://ex.org/a")
        p = Term(type=IRI, iri="http://ex.org/p")

        r1 = await cache.query(s, p, None, "col", "")
        r2 = await cache.query(s, p, None, "col", "")

        assert call_count == 1
        assert len(r1) == 1
        assert r1 is r2

    @pytest.mark.asyncio
    async def test_cache_miss_different_key(self):
        call_count = 0

        async def query_fn(s, p, o, collection, g=""):
            nonlocal call_count
            call_count += 1
            return []

        cache = QueryCache(query_fn, ttl=30)
        s1 = Term(type=IRI, iri="http://ex.org/a")
        s2 = Term(type=IRI, iri="http://ex.org/b")
        p = Term(type=IRI, iri="http://ex.org/p")

        await cache.query(s1, p, None, "col", "")
        await cache.query(s2, p, None, "col", "")

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cache_eviction_by_size(self):
        async def query_fn(s, p, o, collection, g=""):
            return []

        cache = QueryCache(query_fn, ttl=30, max_size=2)
        p = Term(type=IRI, iri="http://ex.org/p")

        for i in range(3):
            s = Term(type=IRI, iri=f"http://ex.org/{i}")
            await cache.query(s, p, None, "col", "")

        assert len(cache._cache) == 2


class TestSparqlCache:

    def test_cache_hit(self):
        cache = SparqlCache()
        query = "SELECT ?s WHERE { ?s ?p ?o }"

        c1 = cache.prepare(query)
        c2 = cache.prepare(query)

        assert c1 is c2

    def test_cache_miss_different_query(self):
        cache = SparqlCache()

        c1 = cache.prepare("SELECT ?s WHERE { ?s ?p ?o }")
        c2 = cache.prepare("SELECT ?x WHERE { ?x ?y ?z }")

        assert c1 is not c2

    def test_cache_eviction_by_size(self):
        cache = SparqlCache(max_size=2)

        cache.prepare("SELECT ?a WHERE { ?a ?b ?c }")
        cache.prepare("SELECT ?d WHERE { ?d ?e ?f }")
        cache.prepare("SELECT ?g WHERE { ?g ?h ?i }")

        assert len(cache._cache) == 2
