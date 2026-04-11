"""
Tests for RDF wire format translators: TermTranslator and TripleTranslator
round-trip encoding for all RDF 1.2 term types (IRI, blank node, typed literal,
language-tagged literal, quoted triple) and named graph quads.
"""

import pytest

from trustgraph.schema import Term, Triple, IRI, BLANK, LITERAL, TRIPLE
from trustgraph.messaging.translators.primitives import (
    TermTranslator, TripleTranslator, SubgraphTranslator,
)


@pytest.fixture
def term_tx():
    return TermTranslator()


@pytest.fixture
def triple_tx():
    return TripleTranslator()


# ---------------------------------------------------------------------------
# TermTranslator — IRI
# ---------------------------------------------------------------------------

class TestTermTranslatorIri:

    def test_iri_decode(self, term_tx):
        data = {"t": "i", "i": "http://example.org/Alice"}
        term = term_tx.decode(data)
        assert term.type == IRI
        assert term.iri == "http://example.org/Alice"

    def test_iri_encode(self, term_tx):
        term = Term(type=IRI, iri="http://example.org/Bob")
        wire = term_tx.encode(term)
        assert wire == {"t": "i", "i": "http://example.org/Bob"}

    def test_iri_round_trip(self, term_tx):
        original = Term(type=IRI, iri="http://example.org/round")
        wire = term_tx.encode(original)
        restored = term_tx.decode(wire)
        assert restored == original


# ---------------------------------------------------------------------------
# TermTranslator — Blank node
# ---------------------------------------------------------------------------

class TestTermTranslatorBlank:

    def test_blank_decode(self, term_tx):
        data = {"t": "b", "d": "_:b42"}
        term = term_tx.decode(data)
        assert term.type == BLANK
        assert term.id == "_:b42"

    def test_blank_encode(self, term_tx):
        term = Term(type=BLANK, id="_:node1")
        wire = term_tx.encode(term)
        assert wire == {"t": "b", "d": "_:node1"}

    def test_blank_round_trip(self, term_tx):
        original = Term(type=BLANK, id="_:x")
        wire = term_tx.encode(original)
        restored = term_tx.decode(wire)
        assert restored == original


# ---------------------------------------------------------------------------
# TermTranslator — Typed literal (XSD)
# ---------------------------------------------------------------------------

class TestTermTranslatorTypedLiteral:

    def test_plain_literal_decode(self, term_tx):
        data = {"t": "l", "v": "hello"}
        term = term_tx.decode(data)
        assert term.type == LITERAL
        assert term.value == "hello"
        assert term.datatype == ""
        assert term.language == ""

    def test_xsd_integer_decode(self, term_tx):
        data = {
            "t": "l", "v": "42",
            "dt": "http://www.w3.org/2001/XMLSchema#integer",
        }
        term = term_tx.decode(data)
        assert term.value == "42"
        assert term.datatype.endswith("#integer")

    def test_typed_literal_encode(self, term_tx):
        term = Term(
            type=LITERAL, value="3.14",
            datatype="http://www.w3.org/2001/XMLSchema#double",
        )
        wire = term_tx.encode(term)
        assert wire["t"] == "l"
        assert wire["v"] == "3.14"
        assert wire["dt"] == "http://www.w3.org/2001/XMLSchema#double"
        assert "ln" not in wire  # No language tag

    def test_typed_literal_round_trip(self, term_tx):
        original = Term(
            type=LITERAL, value="true",
            datatype="http://www.w3.org/2001/XMLSchema#boolean",
        )
        wire = term_tx.encode(original)
        restored = term_tx.decode(wire)
        assert restored == original

    def test_plain_literal_omits_dt_and_ln(self, term_tx):
        term = Term(type=LITERAL, value="x")
        wire = term_tx.encode(term)
        assert "dt" not in wire
        assert "ln" not in wire


# ---------------------------------------------------------------------------
# TermTranslator — Language-tagged literal
# ---------------------------------------------------------------------------

class TestTermTranslatorLangLiteral:

    def test_language_tag_decode(self, term_tx):
        data = {"t": "l", "v": "bonjour", "ln": "fr"}
        term = term_tx.decode(data)
        assert term.value == "bonjour"
        assert term.language == "fr"

    def test_language_tag_encode(self, term_tx):
        term = Term(type=LITERAL, value="colour", language="en-GB")
        wire = term_tx.encode(term)
        assert wire["ln"] == "en-GB"
        assert "dt" not in wire  # No datatype

    def test_language_tag_round_trip(self, term_tx):
        original = Term(type=LITERAL, value="hola", language="es")
        wire = term_tx.encode(original)
        restored = term_tx.decode(wire)
        assert restored == original


# ---------------------------------------------------------------------------
# TermTranslator — Quoted triple (RDF-star)
# ---------------------------------------------------------------------------

