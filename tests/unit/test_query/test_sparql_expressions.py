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

    def test_substr_three_args(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("SUBSTR",
                                  arg=Variable("x"),
                                  start=Literal(1),
                                  length=Literal(4))
        result = evaluate_expression(expr, {"x": lit("2024-03-15")})
        assert result.type == LITERAL
        assert result.value == "2024"

    def test_substr_two_args(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("SUBSTR",
                                  arg=Variable("x"),
                                  start=Literal(6),
                                  length=None)
        result = evaluate_expression(expr, {"x": lit("2024-03-15")})
        assert result.type == LITERAL
        assert result.value == "03-15"

    def test_substr_middle(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("SUBSTR",
                                  arg=Variable("x"),
                                  start=Literal(6),
                                  length=Literal(2))
        result = evaluate_expression(expr, {"x": lit("2024-03-15")})
        assert result.type == LITERAL
        assert result.value == "03"

    def test_substr_null_start(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("SUBSTR",
                                  arg=Variable("x"),
                                  start=Variable("missing"),
                                  length=None)
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result is None

    def test_year(self):
        from rdflib.term import Variable
        expr = self._make_builtin("YEAR", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15", datatype=XSD + "date")}
        )
        assert result == 2024

    def test_month(self):
        from rdflib.term import Variable
        expr = self._make_builtin("MONTH", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15", datatype=XSD + "date")}
        )
        assert result == 3

    def test_day(self):
        from rdflib.term import Variable
        expr = self._make_builtin("DAY", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15", datatype=XSD + "date")}
        )
        assert result == 15

    def test_hours(self):
        from rdflib.term import Variable
        expr = self._make_builtin("HOURS", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15T10:30:45", datatype=XSD + "dateTime")}
        )
        assert result == 10

    def test_minutes(self):
        from rdflib.term import Variable
        expr = self._make_builtin("MINUTES", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15T10:30:45", datatype=XSD + "dateTime")}
        )
        assert result == 30

    def test_seconds(self):
        from rdflib.term import Variable
        expr = self._make_builtin("SECONDS", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15T10:30:45", datatype=XSD + "dateTime")}
        )
        assert result == 45

    def test_year_from_datetime(self):
        from rdflib.term import Variable
        expr = self._make_builtin("YEAR", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15T10:30:45", datatype=XSD + "dateTime")}
        )
        assert result == 2024

    def test_hours_from_date_returns_zero(self):
        from rdflib.term import Variable
        expr = self._make_builtin("HOURS", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15", datatype=XSD + "date")}
        )
        assert result == 0

    def test_year_invalid_date(self):
        from rdflib.term import Variable
        expr = self._make_builtin("YEAR", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("not-a-date")}
        )
        assert result is None

    def test_floor(self):
        from rdflib.term import Variable
        expr = self._make_builtin("FLOOR", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("3.7")}) == 3

    def test_floor_negative(self):
        from rdflib.term import Variable
        expr = self._make_builtin("FLOOR", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("-2.3")}) == -3

    def test_floor_none(self):
        from rdflib.term import Variable
        expr = self._make_builtin("FLOOR", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("abc")}) is None

    def test_ceil(self):
        from rdflib.term import Variable
        expr = self._make_builtin("CEIL", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("3.2")}) == 4

    def test_ceil_negative(self):
        from rdflib.term import Variable
        expr = self._make_builtin("CEIL", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("-2.7")}) == -2

    def test_abs_positive(self):
        from rdflib.term import Variable
        expr = self._make_builtin("ABS", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("42")}) == 42

    def test_abs_negative(self):
        from rdflib.term import Variable
        expr = self._make_builtin("ABS", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("-42")}) == 42

    def test_abs_none(self):
        from rdflib.term import Variable
        expr = self._make_builtin("ABS", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("abc")}) is None

    def test_replace_simple(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("REPLACE",
                                  arg=Variable("x"),
                                  pattern=Literal(" BC"),
                                  replacement=Literal(""),
                                  flags=None)
        result = evaluate_expression(expr, {"x": lit("500 BC")})
        assert result.type == LITERAL
        assert result.value == "500"

    def test_replace_regex(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("REPLACE",
                                  arg=Variable("x"),
                                  pattern=Literal("[0-9]+"),
                                  replacement=Literal("X"),
                                  flags=None)
        result = evaluate_expression(expr, {"x": lit("abc123def456")})
        assert result.value == "abcXdefX"

    def test_replace_case_insensitive(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("REPLACE",
                                  arg=Variable("x"),
                                  pattern=Literal("hello"),
                                  replacement=Literal("world"),
                                  flags=Literal("i"))
        result = evaluate_expression(expr, {"x": lit("HELLO there")})
        assert result.value == "world there"

    def test_round_up(self):
        from rdflib.term import Variable
        expr = self._make_builtin("ROUND", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("3.7")}) == 4

    def test_round_down(self):
        from rdflib.term import Variable
        expr = self._make_builtin("ROUND", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("3.2")}) == 3

    def test_round_none(self):
        from rdflib.term import Variable
        expr = self._make_builtin("ROUND", arg=Variable("x"))
        assert evaluate_expression(expr, {"x": lit("abc")}) is None

    def test_strbefore(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("STRBEFORE",
                                  arg1=Variable("x"), arg2=Literal("-"))
        result = evaluate_expression(expr, {"x": lit("2024-03-15")})
        assert result.value == "2024"

    def test_strbefore_not_found(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("STRBEFORE",
                                  arg1=Variable("x"), arg2=Literal("/"))
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result.value == ""

    def test_strafter(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("STRAFTER",
                                  arg1=Variable("x"), arg2=Literal("-"))
        result = evaluate_expression(expr, {"x": lit("2024-03-15")})
        assert result.value == "03-15"

    def test_strafter_not_found(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("STRAFTER",
                                  arg1=Variable("x"), arg2=Literal("/"))
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result.value == ""

    def test_encode_for_uri(self):
        from rdflib.term import Variable
        expr = self._make_builtin("ENCODE_FOR_URI", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("hello world")})
        assert result.value == "hello%20world"

    def test_encode_for_uri_special_chars(self):
        from rdflib.term import Variable
        expr = self._make_builtin("ENCODE_FOR_URI", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("a/b?c=d&e")})
        assert result.value == "a%2Fb%3Fc%3Dd%26e"

    def test_langmatches_basic(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("LANGMATCHES",
                                  arg1=Literal("en"), arg2=Literal("en"))
        assert evaluate_expression(expr, {}) is True

    def test_langmatches_subtag(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("LANGMATCHES",
                                  arg1=Literal("en-US"), arg2=Literal("en"))
        assert evaluate_expression(expr, {}) is True

    def test_langmatches_wildcard(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("LANGMATCHES",
                                  arg1=Literal("fr"), arg2=Literal("*"))
        assert evaluate_expression(expr, {}) is True

    def test_langmatches_wildcard_empty(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("LANGMATCHES",
                                  arg1=Literal(""), arg2=Literal("*"))
        assert evaluate_expression(expr, {}) is False

    def test_langmatches_no_match(self):
        from rdflib.term import Variable
        from rdflib import Literal
        expr = self._make_builtin("LANGMATCHES",
                                  arg1=Literal("fr"), arg2=Literal("en"))
        assert evaluate_expression(expr, {}) is False

    def test_iri_constructor(self):
        from rdflib.term import Variable
        expr = self._make_builtin("IRI", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("http://example.com/test")}
        )
        assert result.type == IRI
        assert result.iri == "http://example.com/test"

    def test_uri_constructor(self):
        from rdflib.term import Variable
        expr = self._make_builtin("URI", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("http://example.com/test")}
        )
        assert result.type == IRI
        assert result.iri == "http://example.com/test"

    def test_bnode_no_arg(self):
        expr = self._make_builtin("BNODE")
        result = evaluate_expression(expr, {})
        assert result.type == BLANK
        assert len(result.id) > 0

    def test_bnode_with_label(self):
        from rdflib import Literal
        expr = self._make_builtin("BNODE", arg=Literal("mynode"))
        result = evaluate_expression(expr, {})
        assert result.type == BLANK
        assert result.id == "mynode"

    def test_now(self):
        import re as re_mod
        expr = self._make_builtin("NOW")
        result = evaluate_expression(expr, {})
        assert result.type == LITERAL
        assert result.datatype == XSD + "dateTime"
        assert re_mod.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", result.value)

    def test_tz_with_utc(self):
        from rdflib.term import Variable
        expr = self._make_builtin("TZ", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15T10:30:45+0000",
                            datatype=XSD + "dateTime")}
        )
        assert result.type == LITERAL
        assert result.value == "+00:00"

    def test_tz_no_timezone(self):
        from rdflib.term import Variable
        expr = self._make_builtin("TZ", arg=Variable("x"))
        result = evaluate_expression(
            expr, {"x": lit("2024-03-15T10:30:45",
                            datatype=XSD + "dateTime")}
        )
        assert result.value == ""

    def test_rand(self):
        expr = self._make_builtin("RAND")
        result = evaluate_expression(expr, {})
        assert isinstance(result, float)
        assert 0.0 <= result < 1.0

    def test_uuid(self):
        import re as re_mod
        expr = self._make_builtin("UUID")
        result = evaluate_expression(expr, {})
        assert result.type == IRI
        assert result.iri.startswith("urn:uuid:")
        uuid_part = result.iri[len("urn:uuid:"):]
        assert re_mod.match(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            uuid_part
        )

    def test_struuid(self):
        import re as re_mod
        expr = self._make_builtin("STRUUID")
        result = evaluate_expression(expr, {})
        assert result.type == LITERAL
        assert re_mod.match(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            result.value
        )

    def test_md5(self):
        from rdflib.term import Variable
        expr = self._make_builtin("MD5", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result.type == LITERAL
        assert result.value == "5d41402abc4b2a76b9719d911017c592"

    def test_sha1(self):
        from rdflib.term import Variable
        expr = self._make_builtin("SHA1", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result.type == LITERAL
        assert result.value == "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"

    def test_sha256(self):
        from rdflib.term import Variable
        expr = self._make_builtin("SHA256", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result.type == LITERAL
        assert result.value == (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e"
            "1b161e5c1fa7425e73043362938b9824"
        )

    def test_sha512(self):
        from rdflib.term import Variable
        expr = self._make_builtin("SHA512", arg=Variable("x"))
        result = evaluate_expression(expr, {"x": lit("hello")})
        assert result.type == LITERAL
        assert len(result.value) == 128

    def test_exists_with_callback(self):
        from rdflib.plugins.sparql.parserutils import CompValue
        graph = CompValue("BGP")
        expr = self._make_builtin("EXISTS", graph=graph)
        cb = lambda g, s: True
        result = evaluate_expression(expr, {}, exists_cb=cb)
        assert result is True

    def test_exists_callback_false(self):
        from rdflib.plugins.sparql.parserutils import CompValue
        graph = CompValue("BGP")
        expr = self._make_builtin("EXISTS", graph=graph)
        cb = lambda g, s: False
        result = evaluate_expression(expr, {}, exists_cb=cb)
        assert result is False

    def test_notexists_with_callback(self):
        from rdflib.plugins.sparql.parserutils import CompValue
        graph = CompValue("BGP")
        expr = self._make_builtin("NOTEXISTS", graph=graph)
        cb = lambda g, s: True
        result = evaluate_expression(expr, {}, exists_cb=cb)
        assert result is False

    def test_notexists_callback_false(self):
        from rdflib.plugins.sparql.parserutils import CompValue
        graph = CompValue("BGP")
        expr = self._make_builtin("NOTEXISTS", graph=graph)
        cb = lambda g, s: False
        result = evaluate_expression(expr, {}, exists_cb=cb)
        assert result is True


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
