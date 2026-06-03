"""
Round-trip unit tests for KnowledgeRequestTranslator and
KnowledgeResponseTranslator.

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

from trustgraph.messaging.translators.knowledge import (
    KnowledgeRequestTranslator,
    KnowledgeResponseTranslator,
)
from trustgraph.schema import (
    KnowledgeRequest,
    KnowledgeResponse,
    GraphEmbeddings,
    EntityEmbeddings,
    Triples,
    Triple,
    Metadata,
    Term,
    IRI,
    LibraryMetadata,
    LibraryBlob,
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


class TestKnowledgeRequestTranslatorLibrary:

    def test_roundtrip_preserves_library_metadata(self, translator):
        request = KnowledgeRequest(
            operation="put-kg-core",
            id="doc-1",
            library_metadata=LibraryMetadata(
                id="doc-1",
                kind="application/pdf",
                title="Test Document",
                parent_id="",
                document_type="source",
                comments="test comments",
                tags=["tag1", "tag2"],
            ),
        )

        encoded = translator.encode(request)
        assert "library-metadata" in encoded
        lm = encoded["library-metadata"]
        assert lm["id"] == "doc-1"
        assert lm["kind"] == "application/pdf"
        assert lm["title"] == "Test Document"
        assert lm["parent-id"] == ""
        assert lm["document-type"] == "source"
        assert lm["comments"] == "test comments"
        assert lm["tags"] == ["tag1", "tag2"]

        decoded = translator.decode(encoded)
        assert decoded.library_metadata is not None
        assert decoded.library_metadata.id == "doc-1"
        assert decoded.library_metadata.kind == "application/pdf"
        assert decoded.library_metadata.title == "Test Document"
        assert decoded.library_metadata.parent_id == ""
        assert decoded.library_metadata.document_type == "source"
        assert decoded.library_metadata.comments == "test comments"
        assert decoded.library_metadata.tags == ["tag1", "tag2"]

    def test_roundtrip_preserves_child_document_metadata(self, translator):
        request = KnowledgeRequest(
            operation="put-kg-core",
            id="doc-1",
            library_metadata=LibraryMetadata(
                id="chunk-1",
                kind="text/plain",
                title="Chunk 1",
                parent_id="doc-1",
                document_type="chunk",
            ),
        )

        encoded = translator.encode(request)
        decoded = translator.decode(encoded)

        assert decoded.library_metadata.parent_id == "doc-1"
        assert decoded.library_metadata.document_type == "chunk"

    def test_roundtrip_preserves_library_blob(self, translator):
        request = KnowledgeRequest(
            operation="put-kg-core",
            id="doc-1",
            library_blob=LibraryBlob(
                id="doc-1",
                data=b"SGVsbG8gV29ybGQ=",
            ),
        )

        encoded = translator.encode(request)
        assert "library-blob" in encoded
        assert encoded["library-blob"]["id"] == "doc-1"
        assert encoded["library-blob"]["data"] == "SGVsbG8gV29ybGQ="

        decoded = translator.decode(encoded)
        assert decoded.library_blob is not None
        assert decoded.library_blob.id == "doc-1"
        assert decoded.library_blob.data == "SGVsbG8gV29ybGQ="

    def test_absent_library_fields_decode_as_none(self, translator):
        decoded = translator.decode({
            "operation": "get-kg-core",
            "id": "doc-1",
        })
        assert decoded.library_metadata is None
        assert decoded.library_blob is None


class TestKnowledgeResponseTranslatorLibrary:

    @pytest.fixture
    def response_translator(self):
        return KnowledgeResponseTranslator()

    def test_encode_library_metadata(self, response_translator):
        response = KnowledgeResponse(
            ids=None,
            library_metadata=LibraryMetadata(
                id="doc-1",
                kind="application/pdf",
                title="Test",
                parent_id="",
                document_type="source",
                comments="",
                tags=[],
            ),
        )
        encoded = response_translator.encode(response)
        assert "library-metadata" in encoded
        assert encoded["library-metadata"]["id"] == "doc-1"
        assert encoded["library-metadata"]["kind"] == "application/pdf"
        assert encoded["library-metadata"]["document-type"] == "source"

    def test_encode_library_blob_bytes_to_string(self, response_translator):
        response = KnowledgeResponse(
            ids=None,
            library_blob=LibraryBlob(
                id="doc-1",
                data=b"dGVzdCBkYXRh",
            ),
        )
        encoded = response_translator.encode(response)
        assert "library-blob" in encoded
        assert encoded["library-blob"]["id"] == "doc-1"
        assert encoded["library-blob"]["data"] == "dGVzdCBkYXRh"
        assert isinstance(encoded["library-blob"]["data"], str)

    def test_encode_library_blob_string_passthrough(self, response_translator):
        response = KnowledgeResponse(
            ids=None,
            library_blob=LibraryBlob(
                id="doc-1",
                data="already-a-string",
            ),
        )
        encoded = response_translator.encode(response)
        assert encoded["library-blob"]["data"] == "already-a-string"

    def test_library_metadata_is_not_final(self, response_translator):
        response = KnowledgeResponse(
            ids=None,
            library_metadata=LibraryMetadata(id="doc-1"),
        )
        _, is_final = response_translator.encode_with_completion(response)
        assert is_final is False

    def test_library_blob_is_not_final(self, response_translator):
        response = KnowledgeResponse(
            ids=None,
            library_blob=LibraryBlob(id="doc-1", data=b"data"),
        )
        _, is_final = response_translator.encode_with_completion(response)
        assert is_final is False

    def test_eos_is_final(self, response_translator):
        response = KnowledgeResponse(eos=True)
        _, is_final = response_translator.encode_with_completion(response)
        assert is_final is True
