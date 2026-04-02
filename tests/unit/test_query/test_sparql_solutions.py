"""
Tests for SPARQL solution sequence operations.
"""

import pytest
from trustgraph.schema import Term, IRI, LITERAL
from trustgraph.query.sparql.solutions import (
    hash_join, left_join, union, project, distinct,
    order_by, slice_solutions, _terms_equal, _compatible,
)


# --- Test helpers ---

def iri(v):
    return Term(type=IRI, iri=v)

def lit(v):
    return Term(type=LITERAL, value=v)


# --- Fixtures ---

@pytest.fixture
def alice():
    return iri("http://example.com/alice")

@pytest.fixture
def bob():
    return iri("http://example.com/bob")

@pytest.fixture
def carol():
    return iri("http://example.com/carol")

@pytest.fixture
def knows():
    return iri("http://example.com/knows")

@pytest.fixture
def name_alice():
    return lit("Alice")

@pytest.fixture
def name_bob():
    return lit("Bob")


class TestTermsEqual:

    def test_equal_iris(self):
        assert _terms_equal(iri("http://x.com/a"), iri("http://x.com/a"))

    def test_unequal_iris(self):
        assert not _terms_equal(iri("http://x.com/a"), iri("http://x.com/b"))

    def test_equal_literals(self):
        assert _terms_equal(lit("hello"), lit("hello"))

    def test_unequal_literals(self):
        assert not _terms_equal(lit("hello"), lit("world"))

    def test_iri_vs_literal(self):
        assert not _terms_equal(iri("hello"), lit("hello"))

    def test_none_none(self):
        assert _terms_equal(None, None)

    def test_none_vs_term(self):
        assert not _terms_equal(None, iri("http://x.com/a"))


class TestCompatible:

    def test_no_shared_variables(self):
        assert _compatible({"a": iri("http://x")}, {"b": iri("http://y")})

    def test_shared_variable_same_value(self, alice):
        assert _compatible({"s": alice, "x": lit("1")}, {"s": alice, "y": lit("2")})

    def test_shared_variable_different_value(self, alice, bob):
        assert not _compatible({"s": alice}, {"s": bob})

    def test_empty_solutions(self):
        assert _compatible({}, {})

    def test_empty_vs_nonempty(self, alice):
        assert _compatible({}, {"s": alice})


class TestHashJoin:

    def test_join_on_shared_variable(self, alice, bob, name_alice, name_bob):
        left = [
            {"s": alice, "p": iri("http://example.com/knows"), "o": bob},
            {"s": bob, "p": iri("http://example.com/knows"), "o": alice},
        ]
        right = [
            {"s": alice, "label": name_alice},
            {"s": bob, "label": name_bob},
        ]
        result = hash_join(left, right)
        assert len(result) == 2
        # Check that joined solutions have all variables
        for sol in result:
            assert "s" in sol
            assert "p" in sol
            assert "o" in sol
            assert "label" in sol

    def test_join_no_shared_variables_cross_product(self, alice, bob):
        left = [{"a": alice}]
        right = [{"b": bob}, {"b": alice}]
        result = hash_join(left, right)
        assert len(result) == 2

    def test_join_no_matches(self, alice, bob):
        left = [{"s": alice}]
        right = [{"s": bob}]
        result = hash_join(left, right)
        assert len(result) == 0

    def test_join_empty_left(self, alice):
        result = hash_join([], [{"s": alice}])
        assert len(result) == 0

    def test_join_empty_right(self, alice):
        result = hash_join([{"s": alice}], [])
        assert len(result) == 0

    def test_join_multiple_matches(self, alice, name_alice):
        left = [
            {"s": alice, "p": iri("http://e.com/a")},
            {"s": alice, "p": iri("http://e.com/b")},
        ]
        right = [{"s": alice, "label": name_alice}]
        result = hash_join(left, right)
        assert len(result) == 2

    def test_join_preserves_values(self, alice, name_alice):
        left = [{"s": alice, "x": lit("1")}]
        right = [{"s": alice, "y": lit("2")}]
        result = hash_join(left, right)
        assert len(result) == 1
        assert result[0]["x"].value == "1"
        assert result[0]["y"].value == "2"


class TestLeftJoin:

    def test_left_join_with_matches(self, alice, bob, name_alice):
        left = [{"s": alice}, {"s": bob}]
        right = [{"s": alice, "label": name_alice}]
        result = left_join(left, right)
        assert len(result) == 2
        # Alice has label
        alice_sols = [s for s in result if s["s"].iri == "http://example.com/alice"]
        assert len(alice_sols) == 1
        assert "label" in alice_sols[0]
        # Bob preserved without label
        bob_sols = [s for s in result if s["s"].iri == "http://example.com/bob"]
        assert len(bob_sols) == 1
        assert "label" not in bob_sols[0]

    def test_left_join_no_matches(self, alice, bob):
        left = [{"s": alice}]
        right = [{"s": bob, "label": lit("Bob")}]
        result = left_join(left, right)
        assert len(result) == 1
        assert result[0]["s"].iri == "http://example.com/alice"
        assert "label" not in result[0]

    def test_left_join_empty_right(self, alice):
        left = [{"s": alice}]
        result = left_join(left, [])
        assert len(result) == 1

    def test_left_join_empty_left(self):
        result = left_join([], [{"s": iri("http://x")}])
        assert len(result) == 0

    def test_left_join_with_filter(self, alice, bob):
        left = [{"s": alice}, {"s": bob}]
        right = [
            {"s": alice, "val": lit("yes")},
            {"s": bob, "val": lit("no")},
        ]
        # Filter: only keep joins where val == "yes"
        result = left_join(
            left, right,
            filter_fn=lambda sol: sol.get("val") and sol["val"].value == "yes"
        )
        assert len(result) == 2
        # Alice matches filter
        alice_sols = [s for s in result if s["s"].iri == "http://example.com/alice"]
        assert "val" in alice_sols[0]
        assert alice_sols[0]["val"].value == "yes"
        # Bob doesn't match filter, preserved without val
        bob_sols = [s for s in result if s["s"].iri == "http://example.com/bob"]
        assert "val" not in bob_sols[0]


