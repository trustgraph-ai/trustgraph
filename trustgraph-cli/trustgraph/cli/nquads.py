"""
N-Quads serialization and parsing for workspace knowledge bundles: the
wire-format triples yielded by triples_query_stream go out one line per
triple (so an export never holds a whole graph in memory), and bundle
members come back as api Triple values. Term encoding is hand-rolled to
the N-Triples grammar: rdflib's term.n3() emits Turtle-style forms
(numeric shorthand, unescaped newlines) that are not valid in
line-oriented N-Quads.
"""

import re

import rdflib

from trustgraph.schema import IRI, LITERAL
from trustgraph.api.types import Triple

# RDF-star quoted triples have no standard N-Quads encoding; they are
# skipped with a count so callers can surface the omission.

# N-Triples string-literal escapes (ECHAR): backslash first, then the rest.
_ESCAPES = [
    ("\\", "\\\\"),
    ('"', '\\"'),
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\t", "\\t"),
]

# Characters the IRIREF production cannot carry: controls/space plus the
# explicitly forbidden set. One compiled scan keeps this off the profile
# for large exports (it runs per term).
_BAD_IRI = re.compile(r'[\x00-\x20<>"{}|^\x60]')


def _escape_literal(value):
    for raw, esc in _ESCAPES:
        value = value.replace(raw, esc)
    return value


def _encode_iri(iri):
    """<iri>, or None for values the grammar cannot carry."""
    if not iri or _BAD_IRI.search(iri):
        return None
    return f"<{iri}>"


def encode_term(term, is_object=False):
    """Encode one wire-format term dict for an N-Quads line.

    :param is_object: literals are only valid in object position;
        subjects and predicates must be IRIs (bnodes never appear on
        the wire).
    :returns: encoded string, or None when the term can't be represented.
    """
    if term is None:
        return None

    t = term.get("t", "")

    if t == IRI:
        return _encode_iri(term.get("i", ""))

    if t == LITERAL and is_object:
        value = _escape_literal(term.get("v", ""))
        language = term.get("l")
        datatype = term.get("d")
        if language:
            return f'"{value}"@{language}'
        if datatype:
            dt = _encode_iri(datatype)
            if dt is None:
                return None
            return f'"{value}"^^{dt}'
        return f'"{value}"'

    # literals outside object position, RDF-star, unknown types
    return None


def triple_to_nquad(triple, graph_encoded):
    """One wire-format triple dict -> an N-Quads line, or None to skip.

    :param triple: {"s": term, "p": term, "o": term} wire dict
    :param graph_encoded: pre-encoded <graph-iri> string
    """
    s = encode_term(triple.get("s"))
    p = encode_term(triple.get("p"))
    o = encode_term(triple.get("o"), is_object=True)
    if s is None or p is None or o is None:
        return None
    return f"{s} {p} {o} {graph_encoded} .\n"


def serialize_nquads(batches, graph_iri, out):
    """Write wire-format triple batches to a text file-like as N-Quads.

    :param batches: iterable of lists of wire triple dicts
        (e.g. triples_query_stream output)
    :param graph_iri: graph name for every quad (str)
    :param out: text-mode file-like with .write()
    :returns: (written, skipped) counts
    """
    g = _encode_iri(graph_iri)
    if g is None:
        raise ValueError(f"graph IRI not representable in N-Quads: {graph_iri!r}")
    written = 0
    skipped = 0
    for batch in batches:
        for t in batch:
            line = triple_to_nquad(t, g)
            if line is None:
                skipped += 1
            else:
                out.write(line)
                written += 1
    return written, skipped


def parse_nquads(data):
    """Parse N-Quads bytes back into api Triple values.

    Terms are stringified with str(), the same convention tg-load-knowledge
    uses, so values survive the store round trip unchanged. The whole
    member is materialized in memory (bundles are bounded by
    --triples-limit at export); line-streaming is a possible follow-up.

    :param data: N-Quads bytes (one bundle member)
    :returns: list of Triple
    """
    ds = rdflib.Dataset()
    ds.parse(data=data.decode("utf-8"), format="nquads")
    return [
        Triple(s=str(s), p=str(p), o=str(o))
        for s, p, o, _g in ds.quads((None, None, None, None))
    ]
