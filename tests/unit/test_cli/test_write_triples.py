"""
Tests for the N-Triples line parser behind tg-write-triples: the lines it
reads are the ones the CLI itself writes (nquads.py), so IRIs of any scheme
must stay IRIs and the string escapes must be decoded.
"""

import pytest

from trustgraph.cli.nquads import encode_term
from trustgraph.cli.write_triples import parse_ntriples_line

from tests.unit.test_cli.conftest import lit


def _object(escaped):
    line = f'<http://ex.org/s> <http://ex.org/p> "{escaped}" .'
    return parse_ntriples_line(line)[2]["v"]


def test_iri_with_other_scheme_stays_iri():
    s, p, o = parse_ntriples_line(
        "<mailto:a@example.org> <http://ex.org/p> <ftp://ex.org/f> ."
    )
    assert s == {"t": "i", "i": "mailto:a@example.org"}
    assert p == {"t": "i", "i": "http://ex.org/p"}
    assert o == {"t": "i", "i": "ftp://ex.org/f"}


@pytest.mark.parametrize("value", [
    'say "hi"',
    "line one\nline two",
    "tab\there",
    "back\\slash",
    "cr\rlf",
    "mixed \"q\" \\ \n end",
])
def test_literal_round_trips_through_the_writer(value):
    encoded = encode_term(lit(value), is_object=True)
    line = f"<http://ex.org/s> <http://ex.org/p> {encoded} ."
    s, p, o = parse_ntriples_line(line)
    assert o["v"] == value


def test_unicode_escapes():
    assert _object(r"caf\u00e9 \U0001F600") == "café \U0001F600"


def test_unknown_escape_is_kept():
    assert _object(r"a\qb") == r"a\qb"
