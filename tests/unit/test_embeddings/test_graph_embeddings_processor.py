"""
Tests for graph embeddings processor — batch embedding of entity contexts.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.embeddings.graph_embeddings.embeddings import Processor
from trustgraph.schema import (
    EntityContexts, EntityEmbeddings, GraphEmbeddings,
    Term, IRI, Metadata,
)


@pytest.fixture
def processor():
    return Processor(
        taskgroup=AsyncMock(),
        id="test-graph-embeddings",
        batch_size=3,
    )


def _make_entity_context(name, context, chunk_id="chunk-1"):
    """Create an entity context for testing."""
    entity = Term(type=IRI, iri=f"urn:entity:{name}")
    return MagicMock(entity=entity, context=context, chunk_id=chunk_id)


def _make_message(entities, doc_id="doc-1", user="test", collection="default"):
    metadata = Metadata(id=doc_id, user=user, collection=collection)
    value = EntityContexts(metadata=metadata, entities=entities)
    msg = MagicMock()
    msg.value.return_value = value
    return msg


class TestGraphEmbeddingsInit:

    def test_default_batch_size(self):
        p = Processor(taskgroup=AsyncMock(), id="test")
        assert p.batch_size == 5

    def test_custom_batch_size(self):
        p = Processor(taskgroup=AsyncMock(), id="test", batch_size=20)
        assert p.batch_size == 20


class TestGraphEmbeddingsBatchProcessing:

    @pytest.mark.asyncio
    async def test_single_batch_call_for_all_entities(self, processor):
        """All entity contexts should be embedded in a single API call."""
        entities = [
            _make_entity_context("Alice", "Alice is a person"),
            _make_entity_context("Bob", "Bob is a developer"),
            _make_entity_context("Acme", "Acme is a company"),
        ]
        msg = _make_message(entities)

        mock_embed = AsyncMock(return_value=[
            [0.1, 0.2], [0.3, 0.4], [0.5, 0.6],
        ])
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(embed=mock_embed)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        # Single batch call with all three texts
        mock_embed.assert_called_once_with(
            texts=["Alice is a person", "Bob is a developer", "Acme is a company"]
        )

    @pytest.mark.asyncio
    async def test_vectors_paired_with_correct_entities(self, processor):
        """Each vector should be paired with its corresponding entity."""
        entities = [
            _make_entity_context("Alice", "ctx-A", chunk_id="c1"),
            _make_entity_context("Bob", "ctx-B", chunk_id="c2"),
        ]
        msg = _make_message(entities)

        vectors = [[1.0, 2.0], [3.0, 4.0]]
        mock_embed = AsyncMock(return_value=vectors)
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(embed=mock_embed)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        # With batch_size=3, all 2 entities fit in one output message
        mock_output.send.assert_called_once()
        result = mock_output.send.call_args[0][0]
        assert isinstance(result, GraphEmbeddings)
        assert len(result.entities) == 2
        assert result.entities[0].vector == [1.0, 2.0]
        assert result.entities[0].entity.iri == "urn:entity:Alice"
        assert result.entities[0].chunk_id == "c1"
        assert result.entities[1].vector == [3.0, 4.0]
        assert result.entities[1].entity.iri == "urn:entity:Bob"

    @pytest.mark.asyncio
    async def test_output_batching(self, processor):
        """Output should be split into batches of batch_size."""
        # batch_size=3, 7 entities -> 3 output messages (3+3+1)
        entities = [
            _make_entity_context(f"E{i}", f"context {i}")
            for i in range(7)
        ]
        msg = _make_message(entities)

        vectors = [[float(i)] for i in range(7)]
        mock_embed = AsyncMock(return_value=vectors)
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(embed=mock_embed)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        assert mock_output.send.call_count == 3
        # First batch has 3 entities
        batch1 = mock_output.send.call_args_list[0][0][0]
        assert len(batch1.entities) == 3
        # Second batch has 3 entities
        batch2 = mock_output.send.call_args_list[1][0][0]
        assert len(batch2.entities) == 3
        # Third batch has 1 entity
        batch3 = mock_output.send.call_args_list[2][0][0]
        assert len(batch3.entities) == 1

    @pytest.mark.asyncio
    async def test_output_batches_preserve_metadata(self, processor):
        """Each output batch should carry the original metadata."""
        entities = [
            _make_entity_context(f"E{i}", f"ctx {i}")
            for i in range(5)
        ]
        msg = _make_message(entities, doc_id="doc-42", user="alice", collection="main")

        mock_embed = AsyncMock(return_value=[[0.0]] * 5)
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(embed=mock_embed)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        for call in mock_output.send.call_args_list:
            result = call[0][0]
            assert result.metadata.id == "doc-42"
            assert result.metadata.user == "alice"
            assert result.metadata.collection == "main"

    @pytest.mark.asyncio
    async def test_single_entity(self, processor):
        """Single entity should work with one embed call and one output."""
        entities = [_make_entity_context("Solo", "solo context")]
        msg = _make_message(entities)

        mock_embed = AsyncMock(return_value=[[1.0, 2.0, 3.0]])
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(embed=mock_embed)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        mock_embed.assert_called_once_with(texts=["solo context"])
        mock_output.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_error_propagates(self, processor):
        """Embedding service errors should propagate for retry."""
        entities = [_make_entity_context("E", "ctx")]
        msg = _make_message(entities)

        mock_embed = AsyncMock(side_effect=RuntimeError("embedding failed"))

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(embed=mock_embed)
            return MagicMock()

        with pytest.raises(RuntimeError, match="embedding failed"):
            await processor.on_message(msg, MagicMock(), flow)

    @pytest.mark.asyncio
    async def test_exact_batch_size(self, processor):
        """When entity count equals batch_size, exactly one output message."""
        entities = [
            _make_entity_context(f"E{i}", f"ctx {i}")
            for i in range(3)  # batch_size=3
        ]
        msg = _make_message(entities)

        mock_embed = AsyncMock(return_value=[[0.0]] * 3)
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(embed=mock_embed)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        mock_output.send.assert_called_once()
        assert len(mock_output.send.call_args[0][0].entities) == 3
