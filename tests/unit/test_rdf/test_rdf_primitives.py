"""
Tests for RDF 1.2 type system primitives: Term dataclass (IRI, blank node,
typed literal, language-tagged literal, quoted triple), Triple/Quad dataclass
with named graph support, and the knowledge/defs helper types.
"""

import pytest

from trustgraph.schema import Term, Triple, IRI, BLANK, LITERAL, TRIPLE


# ---------------------------------------------------------------------------
# Type constants
# ---------------------------------------------------------------------------

class TestTypeConstants:

    def test_iri_constant(self):
        assert IRI == "i"

    def test_blank_constant(self):
        assert BLANK == "b"

    def test_literal_constant(self):
        assert LITERAL == "l"

    def test_triple_constant(self):
        assert TRIPLE == "t"

    def test_constants_are_distinct(self):
        vals = {IRI, BLANK, LITERAL, TRIPLE}
        assert len(vals) == 4


# ---------------------------------------------------------------------------
# IRI terms
# ---------------------------------------------------------------------------

class TestIriTerm:

    def test_create_iri(self):
        t = Term(type=IRI, iri="http://example.org/Alice")
        assert t.type == IRI
        assert t.iri == "http://example.org/Alice"

    def test_iri_defaults_empty(self):
        t = Term(type=IRI)
        assert t.iri == ""

    def test_iri_with_fragment(self):
        t = Term(type=IRI, iri="http://example.org/ontology#Person")
        assert "#Person" in t.iri

    def test_iri_with_unicode(self):
        t = Term(type=IRI, iri="http://example.org/概念")
        assert "概念" in t.iri

    def test_iri_other_fields_default(self):
        t = Term(type=IRI, iri="http://example.org/x")
        assert t.id == ""
        assert t.value == ""
        assert t.datatype == ""
        assert t.language == ""
        assert t.triple is None


# ---------------------------------------------------------------------------
# Blank node terms
# ---------------------------------------------------------------------------

class TestBlankNodeTerm:

    def test_create_blank_node(self):
        t = Term(type=BLANK, id="_:b0")
        assert t.type == BLANK
        assert t.id == "_:b0"

    def test_blank_node_defaults_empty(self):
        t = Term(type=BLANK)
        assert t.id == ""

    def test_blank_node_arbitrary_id(self):
        t = Term(type=BLANK, id="node-abc-123")
        assert t.id == "node-abc-123"


# ---------------------------------------------------------------------------
# Typed literals (XSD datatypes)
# ---------------------------------------------------------------------------

class TestTypedLiteral:

    def test_plain_literal(self):
        t = Term(type=LITERAL, value="hello")
        assert t.type == LITERAL
        assert t.value == "hello"
        assert t.datatype == ""
        assert t.language == ""

    def test_xsd_integer(self):
        t = Term(
            type=LITERAL, value="42",
            datatype="http://www.w3.org/2001/XMLSchema#integer",
        )
        assert t.value == "42"
        assert "integer" in t.datatype

    def test_xsd_boolean(self):
        t = Term(
            type=LITERAL, value="true",
            datatype="http://www.w3.org/2001/XMLSchema#boolean",
        )
        assert t.datatype.endswith("#boolean")

    def test_xsd_date(self):
        t = Term(
            type=LITERAL, value="2026-03-13",
            datatype="http://www.w3.org/2001/XMLSchema#date",
        )
        assert t.value == "2026-03-13"
        assert t.datatype.endswith("#date")

    def test_xsd_double(self):
        t = Term(
            type=LITERAL, value="3.14",
            datatype="http://www.w3.org/2001/XMLSchema#double",
        )
        assert t.datatype.endswith("#double")

    def test_empty_value_literal(self):
        t = Term(type=LITERAL, value="")
        assert t.value == ""


# ---------------------------------------------------------------------------
# Language-tagged literals
# ---------------------------------------------------------------------------

class TestLanguageTaggedLiteral:

    def test_english_tag(self):
        t = Term(type=LITERAL, value="hello", language="en")
        assert t.language == "en"
        assert t.datatype == ""

    def test_french_tag(self):
        t = Term(type=LITERAL, value="bonjour", language="fr")
        assert t.language == "fr"

    def test_bcp47_subtag(self):
        t = Term(type=LITERAL, value="colour", language="en-GB")
        assert t.language == "en-GB"

    def test_language_and_datatype_mutually_exclusive(self):
        """Both can be set on the dataclass, but semantically only one should be used."""
        t = Term(type=LITERAL, value="x", language="en",
                 datatype="http://www.w3.org/2001/XMLSchema#string")
        # Dataclass allows both — translators should respect mutual exclusivity
        assert t.language == "en"
        assert t.datatype != ""


