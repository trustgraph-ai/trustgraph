"""
Tests for the SPARQL parser module.
"""

import pytest
from trustgraph.query.sparql.parser import (
    parse_sparql, ParseError, rdflib_term_to_term, term_to_rdflib,
)
from trustgraph.schema import Term, IRI, LITERAL, BLANK


class TestParseSparql:
    """Tests for parse_sparql function."""

    def test_select_query_type(self):
        parsed = parse_sparql("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
        assert parsed.query_type == "select"

    def test_select_variables(self):
        parsed = parse_sparql("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
        assert parsed.variables == ["s", "p", "o"]

    def test_select_subset_variables(self):
        parsed = parse_sparql("SELECT ?s ?o WHERE { ?s ?p ?o }")
        assert parsed.variables == ["s", "o"]

    def test_ask_query_type(self):
        parsed = parse_sparql(
            "ASK { <http://example.com/a> ?p ?o }"
        )
        assert parsed.query_type == "ask"

    def test_ask_no_variables(self):
        parsed = parse_sparql(
            "ASK { <http://example.com/a> ?p ?o }"
        )
        assert parsed.variables == []

    def test_construct_query_type(self):
        parsed = parse_sparql(
            "CONSTRUCT { ?s <http://example.com/knows> ?o } "
            "WHERE { ?s <http://example.com/friendOf> ?o }"
        )
        assert parsed.query_type == "construct"

    def test_describe_query_type(self):
        parsed = parse_sparql(
            "DESCRIBE <http://example.com/alice>"
        )
        assert parsed.query_type == "describe"

    def test_select_with_limit(self):
        parsed = parse_sparql(
            "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10"
        )
        assert parsed.query_type == "select"
        assert parsed.variables == ["s"]

    def test_select_with_distinct(self):
        parsed = parse_sparql(
            "SELECT DISTINCT ?s WHERE { ?s ?p ?o }"
        )
        assert parsed.query_type == "select"
        assert parsed.variables == ["s"]

    def test_select_with_filter(self):
        parsed = parse_sparql(
            'SELECT ?s ?label WHERE { '
            '  ?s <http://www.w3.org/2000/01/rdf-schema#label> ?label . '
            '  FILTER(CONTAINS(STR(?label), "test")) '
            '}'
        )
        assert parsed.query_type == "select"
        assert parsed.variables == ["s", "label"]

    def test_select_with_optional(self):
        parsed = parse_sparql(
            "SELECT ?s ?p ?o ?label WHERE { "
            "  ?s ?p ?o . "
            "  OPTIONAL { ?s <http://www.w3.org/2000/01/rdf-schema#label> ?label } "
            "}"
        )
        assert parsed.query_type == "select"
        assert set(parsed.variables) == {"s", "p", "o", "label"}

    def test_select_with_union(self):
        parsed = parse_sparql(
            "SELECT ?s ?label WHERE { "
            "  { ?s <http://example.com/name> ?label } "
            "  UNION "
            "  { ?s <http://www.w3.org/2000/01/rdf-schema#label> ?label } "
            "}"
        )
        assert parsed.query_type == "select"

    def test_select_with_order_by(self):
        parsed = parse_sparql(
            "SELECT ?s ?label WHERE { ?s <http://www.w3.org/2000/01/rdf-schema#label> ?label } "
            "ORDER BY ?label"
        )
        assert parsed.query_type == "select"

    def test_select_with_group_by(self):
        parsed = parse_sparql(
            "SELECT ?p (COUNT(?o) AS ?count) WHERE { ?s ?p ?o } "
            "GROUP BY ?p ORDER BY DESC(?count)"
        )
        assert parsed.query_type == "select"

    def test_select_with_prefixes(self):
        parsed = parse_sparql(
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
            "SELECT ?s ?label WHERE { ?s rdfs:label ?label }"
        )
        assert parsed.query_type == "select"
        assert parsed.variables == ["s", "label"]

    def test_algebra_not_none(self):
        parsed = parse_sparql("SELECT ?s WHERE { ?s ?p ?o }")
        assert parsed.algebra is not None

    def test_parse_error_invalid_sparql(self):
        with pytest.raises(ParseError):
            parse_sparql("NOT VALID SPARQL AT ALL")

    def test_parse_error_incomplete_query(self):
        with pytest.raises(ParseError):
            parse_sparql("SELECT ?s WHERE {")

    def test_parse_error_message(self):
        with pytest.raises(ParseError, match="SPARQL parse error"):
            parse_sparql("GIBBERISH")


class TestRdflibTermToTerm:
    """Tests for rdflib-to-Term conversion."""

    def test_uriref_to_term(self):
        from rdflib import URIRef
        term = rdflib_term_to_term(URIRef("http://example.com/alice"))
        assert term.type == IRI
        assert term.iri == "http://example.com/alice"

    def test_literal_to_term(self):
        from rdflib import Literal
        term = rdflib_term_to_term(Literal("hello"))
        assert term.type == LITERAL
        assert term.value == "hello"

    def test_typed_literal_to_term(self):
        from rdflib import Literal, URIRef
        term = rdflib_term_to_term(
            Literal("42", datatype=URIRef("http://www.w3.org/2001/XMLSchema#integer"))
        )
        assert term.type == LITERAL
        assert term.value == "42"
        assert term.datatype == "http://www.w3.org/2001/XMLSchema#integer"

    def test_lang_literal_to_term(self):
        from rdflib import Literal
        term = rdflib_term_to_term(Literal("hello", lang="en"))
        assert term.type == LITERAL
        assert term.value == "hello"
        assert term.language == "en"

    def test_bnode_to_term(self):
        from rdflib import BNode
        term = rdflib_term_to_term(BNode("b1"))
        assert term.type == BLANK
        assert term.id == "b1"


class TestTermToRdflib:
    """Tests for Term-to-rdflib conversion."""

    def test_iri_term_to_uriref(self):
        from rdflib import URIRef
        result = term_to_rdflib(Term(type=IRI, iri="http://example.com/x"))
        assert isinstance(result, URIRef)
        assert str(result) == "http://example.com/x"

    def test_literal_term_to_literal(self):
        from rdflib import Literal
        result = term_to_rdflib(Term(type=LITERAL, value="hello"))
        assert isinstance(result, Literal)
        assert str(result) == "hello"

    def test_typed_literal_roundtrip(self):
        from rdflib import URIRef
        original = Term(
            type=LITERAL, value="42",
            datatype="http://www.w3.org/2001/XMLSchema#integer"
        )
        rdflib_term = term_to_rdflib(original)
        assert rdflib_term.datatype == URIRef("http://www.w3.org/2001/XMLSchema#integer")

    def test_lang_literal_roundtrip(self):
        original = Term(type=LITERAL, value="bonjour", language="fr")
        rdflib_term = term_to_rdflib(original)
        assert rdflib_term.language == "fr"

    def test_blank_term_to_bnode(self):
        from rdflib import BNode
        result = term_to_rdflib(Term(type=BLANK, id="b1"))
        assert isinstance(result, BNode)
