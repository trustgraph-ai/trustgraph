"""
Tests for the SPARQL algebra evaluator.

Verifies that evaluate() and _query_pattern() call TriplesClient.query()
with the correct arguments, and in particular that workspace is never
passed — workspace isolation is handled by pub/sub topic routing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call

from rdflib.term import Variable, URIRef, Literal
from rdflib.plugins.sparql.parserutils import CompValue

from trustgraph.schema import Term, IRI, LITERAL
from trustgraph.query.sparql.algebra import (
    evaluate, _query_pattern, _eval_bgp,
)


# --- Helpers ---

def iri(v):
    return Term(type=IRI, iri=v)


def lit(v):
    return Term(type=LITERAL, value=v)


def make_triple(s, p, o):
    t = MagicMock()
    t.s = s
    t.p = p
    t.o = o
    return t


def make_bgp(*patterns):
    """Build a CompValue BGP node from (s, p, o) tuples of rdflib terms."""
    node = CompValue("BGP")
    node.triples = list(patterns)
    return node


def make_project(inner, variables):
    node = CompValue("Project")
    node.p = inner
    node.PV = [Variable(v) for v in variables]
    return node


def make_select(inner):
    node = CompValue("SelectQuery")
    node.p = inner
    return node


def make_join(left, right):
    node = CompValue("Join")
    node.p1 = left
    node.p2 = right
    return node


def make_union(left, right):
    node = CompValue("Union")
    node.p1 = left
    node.p2 = right
    return node


def make_slice(inner, start, length):
    node = CompValue("Slice")
    node.p = inner
    node.start = start
    node.length = length
    return node


def make_distinct(inner):
    node = CompValue("Distinct")
    node.p = inner
    return node


class TestQueryPattern:
    """Tests for _query_pattern — the leaf that calls TriplesClient."""

    @pytest.mark.asyncio
    async def test_passes_correct_args(self):
        tc = AsyncMock()
        tc.query.return_value = []

        await _query_pattern(
            tc,
            s=iri("http://example.com/s"),
            p=iri("http://example.com/p"),
            o=None,
            collection="my-collection",
            limit=100,
        )

        tc.query.assert_called_once_with(
            s=iri("http://example.com/s"),
            p=iri("http://example.com/p"),
            o=None,
            limit=100,
            collection="my-collection",
        )

    @pytest.mark.asyncio
    async def test_workspace_not_passed(self):
        tc = AsyncMock()
        tc.query.return_value = []

        await _query_pattern(tc, None, None, None, "default", 10)

        kwargs = tc.query.call_args.kwargs
        assert "workspace" not in kwargs

    @pytest.mark.asyncio
    async def test_returns_query_results(self):
        tc = AsyncMock()
        triple = make_triple(iri("http://a"), iri("http://b"), lit("c"))
        tc.query.return_value = [triple]

        results = await _query_pattern(tc, None, None, None, "default", 10)

        assert len(results) == 1
        assert results[0].s.iri == "http://a"


class TestEvalBgp:
    """Tests for BGP evaluation — triple pattern queries."""

    @pytest.mark.asyncio
    async def test_single_pattern_all_variables(self):
        tc = AsyncMock()
        triple = make_triple(iri("http://s"), iri("http://p"), lit("o"))
        tc.query.return_value = [triple]

        bgp = make_bgp(
            (Variable("s"), Variable("p"), Variable("o")),
        )

        solutions = await evaluate(bgp, tc, collection="default", limit=100)

        assert len(solutions) == 1
        assert solutions[0]["s"].iri == "http://s"
        assert solutions[0]["p"].iri == "http://p"
        assert solutions[0]["o"].value == "o"

    @pytest.mark.asyncio
    async def test_single_pattern_bound_subject(self):
        tc = AsyncMock()
        tc.query.return_value = [
            make_triple(iri("http://s"), iri("http://p"), lit("val")),
        ]

        bgp = make_bgp(
            (URIRef("http://s"), Variable("p"), Variable("o")),
        )

        solutions = await evaluate(bgp, tc, collection="default")

        tc.query.assert_called_once()
        kwargs = tc.query.call_args.kwargs
        assert "workspace" not in kwargs
        assert kwargs["collection"] == "default"

    @pytest.mark.asyncio
    async def test_empty_bgp_returns_empty_solution(self):
        tc = AsyncMock()

        bgp = make_bgp()

        solutions = await evaluate(bgp, tc, collection="default")

        assert solutions == [{}]
        tc.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_results_returns_empty(self):
        tc = AsyncMock()
        tc.query.return_value = []

        bgp = make_bgp(
            (Variable("s"), Variable("p"), Variable("o")),
        )

        solutions = await evaluate(bgp, tc, collection="default")

        assert solutions == []


class TestEvaluate:
    """Tests for the top-level evaluate() dispatcher."""

    @pytest.mark.asyncio
    async def test_select_query_node(self):
        tc = AsyncMock()
        tc.query.return_value = [
            make_triple(iri("http://s"), iri("http://p"), lit("o")),
        ]

        bgp = make_bgp(
            (Variable("s"), Variable("p"), Variable("o")),
        )
        select = make_select(make_project(bgp, ["s", "p"]))

        solutions = await evaluate(select, tc, collection="default")

        assert len(solutions) == 1
        assert "s" in solutions[0]
        assert "p" in solutions[0]
        assert "o" not in solutions[0]

    @pytest.mark.asyncio
    async def test_workspace_never_in_query_calls(self):
        """Verify that no matter the algebra structure, workspace is never
        passed to TriplesClient.query()."""
        tc = AsyncMock()
        tc.query.return_value = [
            make_triple(iri("http://s"), iri("http://p"), lit("o")),
        ]

        bgp1 = make_bgp((Variable("s"), Variable("p"), Variable("o")))
        bgp2 = make_bgp((Variable("a"), Variable("b"), Variable("c")))
        tree = make_select(make_project(
            make_union(bgp1, bgp2), ["s", "p", "o"]
        ))

        await evaluate(tree, tc, collection="test-coll")

        for c in tc.query.call_args_list:
            assert "workspace" not in c.kwargs

    @pytest.mark.asyncio
    async def test_join(self):
        tc = AsyncMock()
        tc.query.side_effect = [
            [make_triple(iri("http://a"), iri("http://p"), lit("v"))],
            [make_triple(iri("http://a"), iri("http://q"), lit("w"))],
        ]

        bgp1 = make_bgp((Variable("s"), URIRef("http://p"), Variable("v1")))
        bgp2 = make_bgp((Variable("s"), URIRef("http://q"), Variable("v2")))
        tree = make_join(bgp1, bgp2)

        solutions = await evaluate(tree, tc, collection="default")

        assert len(solutions) == 1
        assert solutions[0]["s"].iri == "http://a"

    @pytest.mark.asyncio
    async def test_slice(self):
        tc = AsyncMock()
        triples = [
            make_triple(iri(f"http://s{i}"), iri("http://p"), lit(f"o{i}"))
            for i in range(5)
        ]
        tc.query.return_value = triples

        bgp = make_bgp((Variable("s"), Variable("p"), Variable("o")))
        tree = make_slice(bgp, start=1, length=2)

        solutions = await evaluate(tree, tc, collection="default")

        assert len(solutions) == 2

    @pytest.mark.asyncio
    async def test_distinct(self):
        tc = AsyncMock()
        triple = make_triple(iri("http://s"), iri("http://p"), lit("o"))
        tc.query.return_value = [triple, triple]

        bgp = make_bgp((Variable("s"), Variable("p"), Variable("o")))
        tree = make_distinct(bgp)

        solutions = await evaluate(tree, tc, collection="default")

        assert len(solutions) == 1

    @pytest.mark.asyncio
    async def test_unsupported_node_returns_empty_solution(self):
        tc = AsyncMock()

        node = CompValue("SomethingUnknown")

        solutions = await evaluate(node, tc, collection="default")

        assert solutions == [{}]
        tc.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_compvalue_returns_empty_solution(self):
        tc = AsyncMock()

        solutions = await evaluate("not a node", tc, collection="default")

        assert solutions == [{}]