# ---------------------------------------------------------------------------
# Quoted triples (RDF-star)
# ---------------------------------------------------------------------------

class TestQuotedTriple:

    def test_term_with_nested_triple(self):
        inner = Triple(
            s=Term(type=IRI, iri="http://example.org/Alice"),
            p=Term(type=IRI, iri="http://xmlns.com/foaf/0.1/knows"),
            o=Term(type=IRI, iri="http://example.org/Bob"),
        )
        qt = Term(type=TRIPLE, triple=inner)
        assert qt.type == TRIPLE
        assert qt.triple is inner
        assert qt.triple.s.iri == "http://example.org/Alice"

    def test_quoted_triple_as_object(self):
        """A triple whose object is a quoted triple (RDF-star)."""
        inner = Triple(
            s=Term(type=IRI, iri="http://example.org/Hope"),
            p=Term(type=IRI, iri="http://www.w3.org/2004/02/skos/core#definition"),
            o=Term(type=LITERAL, value="A feeling of expectation"),
        )
        outer = Triple(
            s=Term(type=IRI, iri="urn:subgraph:123"),
            p=Term(type=IRI, iri="http://trustgraph.ai/tg/contains"),
            o=Term(type=TRIPLE, triple=inner),
        )
        assert outer.o.type == TRIPLE
        assert outer.o.triple.o.value == "A feeling of expectation"

    def test_quoted_triple_none(self):
        t = Term(type=TRIPLE, triple=None)
        assert t.triple is None


# ---------------------------------------------------------------------------
# Triple / Quad (named graph)
# ---------------------------------------------------------------------------

class TestTripleQuad:

    def test_default_graph_is_none(self):
        t = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="val"),
        )
        assert t.g is None

    def test_named_graph(self):
        t = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="val"),
            g="urn:graph:source",
        )
        assert t.g == "urn:graph:source"

    def test_empty_string_graph(self):
        t = Triple(g="")
        assert t.g == ""

    def test_triple_with_all_none_terms(self):
        t = Triple()
        assert t.s is None
        assert t.p is None
        assert t.o is None
        assert t.g is None

    def test_triple_equality(self):
        """Dataclass equality based on field values."""
        t1 = Triple(
            s=Term(type=IRI, iri="http://example.org/A"),
            p=Term(type=IRI, iri="http://example.org/B"),
            o=Term(type=LITERAL, value="C"),
        )
        t2 = Triple(
            s=Term(type=IRI, iri="http://example.org/A"),
            p=Term(type=IRI, iri="http://example.org/B"),
            o=Term(type=LITERAL, value="C"),
        )
        assert t1 == t2


# ---------------------------------------------------------------------------
# knowledge/defs helper types
# ---------------------------------------------------------------------------

class TestKnowledgeDefs:

    def test_uri_type(self):
        from trustgraph.knowledge.defs import Uri
        u = Uri("http://example.org/x")
        assert u.is_uri() is True
        assert u.is_literal() is False
        assert u.is_triple() is False
        assert str(u) == "http://example.org/x"

    def test_literal_type(self):
        from trustgraph.knowledge.defs import Literal
        l = Literal("hello world")
        assert l.is_uri() is False
        assert l.is_literal() is True
        assert l.is_triple() is False
        assert str(l) == "hello world"

    def test_quoted_triple_type(self):
        from trustgraph.knowledge.defs import QuotedTriple, Uri, Literal
        qt = QuotedTriple(
            s=Uri("http://example.org/s"),
            p=Uri("http://example.org/p"),
            o=Literal("val"),
        )
        assert qt.is_uri() is False
        assert qt.is_literal() is False
        assert qt.is_triple() is True
        assert qt.s == "http://example.org/s"
        assert qt.o == "val"

    def test_quoted_triple_repr(self):
        from trustgraph.knowledge.defs import QuotedTriple, Uri, Literal
        qt = QuotedTriple(
            s=Uri("http://example.org/A"),
            p=Uri("http://example.org/B"),
            o=Literal("C"),
        )
        r = repr(qt)
        assert "<<" in r
        assert ">>" in r
        assert "http://example.org/A" in r

    def test_quoted_triple_nested(self):
        """QuotedTriple can contain another QuotedTriple as object."""
        from trustgraph.knowledge.defs import QuotedTriple, Uri, Literal
        inner = QuotedTriple(
            s=Uri("http://example.org/s"),
            p=Uri("http://example.org/p"),
            o=Literal("v"),
        )
        outer = QuotedTriple(
            s=Uri("http://example.org/s2"),
            p=Uri("http://example.org/p2"),
            o=inner,
        )
        assert outer.o.is_triple() is True
