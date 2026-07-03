"""
Streaming N-Quads serialization of wire-format triples (the dict shape
yielded by triples_query_stream), one line per triple, so a knowledge
export never has to hold a whole graph in memory. Term encoding is
hand-rolled to the N-Triples grammar: rdflib's term.n3() emits
Turtle-style forms (numeric shorthand, unescaped newlines) that are not
valid in line-oriented N-Quads.
"""

# RDF-star quoted triples ("r" terms) have no standard N-Quads encoding;
# they are skipped with a count so callers can surface the omission.

# N-Triples string-literal escapes (ECHAR): backslash first, then the rest.
_ESCAPES = [
    ("\\", "\\\\"),
    ('"', '\\"'),
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\t", "\\t"),
]


def _escape_literal(value):
    for raw, esc in _ESCAPES:
        value = value.replace(raw, esc)
    return value


def _encode_iri(iri):
    """<iri>, or None for values the grammar cannot carry."""
    if not iri or any(c in iri for c in ' <>"{}|^`') or any(ord(c) <= 0x20 for c in iri):
        return None
    return f"<{iri}>"


def encode_term(term, position):
    """Encode one wire-format term dict for an N-Quads line.

    :param position: "s" | "p" | "o" — subjects and predicates must be IRIs
        (bnodes never appear on the wire); literals are object-only.
    :returns: encoded string, or None when the term can't be represented.
    """
    if term is None:
        return None

    t = term.get("t", "")

    if t == "i":
        return _encode_iri(term.get("i", ""))

    if t == "l" and position == "o":
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

    # literals outside object position, RDF-star ("r"), unknown types
    return None


def triple_to_nquad(triple, graph_encoded):
    """One wire-format triple dict -> an N-Quads line, or None to skip.

    :param triple: {"s": term, "p": term, "o": term} wire dict
    :param graph_encoded: pre-encoded <graph-iri> string
    """
    s = encode_term(triple.get("s"), "s")
    p = encode_term(triple.get("p"), "p")
    o = encode_term(triple.get("o"), "o")
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
