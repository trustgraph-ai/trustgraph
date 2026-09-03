"""
Term-conversion tests for the Turtle dumper: term_to_rdflib follows the same
"return None to skip" contract as the N-Quads encoder, and show_graph only
serializes once the whole stream has been consumed, so a term that raises
instead of returning None loses the entire dump.
"""

import rdflib

from trustgraph.cli.graph_to_turtle import term_to_rdflib

from tests.unit.test_cli.conftest import iri, lit


class TestTermToRdflib:

    def test_iri_and_literal_flavours_convert(self):
        assert term_to_rdflib(iri("http://example.com/s")) == \
            rdflib.term.URIRef("http://example.com/s")
        assert term_to_rdflib(lit("plain value")) == rdflib.term.Literal("plain value")
        assert term_to_rdflib(lit("bonjour", lang="fr")) == \
            rdflib.term.Literal("bonjour", lang="fr")
        assert term_to_rdflib(lit("bonjour", lang="fr-CA")) == \
            rdflib.term.Literal("bonjour", lang="fr-CA")

    def test_malformed_iri_is_skipped(self):
        assert term_to_rdflib(iri("http://example.com/bad iri")) is None

    def test_unusable_language_tag_is_skipped_not_raised(self):
        for bad in ["fr CA", "en_US", "en\n", 'en> "x" <urn:evil', 7]:
            assert term_to_rdflib(lit("bonjour", lang=bad)) is None, \
                f"tag {bad!r} was not skipped"
