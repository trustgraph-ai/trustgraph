"""
Round-trip tests for the streaming N-Quads serializer: wire-format triples
are serialized line-by-line, then parsed back with rdflib's nquads parser
and compared term-for-term — proving the output is valid N-Quads and the
encoding (escaping, datatypes, language tags, unicode) is lossless.
"""

import io

import rdflib

from trustgraph.cli.nquads import serialize_nquads, parse_nquads, triple_to_nquad, encode_term

from tests.unit.test_cli.conftest import iri, lit

GRAPH = "urn:trustgraph:collection:default"


def roundtrip(batches):
    """Serialize then parse back; return (parsed_dataset, written, skipped)."""
    out = io.StringIO()
    written, skipped = serialize_nquads(batches, GRAPH, out)
    ds = rdflib.Dataset()
    ds.parse(data=out.getvalue(), format="nquads")
    return ds, written, skipped


class TestNquadsRoundTrip:

    def test_iri_and_literal_flavours_survive_roundtrip(self):
        batches = [[
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/p"),
             "o": iri("http://example.com/o")},
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/label"),
             "o": lit("plain value")},
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/label"),
             "o": lit("bonjour", lang="fr")},
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/count"),
             "o": lit("42", d="http://www.w3.org/2001/XMLSchema#integer")},
        ]]
        ds, written, skipped = roundtrip(batches)

        assert (written, skipped) == (4, 0)
        quads = list(ds.quads((None, None, None, None)))
        assert len(quads) == 4
        g = rdflib.URIRef(GRAPH)
        assert all(q[3] == g for q in quads)

        objects = {q[2] for q in quads}
        assert rdflib.URIRef("http://example.com/o") in objects
        assert rdflib.Literal("plain value") in objects
        assert rdflib.Literal("bonjour", lang="fr") in objects
        assert rdflib.Literal(
            "42", datatype=rdflib.URIRef("http://www.w3.org/2001/XMLSchema#integer")
        ) in objects

    def test_hostile_literal_content_is_escaped_losslessly(self):
        nasty = 'line1\nline2\t"quoted" back\\slash 中文 emoji\U0001f680'
        batches = [[{
            "s": iri("http://example.com/s"),
            "p": iri("http://example.com/note"),
            "o": lit(nasty),
        }]]
        ds, written, skipped = roundtrip(batches)

        assert (written, skipped) == (1, 0)
        obj = next(iter(ds.quads((None, None, None, None))))[2]
        assert str(obj) == nasty

    def test_malformed_and_unrepresentable_terms_are_skipped_not_emitted(self):
        batches = [[
            # IRI with a space (matches graph_to_turtle's malformed skip)
            {"s": iri("http://example.com/bad iri"), "p": iri("http://example.com/p"),
             "o": lit("x")},
            # RDF-star quoted triple: no N-Quads encoding
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/p"),
             "o": {"t": "r", "r": {}}},
            # literal in predicate position: invalid RDF
            {"s": iri("http://example.com/s"), "p": lit("not-a-predicate"),
             "o": lit("x")},
            # language tag outside the LANGTAG production: emitting it raw
            # would break the line and make the whole member unparseable
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/label"),
             "o": lit("bonjour", lang="fr CA")},
            # one good triple to prove the stream continues past skips
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/p"),
             "o": lit("good")},
        ]]
        ds, written, skipped = roundtrip(batches)

        assert (written, skipped) == (1, 4)
        assert len(list(ds.quads((None, None, None, None)))) == 1

    def test_unusable_language_tags_are_skipped_not_emitted(self):
        """One bad tag must not cost the whole member.

        parse_nquads hands the entire member to rdflib at once, and its
        N-Quads parser aborts on the first malformed line, so a tag emitted
        raw takes every other triple in the bundle down with it.
        """
        good = {"s": iri("http://example.com/s"), "p": iri("http://example.com/p"),
                "o": lit("good")}

        for bad in ["fr CA", "en_US", "en\n", 'en> "x" <urn:evil', 7]:
            batches = [[
                {"s": iri("http://example.com/s"),
                 "p": iri("http://example.com/label"),
                 "o": lit("bonjour", lang=bad)},
                good,
            ]]
            ds, written, skipped = roundtrip(batches)
            assert (written, skipped) == (1, 1), f"tag {bad!r} was not skipped"
            assert len(list(ds.quads((None, None, None, None)))) == 1

        # subtags are part of the production and must still survive
        for ok in ["fr", "fr-CA", "de-DE-1996"]:
            batches = [[{"s": iri("http://example.com/s"),
                         "p": iri("http://example.com/label"),
                         "o": lit("bonjour", lang=ok)}]]
            ds, written, skipped = roundtrip(batches)
            assert (written, skipped) == (1, 0), f"tag {ok!r} was wrongly skipped"
            obj = next(iter(ds.quads((None, None, None, None))))[2]
            assert obj == rdflib.Literal("bonjour", lang=ok)

    def test_parse_nquads_preserves_term_types(self):
        """parse_nquads must preserve datatype, language and IRI-vs-literal."""
        batches = [[
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/typed"),
             "o": lit("42", d="http://www.w3.org/2001/XMLSchema#integer")},
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/tagged"),
             "o": lit("bonjour", lang="fr")},
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/ref"),
             "o": iri("http://example.com/o")},
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/str"),
             "o": lit("http://example.com/o")},
        ]]
        out = io.StringIO()
        serialize_nquads(batches, GRAPH, out)
        triples = parse_nquads(out.getvalue().encode())

        by_pred = {t.p: t for t in triples}

        typed = by_pred["http://example.com/typed"]
        assert typed.o == "42"
        assert typed.o_datatype == "http://www.w3.org/2001/XMLSchema#integer"
        assert typed.o_language == ""

        tagged = by_pred["http://example.com/tagged"]
        assert tagged.o == "bonjour"
        assert tagged.o_language == "fr"
        assert tagged.o_datatype == ""

        ref = by_pred["http://example.com/ref"]
        assert ref.o == "http://example.com/o"
        assert ref.o_datatype == ""
        assert ref.o_language == ""

        string_lit = by_pred["http://example.com/str"]
        assert string_lit.o == "http://example.com/o"
        assert string_lit.o_datatype == ""

        # IRI and literal with the same lexical form must remain distinguishable
        assert ref.o == string_lit.o

    def test_streaming_shape_one_line_per_triple(self):
        line = triple_to_nquad(
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/p"),
             "o": lit("v")},
            f"<{GRAPH}>",
        )
        assert line.endswith(" .\n")
        assert line.count("\n") == 1