class TestTermTranslatorQuotedTriple:

    def test_quoted_triple_decode(self, term_tx):
        data = {
            "t": "t",
            "tr": {
                "s": {"t": "i", "i": "http://example.org/Alice"},
                "p": {"t": "i", "i": "http://xmlns.com/foaf/0.1/knows"},
                "o": {"t": "i", "i": "http://example.org/Bob"},
            },
        }
        term = term_tx.decode(data)
        assert term.type == TRIPLE
        assert term.triple is not None
        assert term.triple.s.iri == "http://example.org/Alice"
        assert term.triple.o.iri == "http://example.org/Bob"

    def test_quoted_triple_encode(self, term_tx):
        inner = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="val"),
        )
        term = Term(type=TRIPLE, triple=inner)
        wire = term_tx.encode(term)
        assert wire["t"] == "t"
        assert "tr" in wire
        assert wire["tr"]["s"]["i"] == "http://example.org/s"
        assert wire["tr"]["o"]["v"] == "val"

    def test_quoted_triple_round_trip(self, term_tx):
        inner = Triple(
            s=Term(type=IRI, iri="http://example.org/A"),
            p=Term(type=IRI, iri="http://example.org/B"),
            o=Term(type=LITERAL, value="C", language="en"),
        )
        original = Term(type=TRIPLE, triple=inner)
        wire = term_tx.encode(original)
        restored = term_tx.decode(wire)
        assert restored.type == TRIPLE
        assert restored.triple.s == original.triple.s
        assert restored.triple.o == original.triple.o

    def test_quoted_triple_none_triple(self, term_tx):
        term = Term(type=TRIPLE, triple=None)
        wire = term_tx.encode(term)
        assert wire == {"t": "t"}
        # And back
        restored = term_tx.decode(wire)
        assert restored.type == TRIPLE
        assert restored.triple is None

    def test_quoted_triple_with_literal_object(self, term_tx):
        data = {
            "t": "t",
            "tr": {
                "s": {"t": "i", "i": "http://example.org/Hope"},
                "p": {"t": "i", "i": "http://www.w3.org/2004/02/skos/core#definition"},
                "o": {"t": "l", "v": "A feeling of expectation"},
            },
        }
        term = term_tx.decode(data)
        assert term.triple.o.type == LITERAL
        assert term.triple.o.value == "A feeling of expectation"


# ---------------------------------------------------------------------------
# TermTranslator — Edge cases
# ---------------------------------------------------------------------------

class TestTermTranslatorEdgeCases:

    def test_unknown_type(self, term_tx):
        data = {"t": "z"}
        term = term_tx.decode(data)
        assert term.type == "z"

    def test_empty_type(self, term_tx):
        data = {}
        term = term_tx.decode(data)
        assert term.type == ""

    def test_missing_iri_field(self, term_tx):
        data = {"t": "i"}
        term = term_tx.decode(data)
        assert term.iri == ""

    def test_missing_literal_fields(self, term_tx):
        data = {"t": "l"}
        term = term_tx.decode(data)
        assert term.value == ""
        assert term.datatype == ""
        assert term.language == ""


# ---------------------------------------------------------------------------
# TripleTranslator
# ---------------------------------------------------------------------------

class TestTripleTranslator:

    def test_triple_decode(self, triple_tx):
        data = {
            "s": {"t": "i", "i": "http://example.org/s"},
            "p": {"t": "i", "i": "http://example.org/p"},
            "o": {"t": "l", "v": "object"},
        }
        triple = triple_tx.decode(data)
        assert triple.s.iri == "http://example.org/s"
        assert triple.o.value == "object"
        assert triple.g is None

    def test_triple_encode(self, triple_tx):
        triple = Triple(
            s=Term(type=IRI, iri="http://example.org/A"),
            p=Term(type=IRI, iri="http://example.org/B"),
            o=Term(type=LITERAL, value="C"),
        )
        wire = triple_tx.encode(triple)
        assert wire["s"]["t"] == "i"
        assert wire["o"]["v"] == "C"
        assert "g" not in wire

    def test_quad_with_named_graph(self, triple_tx):
        data = {
            "s": {"t": "i", "i": "http://example.org/s"},
            "p": {"t": "i", "i": "http://example.org/p"},
            "o": {"t": "l", "v": "val"},
            "g": "urn:graph:source",
        }
        quad = triple_tx.decode(data)
        assert quad.g == "urn:graph:source"

    def test_quad_encode_includes_graph(self, triple_tx):
        quad = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="v"),
            g="urn:graph:retrieval",
        )
        wire = triple_tx.encode(quad)
        assert wire["g"] == "urn:graph:retrieval"

    def test_quad_round_trip(self, triple_tx):
        original = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="v"),
            g="urn:graph:source",
        )
        wire = triple_tx.encode(original)
        restored = triple_tx.decode(wire)
        assert restored == original

    def test_none_graph_omitted_from_wire(self, triple_tx):
        triple = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="v"),
            g=None,
        )
        wire = triple_tx.encode(triple)
        assert "g" not in wire

    def test_missing_terms_handled(self, triple_tx):
        data = {}
        triple = triple_tx.decode(data)
        assert triple.s is None
        assert triple.p is None
        assert triple.o is None


# ---------------------------------------------------------------------------
# SubgraphTranslator
# ---------------------------------------------------------------------------

class TestSubgraphTranslator:

    def test_subgraph_round_trip(self):
        tx = SubgraphTranslator()
        triples = [
            Triple(
                s=Term(type=IRI, iri="http://example.org/A"),
                p=Term(type=IRI, iri="http://example.org/rel"),
                o=Term(type=LITERAL, value="v1"),
            ),
            Triple(
                s=Term(type=IRI, iri="http://example.org/B"),
                p=Term(type=IRI, iri="http://example.org/rel"),
                o=Term(type=IRI, iri="http://example.org/C"),
                g="urn:graph:source",
            ),
        ]
        wire_list = tx.encode(triples)
        assert len(wire_list) == 2
        assert wire_list[1]["g"] == "urn:graph:source"

        restored = tx.decode(wire_list)
        assert len(restored) == 2
        assert restored[0] == triples[0]
        assert restored[1] == triples[1]

    def test_empty_subgraph(self):
        tx = SubgraphTranslator()
        assert tx.decode([]) == []
        assert tx.encode([]) == []
