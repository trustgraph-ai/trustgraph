"""
Tests for document embeddings processor — single-chunk embedding via batch API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.embeddings.document_embeddings.embeddings import Processor
from trustgraph.schema import (
    Chunk, DocumentEmbeddings, ChunkEmbeddings,
    EmbeddingsRequest, EmbeddingsResponse, Metadata,
)


@pytest.fixture
def processor():
    return Processor(
        taskgroup=AsyncMock(),
        id="test-doc-embeddings",
    )


def _make_chunk_message(chunk_text="Hello world", doc_id="doc-1", collection="default"):
    metadata = Metadata(id=doc_id, collection=collection)
    value = Chunk(metadata=metadata, chunk=chunk_text, document_id=doc_id)
    msg = MagicMock()
    msg.value.return_value = value
    return msg


class TestDocumentEmbeddingsProcessor:

    @pytest.mark.asyncio
    async def test_sends_single_text_as_list(self, processor):
        """Document embeddings should wrap single chunk in a list for the API."""
        msg = _make_chunk_message("test chunk text")

        mock_request = AsyncMock(return_value=EmbeddingsResponse(
            error=None, vectors=[[0.1, 0.2, 0.3]]
        ))
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(request=mock_request)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        # Should send EmbeddingsRequest with texts=[chunk]
        mock_request.assert_called_once()
        req = mock_request.call_args[0][0]
        assert isinstance(req, EmbeddingsRequest)
        assert req.texts == ["test chunk text"]

    @pytest.mark.asyncio
    async def test_extracts_first_vector(self, processor):
        """Should use vectors[0] from the response."""
        msg = _make_chunk_message("chunk")

        mock_request = AsyncMock(return_value=EmbeddingsResponse(
            error=None, vectors=[[1.0, 2.0, 3.0]]
        ))
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(request=mock_request)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        result = mock_output.send.call_args[0][0]
        assert isinstance(result, DocumentEmbeddings)
        assert len(result.chunks) == 1
        assert result.chunks[0].vector == [1.0, 2.0, 3.0]

    @pytest.mark.asyncio
    async def test_empty_vectors_response(self, processor):
        """Should handle empty vectors response gracefully."""
        msg = _make_chunk_message("chunk")

        mock_request = AsyncMock(return_value=EmbeddingsResponse(
            error=None, vectors=[]
        ))
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(request=mock_request)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        result = mock_output.send.call_args[0][0]
        assert result.chunks[0].vector == []

    @pytest.mark.asyncio
    async def test_chunk_id_is_document_id(self, processor):
        """ChunkEmbeddings should use document_id as chunk_id."""
        msg = _make_chunk_message(doc_id="my-doc-42")

        mock_request = AsyncMock(return_value=EmbeddingsResponse(
            error=None, vectors=[[0.0]]
        ))
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(request=mock_request)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        result = mock_output.send.call_args[0][0]
        assert result.chunks[0].chunk_id == "my-doc-42"

    @pytest.mark.asyncio
    async def test_metadata_preserved(self, processor):
        """Output should carry the original metadata."""
        msg = _make_chunk_message(collection="reports", doc_id="d1")

        mock_request = AsyncMock(return_value=EmbeddingsResponse(
            error=None, vectors=[[0.0]]
        ))
        mock_output = AsyncMock()

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(request=mock_request)
            elif name == "output":
                return mock_output
            return MagicMock()

        await processor.on_message(msg, MagicMock(), flow)

        result = mock_output.send.call_args[0][0]
        assert result.metadata.collection == "reports"
        assert result.metadata.id == "d1"

    @pytest.mark.asyncio
    async def test_error_propagates(self, processor):
        """Embedding errors should propagate for retry."""
        msg = _make_chunk_message()

        mock_request = AsyncMock(side_effect=RuntimeError("service down"))

        def flow(name):
            if name == "embeddings-request":
                return MagicMock(request=mock_request)
            return MagicMock()

        with pytest.raises(RuntimeError, match="service down"):
            await processor.on_message(msg, MagicMock(), flow)
