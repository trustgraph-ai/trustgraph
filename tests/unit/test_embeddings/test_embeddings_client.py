"""
Tests for EmbeddingsClient — the client interface for batch embeddings.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.base.embeddings_client import EmbeddingsClient
from trustgraph.schema import EmbeddingsRequest, EmbeddingsResponse, Error


class TestEmbeddingsClient:

    @pytest.mark.asyncio
    async def test_embed_sends_request_and_returns_vectors(self):
        """embed() should send an EmbeddingsRequest and return vectors."""
        client = EmbeddingsClient.__new__(EmbeddingsClient)
        client.request = AsyncMock(return_value=EmbeddingsResponse(
            error=None,
            vectors=[[0.1, 0.2], [0.3, 0.4]],
        ))

        result = await client.embed(texts=["hello", "world"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        client.request.assert_called_once()
        req = client.request.call_args[0][0]
        assert isinstance(req, EmbeddingsRequest)
        assert req.texts == ["hello", "world"]

    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """embed() should work with a single text."""
        client = EmbeddingsClient.__new__(EmbeddingsClient)
        client.request = AsyncMock(return_value=EmbeddingsResponse(
            error=None,
            vectors=[[1.0, 2.0, 3.0]],
        ))

        result = await client.embed(texts=["single"])

        assert result == [[1.0, 2.0, 3.0]]

    @pytest.mark.asyncio
    async def test_embed_raises_on_error_response(self):
        """embed() should raise RuntimeError when response contains an error."""
        client = EmbeddingsClient.__new__(EmbeddingsClient)
        client.request = AsyncMock(return_value=EmbeddingsResponse(
            error=Error(type="embeddings-error", message="model not found"),
            vectors=[],
        ))

        with pytest.raises(RuntimeError, match="model not found"):
            await client.embed(texts=["test"])

    @pytest.mark.asyncio
    async def test_embed_passes_timeout(self):
        """embed() should pass timeout to the underlying request."""
        client = EmbeddingsClient.__new__(EmbeddingsClient)
        client.request = AsyncMock(return_value=EmbeddingsResponse(
            error=None, vectors=[[0.0]],
        ))

        await client.embed(texts=["test"], timeout=60)

        _, kwargs = client.request.call_args
        assert kwargs["timeout"] == 60

    @pytest.mark.asyncio
    async def test_embed_default_timeout(self):
        """embed() should use 300s default timeout."""
        client = EmbeddingsClient.__new__(EmbeddingsClient)
        client.request = AsyncMock(return_value=EmbeddingsResponse(
            error=None, vectors=[[0.0]],
        ))

        await client.embed(texts=["test"])

        _, kwargs = client.request.call_args
        assert kwargs["timeout"] == 300

    @pytest.mark.asyncio
    async def test_embed_empty_texts(self):
        """embed() with empty list should still make the request."""
        client = EmbeddingsClient.__new__(EmbeddingsClient)
        client.request = AsyncMock(return_value=EmbeddingsResponse(
            error=None, vectors=[],
        ))

        result = await client.embed(texts=[])

        assert result == []

    @pytest.mark.asyncio
    async def test_embed_large_batch(self):
        """embed() should handle large batches."""
        client = EmbeddingsClient.__new__(EmbeddingsClient)
        n = 100
        vectors = [[float(i)] for i in range(n)]
        client.request = AsyncMock(return_value=EmbeddingsResponse(
            error=None, vectors=vectors,
        ))

        texts = [f"text {i}" for i in range(n)]
        result = await client.embed(texts=texts)

        assert len(result) == n
        req = client.request.call_args[0][0]
        assert len(req.texts) == n
