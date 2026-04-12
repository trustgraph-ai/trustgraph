"""
Tests for SPARQL FILTER expression evaluator.
"""

import pytest
from trustgraph.schema import Term, IRI, LITERAL, BLANK
from trustgraph.query.sparql.expressions import (
    evaluate_expression, _effective_boolean, _to_string, _to_numeric,
    _comparable_value,
)


# --- Helpers ---

def iri(v):
    return Term(type=IRI, iri=v)

def lit(v, datatype="", language=""):
    return Term(type=LITERAL, value=v, datatype=datatype, language=language)

def blank(v):
    return Term(type=BLANK, id=v)

XSD = "http://www.w3.org/2001/XMLSchema#"


class TestEvaluateExpression:
    """Test expression evaluation with rdflib algebra nodes."""

    def test_variable_bound(self):
        from rdflib.term import Variable
        result = evaluate_expression(Variable("x"), {"x": lit("hello")})
        assert result.value == "hello"

    def test_variable_unbound(self):
        from rdflib.term import Variable
        result = evaluate_expression(Variable("x"), {})
        assert result is None

    def test_uriref_constant(self):
        from rdflib import URIRef
        result = evaluate_expression(
            URIRef("http://example.com/a"), {}
        )
        assert result.type == IRI
        assert result.iri == "http://example.com/a"

    def test_literal_constant(self):
        from rdflib import Literal
        result = evaluate_expression(Literal("hello"), {})
        assert result.type == LITERAL
        assert result.value == "hello"

    def test_boolean_constant(self):
        assert evaluate_expression(True, {}) is True
        assert evaluate_expression(False, {}) is False

    def test_numeric_constant(self):
        assert evaluate_expression(42, {}) == 42
        assert evaluate_expression(3.14, {}) == 3.14

    def test_none_returns_true(self):
        assert evaluate_expression(None, {}) is True


