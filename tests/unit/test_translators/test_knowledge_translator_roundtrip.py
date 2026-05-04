"""
Round-trip unit tests for KnowledgeRequestTranslator.

Regression coverage: a previous version of the decode side constructed
EntityEmbeddings(vectors=...) — the schema field is `vector` (singular),
so any real graph-embeddings KnowledgeRequest would crash on first
message. The encode side already wrote `"vector"`, so encode→decode was
asymmetric.

These tests build a real KnowledgeRequest with graph-embeddings, encode
it, decode the result, and assert the round-trip is lossless. They also
exercise the triples path so any future schema drift in Metadata or
Triples breaks the test.
"""

import pytest

from trustgraph.messaging.translators.knowledge import KnowledgeRequestTranslator
from trustgraph.schema import (
    KnowledgeRequest,
    GraphEmbeddings,
    EntityEmbeddings,
    Triples,
    Triple,
    Metadata,
    Term,
    IRI,
)


def _term_iri(uri):
    return Term(type=IRI, iri=uri)


@pytest.fixture
def translator():
    return KnowledgeRequestTranslator()


@pytest.fixture
def graph_embeddings_request():
    return KnowledgeRequest(
        operation="put-kg-core",
        id="doc-1",
        flow="default",
        collection="testcoll",
        graph_embeddings=GraphEmbeddings(
            metadata=Metadata(
                id="doc-1",
                root="",
                collection="testcoll",
            ),
            entities=[
                EntityEmbeddings(
                    entity=_term_iri("http://example.org/alice"),
                    vector=[0.1, 0.2, 0.3],
                ),
                EntityEmbeddings(
                    entity=_term_iri("http://example.org/bob"),
                    vector=[0.4, 0.5, 0.6],
                ),
            ],
        ),
    )


@pytest.fixture
def triples_request():
    return KnowledgeRequest(
        operation="put-kg-core",
        id="doc-1",
        flow="default",
        collection="testcoll",
        triples=Triples(
            metadata=Metadata(
                id="doc-1",
                root="",
                collection="testcoll",
            ),
            triples=[
                Triple(
                    s=_term_iri("http://example.org/alice"),
                    p=_term_iri("http://example.org/knows"),
                    o=_term_iri("http://example.org/bob"),
                ),
            ],
        ),
    )


class TestKnowledgeRequestTranslatorGraphEmbeddings:

    def test_encode_produces_singular_vector_key(
        self, translator, graph_embeddings_request,
    ):
        """The wire key must be `vector`, never `vectors`."""
        encoded = translator.encode(graph_embeddings_request)
        entities = encoded["graph-embeddings"]["entities"]
        assert all("vector" in e for e in entities)
        assert all("vectors" not in e for e in entities)
        assert entities[0]["vector"] == [0.1, 0.2, 0.3]

    def test_roundtrip_preserves_graph_embeddings(
        self, translator, graph_embeddings_request,
    ):
        """encode -> decode must be lossless for the GE branch."""
        encoded = translator.encode(graph_embeddings_request)
        decoded = translator.decode(encoded)

        assert isinstance(decoded, KnowledgeRequest)
        assert decoded.operation == "put-kg-core"
        assert decoded.id == "doc-1"
        assert decoded.id == "doc-1"
        assert decoded.flow == "default"
        assert decoded.collection == "testcoll"

        assert decoded.graph_embeddings is not None
        ge = decoded.graph_embeddings
        assert isinstance(ge, GraphEmbeddings)
        assert isinstance(ge.metadata, Metadata)
        assert ge.metadata.id == "doc-1"
        assert ge.metadata.collection == "testcoll"

        assert len(ge.entities) == 2
        assert ge.entities[0].vector == [0.1, 0.2, 0.3]
        assert ge.entities[1].vector == [0.4, 0.5, 0.6]
        assert ge.entities[0].entity.iri == "http://example.org/alice"
        assert ge.entities[1].entity.iri == "http://example.org/bob"


class TestKnowledgeRequestTranslatorTriples:

    def test_roundtrip_preserves_triples(self, translator, triples_request):
        encoded = translator.encode(triples_request)
        decoded = translator.decode(encoded)

        assert isinstance(decoded, KnowledgeRequest)
        assert decoded.triples is not None
        assert isinstance(decoded.triples.metadata, Metadata)
        assert decoded.triples.metadata.id == "doc-1"
        assert decoded.triples.metadata.collection == "testcoll"

        assert len(decoded.triples.triples) == 1
        t = decoded.triples.triples[0]
        assert t.s.iri == "http://example.org/alice"
        assert t.p.iri == "http://example.org/knows"
        assert t.o.iri == "http://example.org/bob"
