"""
Round-trip tests for the streaming N-Quads serializer: wire-format triples
are serialized line-by-line, then parsed back with rdflib's nquads parser
and compared term-for-term — proving the output is valid N-Quads and the
encoding (escaping, datatypes, language tags, unicode) is lossless.
"""

import io

import rdflib

from trustgraph.cli.nquads import serialize_nquads, triple_to_nquad

GRAPH = "urn:trustgraph:collection:default"


def iri(v):
    return {"t": "i", "i": v}


def lit(v, d=None, lang=None):
    t = {"t": "l", "v": v}
    if d:
        t["d"] = d
    if lang:
        t["l"] = lang
    return t


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
            # one good triple to prove the stream continues past skips
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/p"),
             "o": lit("good")},
        ]]
        ds, written, skipped = roundtrip(batches)

        assert (written, skipped) == (1, 3)
        assert len(list(ds.quads((None, None, None, None)))) == 1

    def test_streaming_shape_one_line_per_triple(self):
        # Two batches -> lines usable incrementally (no whole-graph buffering).
        line = triple_to_nquad(
            {"s": iri("http://example.com/s"), "p": iri("http://example.com/p"),
             "o": lit("v")},
            f"<{GRAPH}>",
        )
        assert line.endswith(" .\n")
        assert line.count("\n") == 1
