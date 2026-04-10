"""
Round-trip unit tests for DocumentEmbeddingsTranslator.

Regression coverage: a previous version of the decode side constructed
ChunkEmbeddings(vectors=...) — the schema field is `vector` (singular),
so any real DocumentEmbeddings message would crash on decode. The encode
side already wrote `"vector"`, so encode→decode was asymmetric.
"""

import pytest

from trustgraph.messaging.translators.document_loading import (
    DocumentEmbeddingsTranslator,
)
from trustgraph.schema import (
    DocumentEmbeddings,
    ChunkEmbeddings,
    Metadata,
)


@pytest.fixture
def translator():
    return DocumentEmbeddingsTranslator()


@pytest.fixture
def sample():
    return DocumentEmbeddings(
        metadata=Metadata(
            id="doc-1",
            root="",
            user="alice",
            collection="testcoll",
        ),
        chunks=[
            ChunkEmbeddings(chunk_id="c1", vector=[0.1, 0.2, 0.3]),
            ChunkEmbeddings(chunk_id="c2", vector=[0.4, 0.5, 0.6]),
        ],
    )


class TestDocumentEmbeddingsTranslator:

    def test_encode_uses_singular_vector_key(self, translator, sample):
        encoded = translator.encode(sample)
        chunks = encoded["chunks"]
        assert all("vector" in c for c in chunks)
        assert all("vectors" not in c for c in chunks)
        assert chunks[0]["vector"] == [0.1, 0.2, 0.3]

    def test_roundtrip_preserves_document_embeddings(self, translator, sample):
        encoded = translator.encode(sample)
        decoded = translator.decode(encoded)

        assert isinstance(decoded, DocumentEmbeddings)
        assert isinstance(decoded.metadata, Metadata)
        assert decoded.metadata.id == "doc-1"
        assert decoded.metadata.user == "alice"
        assert decoded.metadata.collection == "testcoll"

        assert len(decoded.chunks) == 2
        assert decoded.chunks[0].chunk_id == "c1"
        assert decoded.chunks[0].vector == [0.1, 0.2, 0.3]
        assert decoded.chunks[1].chunk_id == "c2"
        assert decoded.chunks[1].vector == [0.4, 0.5, 0.6]
