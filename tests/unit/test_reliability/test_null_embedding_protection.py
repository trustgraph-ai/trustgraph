"""
Tests for null embedding protection: empty/None vector skipping, entity
validation, dimension-aware collection creation, and query-time empty
vector handling.

Tests the pure functions and logic without Qdrant connections.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from trustgraph.schema import Term, IRI, LITERAL, BLANK


# ---------------------------------------------------------------------------
# Graph embeddings: get_term_value
# ---------------------------------------------------------------------------

class TestGraphEmbeddingsGetTermValue:

    def test_iri_returns_iri(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import get_term_value
        t = Term(type=IRI, iri="http://example.org/x")
        assert get_term_value(t) == "http://example.org/x"

    def test_literal_returns_value(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import get_term_value
        t = Term(type=LITERAL, value="hello")
        assert get_term_value(t) == "hello"

    def test_blank_returns_id(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import get_term_value
        t = Term(type=BLANK, id="_:b0")
        assert get_term_value(t) == "_:b0"

    def test_none_returns_none(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import get_term_value
        assert get_term_value(None) is None

    def test_blank_with_value_fallback(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import get_term_value
        t = Term(type=BLANK, id="", value="fallback")
        assert get_term_value(t) == "fallback"


# ---------------------------------------------------------------------------
# Document embeddings: null vector protection
# ---------------------------------------------------------------------------

class TestDocEmbeddingsNullProtection:

    @pytest.mark.asyncio
    async def test_empty_vector_skipped(self):
        """Embeddings with empty vectors should be silently skipped."""
        from trustgraph.storage.doc_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()

        # Mock collection_exists for config check
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "col1"

        emb = MagicMock()
        emb.chunk_id = "chunk-1"
        emb.vector = []  # Empty vector
        msg.chunks = [emb]

        await proc.store_document_embeddings(msg)

        # No upsert should be called
        proc.qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_vector_skipped(self):
        from trustgraph.storage.doc_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "col1"

        emb = MagicMock()
        emb.chunk_id = "chunk-1"
        emb.vector = None  # None vector
        msg.chunks = [emb]

        await proc.store_document_embeddings(msg)
        proc.qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_chunk_id_skipped(self):
        from trustgraph.storage.doc_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "col1"

        emb = MagicMock()
        emb.chunk_id = ""  # Empty chunk ID
        emb.vector = [0.1, 0.2, 0.3]
        msg.chunks = [emb]

        await proc.store_document_embeddings(msg)
        proc.qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_embedding_upserted(self):
        from trustgraph.storage.doc_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.qdrant.collection_exists.return_value = True
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "col1"

        emb = MagicMock()
        emb.chunk_id = "chunk-1"
        emb.vector = [0.1, 0.2, 0.3]
        msg.chunks = [emb]

        await proc.store_document_embeddings(msg)
        proc.qdrant.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_dimension_in_collection_name(self):
        """Collection name should include vector dimension."""
        from trustgraph.storage.doc_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.qdrant.collection_exists.return_value = True
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "alice"
        msg.metadata.collection = "docs"

        emb = MagicMock()
        emb.chunk_id = "c1"
        emb.vector = [0.0] * 384  # 384-dim vector
        msg.chunks = [emb]

        await proc.store_document_embeddings(msg)

        call_args = proc.qdrant.upsert.call_args
        assert "d_alice_docs_384" in call_args[1]["collection_name"]


# ---------------------------------------------------------------------------
# Graph embeddings: null entity and vector protection
# ---------------------------------------------------------------------------

class TestGraphEmbeddingsNullProtection:

    @pytest.mark.asyncio
    async def test_empty_entity_skipped(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "col1"

        entity = MagicMock()
        entity.entity = Term(type=IRI, iri="")  # Empty IRI
        entity.vector = [0.1, 0.2, 0.3]
        msg.entities = [entity]

        await proc.store_graph_embeddings(msg)
        proc.qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_entity_skipped(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "col1"

        entity = MagicMock()
        entity.entity = None  # Null entity
        entity.vector = [0.1, 0.2, 0.3]
        msg.entities = [entity]

        await proc.store_graph_embeddings(msg)
        proc.qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_vector_skipped(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "col1"

        entity = MagicMock()
        entity.entity = Term(type=IRI, iri="http://example.org/x")
        entity.vector = []  # Empty vector
        msg.entities = [entity]

        await proc.store_graph_embeddings(msg)
        proc.qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_entity_and_vector_upserted(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.qdrant.collection_exists.return_value = True
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "col1"

        entity = MagicMock()
        entity.entity = Term(type=IRI, iri="http://example.org/Alice")
        entity.vector = [0.1, 0.2, 0.3]
        entity.chunk_id = "c1"
        msg.entities = [entity]

        await proc.store_graph_embeddings(msg)
        proc.qdrant.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_lazy_collection_creation_on_new_dimension(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.qdrant.collection_exists.return_value = False
        proc.collection_exists = MagicMock(return_value=True)

        msg = MagicMock()
        msg.metadata.user = "alice"
        msg.metadata.collection = "graphs"

        entity = MagicMock()
        entity.entity = Term(type=IRI, iri="http://example.org/x")
        entity.vector = [0.0] * 768
        entity.chunk_id = ""
        msg.entities = [entity]

        await proc.store_graph_embeddings(msg)

        # Collection should be created with correct dimension
        proc.qdrant.create_collection.assert_called_once()
        create_args = proc.qdrant.create_collection.call_args
        assert create_args[1]["collection_name"] == "t_alice_graphs_768"


# ---------------------------------------------------------------------------
# Collection validation — deleted-while-in-flight protection
# ---------------------------------------------------------------------------

class TestCollectionValidation:

    @pytest.mark.asyncio
    async def test_doc_embeddings_dropped_for_deleted_collection(self):
        from trustgraph.storage.doc_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.collection_exists = MagicMock(return_value=False)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "deleted-col"
        msg.chunks = [MagicMock()]

        await proc.store_document_embeddings(msg)
        proc.qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_graph_embeddings_dropped_for_deleted_collection(self):
        from trustgraph.storage.graph_embeddings.qdrant.write import Processor

        proc = Processor.__new__(Processor)
        proc.qdrant = MagicMock()
        proc.collection_exists = MagicMock(return_value=False)

        msg = MagicMock()
        msg.metadata.user = "user1"
        msg.metadata.collection = "deleted-col"
        msg.entities = [MagicMock()]

        await proc.store_graph_embeddings(msg)
        proc.qdrant.upsert.assert_not_called()
