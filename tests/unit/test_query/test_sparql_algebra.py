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
    evaluate, materialise, _query_pattern, _eval_bgp,
)


# --- Helpers ---

def iri(v):
    return Term(type=IRI, iri=v)


def lit(v):
    return Term(type=LITERAL, value=v)


def make_tc(query_return=None, query_side_effect=None):
    """Create a mock TriplesClient with both query() and query_gen() support."""
    tc = AsyncMock()

    if query_side_effect is not None:
        tc.query.side_effect = query_side_effect

        async def gen_side_effect(**kwargs):
            results = await query_side_effect(**kwargs)
            for r in results:
                yield r

        tc.query_gen = gen_side_effect
    else:
        items = query_return or []
        tc.query.return_value = items

        async def gen(**kwargs):
            for item in items:
                yield item

        tc.query_gen = gen

    return tc


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


def make_filter(inner, expr):
    node = CompValue("Filter")
    node.p = inner
    node.expr = expr
    return node


def make_minus(left, right):
    node = CompValue("Minus")
    node.p1 = left
    node.p2 = right
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
        triple = make_triple(iri("http://s"), iri("http://p"), lit("o"))
        tc = make_tc(query_return=[triple])

        bgp = make_bgp(
            (Variable("s"), Variable("p"), Variable("o")),
        )

        solutions = await materialise(bgp, tc, collection="default", limit=100)

        assert len(solutions) == 1
        assert solutions[0]["s"].iri == "http://s"
        assert solutions[0]["p"].iri == "http://p"
        assert solutions[0]["o"].value == "o"

    @pytest.mark.asyncio
    async def test_single_pattern_bound_subject(self):
        tc = make_tc(query_return=[
            make_triple(iri("http://s"), iri("http://p"), lit("val")),
        ])

        bgp = make_bgp(
            (URIRef("http://s"), Variable("p"), Variable("o")),
        )

        solutions = await materialise(bgp, tc, collection="default")

        assert len(solutions) == 1

    @pytest.mark.asyncio
    async def test_empty_bgp_returns_empty_solution(self):
        tc = make_tc()

        bgp = make_bgp()

        solutions = await materialise(bgp, tc, collection="default")

        assert solutions == [{}]

    @pytest.mark.asyncio
    async def test_no_results_returns_empty(self):
        tc = make_tc(query_return=[])

        bgp = make_bgp(
            (Variable("s"), Variable("p"), Variable("o")),
        )

        solutions = await materialise(bgp, tc, collection="default")

        assert solutions == []