class TestUnion:

    def test_union_concatenates(self, alice, bob):
        left = [{"s": alice}]
        right = [{"s": bob}]
        result = union(left, right)
        assert len(result) == 2

    def test_union_preserves_order(self, alice, bob):
        left = [{"s": alice}]
        right = [{"s": bob}]
        result = union(left, right)
        assert result[0]["s"].iri == "http://example.com/alice"
        assert result[1]["s"].iri == "http://example.com/bob"

    def test_union_empty_left(self, alice):
        result = union([], [{"s": alice}])
        assert len(result) == 1

    def test_union_both_empty(self):
        result = union([], [])
        assert len(result) == 0

    def test_union_allows_duplicates(self, alice):
        result = union([{"s": alice}], [{"s": alice}])
        assert len(result) == 2


class TestProject:

    def test_project_keeps_selected(self, alice, name_alice):
        solutions = [{"s": alice, "label": name_alice, "extra": lit("x")}]
        result = project(solutions, ["s", "label"])
        assert len(result) == 1
        assert "s" in result[0]
        assert "label" in result[0]
        assert "extra" not in result[0]

    def test_project_missing_variable(self, alice):
        solutions = [{"s": alice}]
        result = project(solutions, ["s", "missing"])
        assert len(result) == 1
        assert "s" in result[0]
        assert "missing" not in result[0]

    def test_project_empty(self):
        result = project([], ["s"])
        assert len(result) == 0


class TestDistinct:

    def test_removes_duplicates(self, alice):
        solutions = [{"s": alice}, {"s": alice}, {"s": alice}]
        result = distinct(solutions)
        assert len(result) == 1

    def test_keeps_different(self, alice, bob):
        solutions = [{"s": alice}, {"s": bob}]
        result = distinct(solutions)
        assert len(result) == 2

    def test_empty(self):
        result = distinct([])
        assert len(result) == 0

    def test_multi_variable_distinct(self, alice, bob):
        solutions = [
            {"s": alice, "o": bob},
            {"s": alice, "o": bob},
            {"s": alice, "o": alice},
        ]
        result = distinct(solutions)
        assert len(result) == 2


class TestOrderBy:

    def test_order_by_ascending(self):
        solutions = [
            {"label": lit("Charlie")},
            {"label": lit("Alice")},
            {"label": lit("Bob")},
        ]
        key_fns = [(lambda sol: sol.get("label"), True)]
        result = order_by(solutions, key_fns)
        assert result[0]["label"].value == "Alice"
        assert result[1]["label"].value == "Bob"
        assert result[2]["label"].value == "Charlie"

    def test_order_by_descending(self):
        solutions = [
            {"label": lit("Alice")},
            {"label": lit("Charlie")},
            {"label": lit("Bob")},
        ]
        key_fns = [(lambda sol: sol.get("label"), False)]
        result = order_by(solutions, key_fns)
        assert result[0]["label"].value == "Charlie"
        assert result[1]["label"].value == "Bob"
        assert result[2]["label"].value == "Alice"

    def test_order_by_empty(self):
        result = order_by([], [(lambda sol: sol.get("x"), True)])
        assert len(result) == 0

    def test_order_by_no_keys(self, alice):
        solutions = [{"s": alice}]
        result = order_by(solutions, [])
        assert len(result) == 1


class TestSlice:

    def test_limit(self, alice, bob, carol):
        solutions = [{"s": alice}, {"s": bob}, {"s": carol}]
        result = slice_solutions(solutions, limit=2)
        assert len(result) == 2

    def test_offset(self, alice, bob, carol):
        solutions = [{"s": alice}, {"s": bob}, {"s": carol}]
        result = slice_solutions(solutions, offset=1)
        assert len(result) == 2
        assert result[0]["s"].iri == "http://example.com/bob"

    def test_offset_and_limit(self, alice, bob, carol):
        solutions = [{"s": alice}, {"s": bob}, {"s": carol}]
        result = slice_solutions(solutions, offset=1, limit=1)
        assert len(result) == 1
        assert result[0]["s"].iri == "http://example.com/bob"

    def test_limit_zero(self, alice):
        result = slice_solutions([{"s": alice}], limit=0)
        assert len(result) == 0

    def test_offset_beyond_length(self, alice):
        result = slice_solutions([{"s": alice}], offset=10)
        assert len(result) == 0

    def test_no_slice(self, alice, bob):
        solutions = [{"s": alice}, {"s": bob}]
        result = slice_solutions(solutions)
        assert len(result) == 2