class TestRelationalExpressions:
    """Test comparison operators via CompValue nodes."""

    def _make_relational(self, left, op, right):
        from rdflib.plugins.sparql.parserutils import CompValue
        return CompValue("RelationalExpression",
                        expr=left, op=op, other=right)

    def test_equal_literals(self):
        from rdflib import Literal
        expr = self._make_relational(Literal("a"), "=", Literal("a"))
        assert evaluate_expression(expr, {}) is True

    def test_not_equal_literals(self):
        from rdflib import Literal
        expr = self._make_relational(Literal("a"), "!=", Literal("b"))
        assert evaluate_expression(expr, {}) is True

    def test_less_than(self):
        from rdflib import Literal
        expr = self._make_relational(Literal("a"), "<", Literal("b"))
        assert evaluate_expression(expr, {}) is True

    def test_greater_than(self):
        from rdflib import Literal
        expr = self._make_relational(Literal("b"), ">", Literal("a"))
        assert evaluate_expression(expr, {}) is True

    def test_equal_with_variables(self):
        from rdflib.term import Variable
        expr = self._make_relational(Variable("x"), "=", Variable("y"))
        sol = {"x": lit("same"), "y": lit("same")}
        assert evaluate_expression(expr, sol) is True

    def test_unequal_with_variables(self):
        from rdflib.term import Variable
        expr = self._make_relational(Variable("x"), "=", Variable("y"))
        sol = {"x": lit("one"), "y": lit("two")}
        assert evaluate_expression(expr, sol) is False

    def test_none_operand_returns_false(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_relational(Variable("x"), "=", Literal("a"))
        assert evaluate_expression(expr, {}) is False


class TestLogicalExpressions:

    def _make_and(self, exprs):
        from rdflib.plugins.sparql.parserutils import CompValue
        return CompValue("ConditionalAndExpression",
                        expr=exprs[0], other=exprs[1:])

    def _make_or(self, exprs):
        from rdflib.plugins.sparql.parserutils import CompValue
        return CompValue("ConditionalOrExpression",
                        expr=exprs[0], other=exprs[1:])

    def _make_not(self, expr):
        from rdflib.plugins.sparql.parserutils import CompValue
        return CompValue("UnaryNot", expr=expr)

    def test_and_true_true(self):
        result = evaluate_expression(self._make_and([True, True]), {})
        assert result is True

    def test_and_true_false(self):
        result = evaluate_expression(self._make_and([True, False]), {})
        assert result is False

    def test_or_false_true(self):
        result = evaluate_expression(self._make_or([False, True]), {})
        assert result is True

    def test_or_false_false(self):
        result = evaluate_expression(self._make_or([False, False]), {})
        assert result is False

    def test_not_true(self):
        result = evaluate_expression(self._make_not(True), {})
        assert result is False

    def test_not_false(self):
        result = evaluate_expression(self._make_not(False), {})
        assert result is True


class TestBuiltinFunctions:

    def _make_builtin(self, name, **kwargs):
        from rdflib.plugins.sparql.parserutils import CompValue
        return CompValue(f"Builtin_{name}", **kwargs)

    def test_bound_true(self):
        from rdflib.term import Variable
        expr = self._make_builtin("BOUND", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("hi")}) is True

    def test_bound_false(self):
        from rdflib.term import Variable
        expr = self._make_builtin("BOUND", arg=Variable("x"))
        assert evaluate_expression(expr, {}) is False

    def test_isiri_true(self):
        from rdflib.term import Variable
        expr = self._make_builtin("isIRI", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": iri("http://x")}) is True

    def test_isiri_false(self):
        from rdflib.term import Variable
        expr = self._make_builtin("isIRI", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("hello")}) is False

    def test_isliteral_true(self):
        from rdflib.term import Variable
        expr = self._make_builtin("isLITERAL", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("hello")}) is True

    def test_isliteral_false(self):
        from rdflib.term import Variable
        expr = self._make_builtin("isLITERAL", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": iri("http://x")}) is False

    def test_isblank_true(self):
        from rdflib.term import Variable
        expr = self._make_builtin("isBLANK", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": blank("b1")}) is True

    def test_isblank_false(self):
        from rdflib.term import Variable
        expr = self._make_builtin("isBLANK", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": iri("http://x")}) is False

    def test_str(self):
        from rdflib.term import Variable
        expr = self._make_builtin("STR", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": iri("http://example.com/a")})
        assert result.type == LITERAL
        assert result.value == "http://example.com/a"

    def test_lang(self):
        from rdflib.term import Variable
        expr = self._make_builtin("LANG", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("hello", language="en")}
        )
        assert result.value == "en"

    def test_lang_no_tag(self):
        from rdflib.term import Variable
        expr = self._make_builtin("LANG", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result.value == ""

    def test_datatype(self):
        from rdflib.term import Variable
        expr = self._make_builtin("DATATYPE", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("42", datatype=XSD + "integer")}
        )
        assert result.type == IRI
        assert result.iri == XSD + "integer"

    def test_strlen(self):
        from rdflib.term import Variable
        expr = self._make_builtin("STRLEN", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result == 5

    def test_ucase(self):
        from rdflib.term import Variable
        expr = self._make_builtin("UCASE", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result.value == "HELLO"

    def test_lcase(self):
        from rdflib.term import Variable
        expr = self._make_builtin("LCASE", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("HELLO")})
        assert result.value == "hello"

    def test_contains_true(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("CONTAINS",
                                  arg1=Variable("x"), arg2=Literal("ell"))
        assert evaluate_expression(expr, {"x": lit("hello")}) is True

    def test_contains_false(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("CONTAINS",
                                  arg1=Variable("x"), arg2=Literal("xyz"))
        assert evaluate_expression(expr, {"x": lit("hello")}) is False

    def test_strstarts_true(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("STRSTARTS",
                                  arg1=Variable("x"), arg2=Literal("hel"))
        assert evaluate_expression(expr, {"x": lit("hello")}) is True

    def test_strends_true(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("STRENDS",
                                  arg1=Variable("x"), arg2=Literal("llo"))
        assert evaluate_expression(expr, {"x": lit("hello")}) is True

    def test_regex_match(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("REGEX",
                                  text=Variable("x"),
                                  pattern=Literal("^hel"),
                                  flags=None)
        assert evaluate_expression(expr, {"x": lit("hello")}) is True

    def test_regex_case_insensitive(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("REGEX",
                                  text=Variable("x"),
                                  pattern=Literal("HELLO"),
                                  flags=Literal("i"))
        assert evaluate_expression(expr, {"x": lit("hello")}) is True

    def test_regex_no_match(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("REGEX",
                                  text=Variable("x"),
                                  pattern=Literal("^world"),
                                  flags=None)
        assert evaluate_expression(expr, {"x": lit("hello")}) is False


class TestEffectiveBoolean:

    def test_true(self):
        assert _effective_boolean(True) is True

    def test_false(self):
        assert _effective_boolean(False) is False

    def test_none(self):
        assert _effective_boolean(None) is False

    def test_nonzero_int(self):
        assert _effective_boolean(42) is True

    def test_zero_int(self):
        assert _effective_boolean(0) is False

    def test_nonempty_string(self):
        assert _effective_boolean("hello") is True

    def test_empty_string(self):
        assert _effective_boolean("") is False

    def test_iri_term(self):
        assert _effective_boolean(iri("http://x")) is True

    def test_nonempty_literal(self):
        assert _effective_boolean(lit("hello")) is True

    def test_empty_literal(self):
        assert _effective_boolean(lit("")) is False

    def test_boolean_literal_true(self):
        assert _effective_boolean(
            lit("true", datatype=XSD + "boolean")
        ) is True

    def test_boolean_literal_false(self):
        assert _effective_boolean(
            lit("false", datatype=XSD + "boolean")
        ) is False

    def test_numeric_literal_nonzero(self):
        assert _effective_boolean(
            lit("42", datatype=XSD + "integer")
        ) is True

    def test_numeric_literal_zero(self):
        assert _effective_boolean(
            lit("0", datatype=XSD + "integer")
        ) is False


class TestToString:

    def test_none(self):
        assert _to_string(None) == ""

    def test_string(self):
        assert _to_string("hello") == "hello"

    def test_iri_term(self):
        assert _to_string(iri("http://example.com")) == "http://example.com"

    def test_literal_term(self):
        assert _to_string(lit("hello")) == "hello"

    def test_blank_term(self):
        assert _to_string(blank("b1")) == "b1"


class TestToNumeric:

    def test_none(self):
        assert _to_numeric(None) is None

    def test_int(self):
        assert _to_numeric(42) == 42

    def test_float(self):
        assert _to_numeric(3.14) == 3.14

    def test_integer_literal(self):
        assert _to_numeric(lit("42")) == 42

    def test_decimal_literal(self):
        assert _to_numeric(lit("3.14")) == 3.14

    def test_non_numeric_literal(self):
        assert _to_numeric(lit("hello")) is None

    def test_numeric_string(self):
        assert _to_numeric("42") == 42

    def test_non_numeric_string(self):
        assert _to_numeric("abc") is None


class TestComparableValue:

    def test_none(self):
        assert _comparable_value(None) == (0, "")

    def test_int(self):
        assert _comparable_value(42) == (2, 42)

    def test_iri(self):
        assert _comparable_value(iri("http://x")) == (4, "http://x")

    def test_literal(self):
        assert _comparable_value(lit("hello")) == (3, "hello")

    def test_numeric_literal(self):
        assert _comparable_value(lit("42")) == (2, 42)

    def test_ordering(self):
        vals = [lit("b"), lit("a"), lit("c")]
        sorted_vals = sorted(vals, key=_comparable_value)
        assert sorted_vals[0].value == "a"
        assert sorted_vals[1].value == "b"
        assert sorted_vals[2].value == "c"