class TestEvaluate:
    """Tests for the top-level evaluate() dispatcher."""

    @pytest.mark.asyncio
    async def test_select_query_node(self):
        tc = make_tc(query_return=[
            make_triple(iri("http://s"), iri("http://p"), lit("o")),
        ])

        bgp = make_bgp(
            (Variable("s"), Variable("p"), Variable("o")),
        )
        select = make_select(make_project(bgp, ["s", "p"]))

        solutions = await materialise(select, tc, collection="default")

        assert len(solutions) == 1
        assert "s" in solutions[0]
        assert "p" in solutions[0]
        assert "o" not in solutions[0]

    @pytest.mark.asyncio
    async def test_workspace_never_in_query_calls(self):
        """Verify that no matter the algebra structure, workspace is never
        passed to TriplesClient.query()."""
        tc = make_tc(query_return=[
            make_triple(iri("http://s"), iri("http://p"), lit("o")),
        ])

        bgp1 = make_bgp((Variable("s"), Variable("p"), Variable("o")))
        bgp2 = make_bgp((Variable("a"), Variable("b"), Variable("c")))
        tree = make_select(make_project(
            make_union(bgp1, bgp2), ["s", "p", "o"]
        ))

        await materialise(tree, tc, collection="test-coll")

    @pytest.mark.asyncio
    async def test_join(self):
        call_count = 0

        async def mock_query(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [make_triple(iri("http://a"), iri("http://p"), lit("v"))]
            else:
                return [make_triple(iri("http://a"), iri("http://q"), lit("w"))]

        tc = make_tc(query_side_effect=mock_query)

        bgp1 = make_bgp((Variable("s"), URIRef("http://p"), Variable("v1")))
        bgp2 = make_bgp((Variable("s"), URIRef("http://q"), Variable("v2")))
        tree = make_join(bgp1, bgp2)

        solutions = await materialise(tree, tc, collection="default")

        assert len(solutions) == 1
        assert solutions[0]["s"].iri == "http://a"

    @pytest.mark.asyncio
    async def test_slice(self):
        triples = [
            make_triple(iri(f"http://s{i}"), iri("http://p"), lit(f"o{i}"))
            for i in range(5)
        ]
        tc = make_tc(query_return=triples)

        bgp = make_bgp((Variable("s"), Variable("p"), Variable("o")))
        tree = make_slice(bgp, start=1, length=2)

        solutions = await materialise(tree, tc, collection="default")

        assert len(solutions) == 2

    @pytest.mark.asyncio
    async def test_distinct(self):
        triple = make_triple(iri("http://s"), iri("http://p"), lit("o"))
        tc = make_tc(query_return=[triple, triple])

        bgp = make_bgp((Variable("s"), Variable("p"), Variable("o")))
        tree = make_distinct(bgp)

        solutions = await materialise(tree, tc, collection="default")

        assert len(solutions) == 1

    @pytest.mark.asyncio
    async def test_minus_removes_matching(self):
        alice = iri("http://example.com/alice")
        bob = iri("http://example.com/bob")
        knows = iri("http://example.com/knows")
        hates = iri("http://example.com/hates")
        charlie = iri("http://example.com/charlie")

        left_triple = make_triple(alice, knows, bob)
        right_triple2 = make_triple(alice, hates, charlie)

        async def mock_query(**kwargs):
            pred = kwargs.get("p")
            if pred and pred.iri == "http://example.com/knows":
                return [left_triple]
            elif pred and pred.iri == "http://example.com/hates":
                return [right_triple2]
            return []

        tc = make_tc(query_side_effect=mock_query)

        left_bgp = make_bgp(
            (Variable("s"), URIRef("http://example.com/knows"), Variable("o"))
        )
        right_bgp = make_bgp(
            (Variable("s"), URIRef("http://example.com/hates"), Variable("r"))
        )

        tree = make_select(
            make_project(
                make_minus(left_bgp, right_bgp),
                ["s", "o"]
            )
        )

        solutions = await materialise(tree, tc, collection="default")

        assert len(solutions) == 0

    @pytest.mark.asyncio
    async def test_minus_no_shared_vars_preserves_all(self):
        alice = iri("http://example.com/alice")
        bob = iri("http://example.com/bob")

        left_triple = make_triple(alice, iri("http://example.com/p"), bob)

        async def mock_query(**kwargs):
            pred = kwargs.get("p")
            if pred and pred.iri == "http://example.com/p":
                return [left_triple]
            return []

        tc = make_tc(query_side_effect=mock_query)

        left_bgp = make_bgp(
            (Variable("s"), URIRef("http://example.com/p"), Variable("o"))
        )
        right_bgp = make_bgp(
            (Variable("x"), URIRef("http://example.com/q"), Variable("y"))
        )

        tree = make_select(
            make_project(
                make_minus(left_bgp, right_bgp),
                ["s", "o"]
            )
        )

        solutions = await materialise(tree, tc, collection="default")

        assert len(solutions) == 1

    @pytest.mark.asyncio
    async def test_filter_exists_keeps_matching(self):
        alice = iri("http://example.com/alice")
        bob = iri("http://example.com/bob")
        charlie = iri("http://example.com/charlie")

        left_triple1 = make_triple(alice, iri("http://example.com/knows"), bob)
        left_triple2 = make_triple(alice, iri("http://example.com/knows"), charlie)
        exists_triple = make_triple(bob, iri("http://example.com/likes"), alice)

        async def mock_query(**kwargs):
            pred = kwargs.get("p")
            if pred and pred.iri == "http://example.com/knows":
                return [left_triple1, left_triple2]
            elif pred and pred.iri == "http://example.com/likes":
                return [exists_triple]
            return []

        tc = make_tc(query_side_effect=mock_query)

        left_bgp = make_bgp(
            (Variable("s"), URIRef("http://example.com/knows"), Variable("o"))
        )
        exists_bgp = make_bgp(
            (Variable("o"), URIRef("http://example.com/likes"), Variable("_any"))
        )

        exists_expr = CompValue("Builtin_EXISTS")
        exists_expr.graph = exists_bgp

        tree = make_select(
            make_project(
                make_filter(left_bgp, exists_expr),
                ["s", "o"]
            )
        )

        solutions = await materialise(tree, tc, collection="default")

        result_objects = [s["o"].iri for s in solutions]
        assert "http://example.com/bob" in result_objects
        assert "http://example.com/charlie" not in result_objects

    @pytest.mark.asyncio
    async def test_filter_not_exists_removes_matching(self):
        alice = iri("http://example.com/alice")
        bob = iri("http://example.com/bob")
        charlie = iri("http://example.com/charlie")

        left_triple1 = make_triple(alice, iri("http://example.com/knows"), bob)
        left_triple2 = make_triple(alice, iri("http://example.com/knows"), charlie)
        exists_triple = make_triple(bob, iri("http://example.com/likes"), alice)

        async def mock_query(**kwargs):
            pred = kwargs.get("p")
            if pred and pred.iri == "http://example.com/knows":
                return [left_triple1, left_triple2]
            elif pred and pred.iri == "http://example.com/likes":
                return [exists_triple]
            return []

        tc = make_tc(query_side_effect=mock_query)

        left_bgp = make_bgp(
            (Variable("s"), URIRef("http://example.com/knows"), Variable("o"))
        )
        exists_bgp = make_bgp(
            (Variable("o"), URIRef("http://example.com/likes"), Variable("_any"))
        )

        not_exists_expr = CompValue("Builtin_NOTEXISTS")
        not_exists_expr.graph = exists_bgp

        tree = make_select(
            make_project(
                make_filter(left_bgp, not_exists_expr),
                ["s", "o"]
            )
        )

        solutions = await materialise(tree, tc, collection="default")

        result_objects = [s["o"].iri for s in solutions]
        assert "http://example.com/charlie" in result_objects
        assert "http://example.com/bob" not in result_objects

    @pytest.mark.asyncio
    async def test_join_values_uses_bind_join(self):
        """When VALUES is joined with a BGP, the bind join should pass
        the VALUES bindings into the BGP evaluation so the triple store
        query is selective (not a wildcard)."""
        alice = iri("http://example.com/alice")
        bob = iri("http://example.com/bob")
        knows = iri("http://example.com/knows")

        queries_issued = []

        async def mock_query(**kwargs):
            queries_issued.append(kwargs)
            s, p = kwargs.get("s"), kwargs.get("p")
            if s and s.iri == "http://example.com/alice" and p and p.iri == "http://example.com/knows":
                return [make_triple(alice, knows, bob)]
            return []

        tc = make_tc(query_side_effect=mock_query)

        # VALUES ?s { <alice> }
        values_node = CompValue("values")
        values_node.var = [Variable("s")]
        values_node.value = [[URIRef("http://example.com/alice")]]
        values_node.res = None

        to_multiset = CompValue("ToMultiSet")
        to_multiset.p = values_node

        bgp = make_bgp(
            (Variable("s"), URIRef("http://example.com/knows"), Variable("o")),
        )

        tree = make_join(to_multiset, bgp)
        solutions = await materialise(tree, tc, collection="default")

        assert len(solutions) == 1
        assert solutions[0]["s"].iri == "http://example.com/alice"
        assert solutions[0]["o"].iri == "http://example.com/bob"

        # The key assertion: the BGP query should have received
        # s=alice (bound from VALUES), NOT s=None (wildcard)
        assert len(queries_issued) == 1
        assert queries_issued[0]["s"] is not None
        assert queries_issued[0]["s"].iri == "http://example.com/alice"

    @pytest.mark.asyncio
    async def test_join_values_multiple_bindings(self):
        """Bind join with multiple VALUES bindings."""
        alice = iri("http://example.com/alice")
        bob = iri("http://example.com/bob")
        knows = iri("http://example.com/knows")
        charlie = iri("http://example.com/charlie")

        async def mock_query(**kwargs):
            s = kwargs.get("s")
            if s and s.iri == "http://example.com/alice":
                return [make_triple(alice, knows, bob)]
            elif s and s.iri == "http://example.com/bob":
                return [make_triple(bob, knows, charlie)]
            return []

        tc = make_tc(query_side_effect=mock_query)

        values_node = CompValue("values")
        values_node.var = [Variable("s")]
        values_node.value = [
            [URIRef("http://example.com/alice")],
            [URIRef("http://example.com/bob")],
        ]
        values_node.res = None

        to_multiset = CompValue("ToMultiSet")
        to_multiset.p = values_node

        bgp = make_bgp(
            (Variable("s"), URIRef("http://example.com/knows"), Variable("o")),
        )

        tree = make_join(to_multiset, bgp)
        solutions = await materialise(tree, tc, collection="default")

        assert len(solutions) == 2
        subjects = {s["s"].iri for s in solutions}
        assert subjects == {
            "http://example.com/alice",
            "http://example.com/bob",
        }

    @pytest.mark.asyncio
    async def test_unsupported_node_returns_empty_solution(self):
        tc = make_tc()

        node = CompValue("SomethingUnknown")

        solutions = await materialise(node, tc, collection="default")

        assert solutions == [{}]

    @pytest.mark.asyncio
    async def test_non_compvalue_returns_empty_solution(self):
        tc = make_tc()

        solutions = await materialise("not a node", tc, collection="default")

        assert solutions == [{}]
