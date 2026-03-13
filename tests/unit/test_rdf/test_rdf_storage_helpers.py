"""
Tests for RDF storage helper functions used by the Cassandra triple writer:
serialize_triple, get_term_value, get_term_otype, get_term_dtype, get_term_lang.
"""

import json
import pytest

from trustgraph.schema import Term, Triple, IRI, BLANK, LITERAL, TRIPLE
from trustgraph.storage.triples.cassandra.write import (
    serialize_triple,
    get_term_value,
    get_term_otype,
    get_term_dtype,
    get_term_lang,
)


# ---------------------------------------------------------------------------
# get_term_otype — maps Term.type to storage object type code
# ---------------------------------------------------------------------------

class TestGetTermOtype:

    def test_iri_maps_to_u(self):
        assert get_term_otype(Term(type=IRI, iri="http://x")) == "u"

    def test_blank_maps_to_u(self):
        assert get_term_otype(Term(type=BLANK, id="_:b0")) == "u"

    def test_literal_maps_to_l(self):
        assert get_term_otype(Term(type=LITERAL, value="x")) == "l"

    def test_triple_maps_to_t(self):
        assert get_term_otype(Term(type=TRIPLE)) == "t"

    def test_none_defaults_to_u(self):
        assert get_term_otype(None) == "u"

    def test_unknown_type_defaults_to_u(self):
        assert get_term_otype(Term(type="z")) == "u"


# ---------------------------------------------------------------------------
# get_term_dtype — extracts XSD datatype from literals
# ---------------------------------------------------------------------------

class TestGetTermDtype:

    def test_literal_with_datatype(self):
        t = Term(type=LITERAL, value="42",
                 datatype="http://www.w3.org/2001/XMLSchema#integer")
        assert get_term_dtype(t) == "http://www.w3.org/2001/XMLSchema#integer"

    def test_literal_without_datatype(self):
        t = Term(type=LITERAL, value="hello")
        assert get_term_dtype(t) == ""

    def test_iri_returns_empty(self):
        assert get_term_dtype(Term(type=IRI, iri="http://x")) == ""

    def test_none_returns_empty(self):
        assert get_term_dtype(None) == ""


# ---------------------------------------------------------------------------
# get_term_lang — extracts language tag from literals
# ---------------------------------------------------------------------------

class TestGetTermLang:

    def test_literal_with_language(self):
        t = Term(type=LITERAL, value="bonjour", language="fr")
        assert get_term_lang(t) == "fr"

    def test_literal_without_language(self):
        t = Term(type=LITERAL, value="hello")
        assert get_term_lang(t) == ""

    def test_iri_returns_empty(self):
        assert get_term_lang(Term(type=IRI, iri="http://x")) == ""

    def test_none_returns_empty(self):
        assert get_term_lang(None) == ""

    def test_bcp47_subtag_preserved(self):
        t = Term(type=LITERAL, value="colour", language="en-GB")
        assert get_term_lang(t) == "en-GB"


# ---------------------------------------------------------------------------
# get_term_value — extracts string value from any Term
# ---------------------------------------------------------------------------

class TestGetTermValue:

    def test_iri_returns_iri(self):
        t = Term(type=IRI, iri="http://example.org/Alice")
        assert get_term_value(t) == "http://example.org/Alice"

    def test_literal_returns_value(self):
        t = Term(type=LITERAL, value="hello")
        assert get_term_value(t) == "hello"

    def test_blank_returns_id(self):
        t = Term(type=BLANK, id="_:b0")
        assert get_term_value(t) == "_:b0"

    def test_none_returns_none(self):
        assert get_term_value(None) is None

    def test_triple_returns_serialized_json(self):
        inner = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="val"),
        )
        t = Term(type=TRIPLE, triple=inner)
        result = get_term_value(t)
        parsed = json.loads(result)
        assert parsed["s"]["type"] == "i"
        assert parsed["s"]["iri"] == "http://example.org/s"
        assert parsed["o"]["value"] == "val"


# ---------------------------------------------------------------------------
# serialize_triple — full Triple → JSON serialization
# ---------------------------------------------------------------------------

class TestSerializeTriple:

    def test_serialize_iri_triple(self):
        t = Triple(
            s=Term(type=IRI, iri="http://example.org/A"),
            p=Term(type=IRI, iri="http://example.org/rel"),
            o=Term(type=IRI, iri="http://example.org/B"),
        )
        result = json.loads(serialize_triple(t))
        assert result["s"]["type"] == "i"
        assert result["s"]["iri"] == "http://example.org/A"
        assert result["p"]["iri"] == "http://example.org/rel"
        assert result["o"]["type"] == "i"

    def test_serialize_literal_object(self):
        t = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="hello"),
        )
        result = json.loads(serialize_triple(t))
        assert result["o"]["type"] == "l"
        assert result["o"]["value"] == "hello"

    def test_serialize_typed_literal(self):
        t = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="42",
                   datatype="http://www.w3.org/2001/XMLSchema#integer"),
        )
        result = json.loads(serialize_triple(t))
        assert result["o"]["datatype"] == "http://www.w3.org/2001/XMLSchema#integer"

    def test_serialize_language_tagged_literal(self):
        t = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="bonjour", language="fr"),
        )
        result = json.loads(serialize_triple(t))
        assert result["o"]["language"] == "fr"

    def test_serialize_blank_node(self):
        t = Triple(
            s=Term(type=BLANK, id="_:b0"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="v"),
        )
        result = json.loads(serialize_triple(t))
        assert result["s"]["type"] == "b"
        assert result["s"]["id"] == "_:b0"

    def test_serialize_nested_quoted_triple(self):
        inner = Triple(
            s=Term(type=IRI, iri="http://example.org/inner-s"),
            p=Term(type=IRI, iri="http://example.org/inner-p"),
            o=Term(type=LITERAL, value="inner-val"),
        )
        outer = Triple(
            s=Term(type=IRI, iri="http://example.org/outer-s"),
            p=Term(type=IRI, iri="http://example.org/outer-p"),
            o=Term(type=TRIPLE, triple=inner),
        )
        result = json.loads(serialize_triple(outer))
        nested = json.loads(result["o"]["triple"])
        assert nested["s"]["iri"] == "http://example.org/inner-s"
        assert nested["o"]["value"] == "inner-val"

    def test_serialize_none_returns_none(self):
        assert serialize_triple(None) is None

    def test_serialize_none_terms(self):
        t = Triple(s=None, p=None, o=None)
        result = json.loads(serialize_triple(t))
        assert result["s"] is None
        assert result["p"] is None
        assert result["o"] is None

    def test_serialize_plain_literal_omits_datatype_and_language(self):
        t = Triple(
            s=Term(type=IRI, iri="http://example.org/s"),
            p=Term(type=IRI, iri="http://example.org/p"),
            o=Term(type=LITERAL, value="plain"),
        )
        result = json.loads(serialize_triple(t))
        assert "datatype" not in result["o"]
        assert "language" not in result["o"]
