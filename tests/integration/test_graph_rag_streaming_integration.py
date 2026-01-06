"""
Integration tests for GraphRAG streaming functionality

These tests verify the streaming behavior of GraphRAG, testing token-by-token
response delivery through the complete pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from trustgraph.retrieval.graph_rag.graph_rag import GraphRag
from tests.utils.streaming_assertions import (
    assert_streaming_chunks_valid,
    assert_rag_streaming_chunks,
    assert_streaming_content_matches,
    assert_callback_invoked,
)


@pytest.mark.integration
class TestGraphRagStreaming:
    """Integration tests for GraphRAG streaming"""

    @pytest.fixture
    def mock_embeddings_client(self):
        """Mock embeddings client"""
        client = AsyncMock()
        client.embed.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        return client

    @pytest.fixture
    def mock_graph_embeddings_client(self):
        """Mock graph embeddings client"""
        client = AsyncMock()
        client.query.return_value = [
            "http://trustgraph.ai/e/machine-learning",
        ]
        return client

    @pytest.fixture
    def mock_triples_client(self):
        """Mock triples client with minimal responses"""
        client = AsyncMock()

        async def query_side_effect(s=None, p=None, o=None, limit=None, user=None, collection=None):
            if p == "http://www.w3.org/2000/01/rdf-schema#label":
                return [MagicMock(s=s, p=p, o="Machine Learning")]
            return []

        client.query.side_effect = query_side_effect
        return client

    @pytest.fixture
    def mock_streaming_prompt_client(self, mock_streaming_llm_response):
        """Mock prompt client with streaming support"""
        client = AsyncMock()

        async def kg_prompt_side_effect(query, kg, timeout=600, streaming=False, chunk_callback=None):
            # Both modes return the same text
            full_text = "Machine learning is a subset of artificial intelligence that focuses on algorithms that learn from data."

            if streaming and chunk_callback:
                # Simulate streaming chunks with end_of_stream flags
                chunks = []
                async for chunk in mock_streaming_llm_response():
                    chunks.append(chunk)

                # Send all chunks with end_of_stream=False except the last
                for i, chunk in enumerate(chunks):
                    is_final = (i == len(chunks) - 1)
                    await chunk_callback(chunk, is_final)

                return full_text
            else:
                # Non-streaming response - same text
                return full_text

        client.kg_prompt.side_effect = kg_prompt_side_effect
        return client

    @pytest.fixture
    def graph_rag_streaming(self, mock_embeddings_client, mock_graph_embeddings_client,
                            mock_triples_client, mock_streaming_prompt_client):
        """Create GraphRag instance with streaming support"""
        return GraphRag(
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            prompt_client=mock_streaming_prompt_client,
            verbose=True
        )

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_basic(self, graph_rag_streaming, streaming_chunk_collector):
        """Test basic GraphRAG streaming functionality"""
        # Arrange
        query = "What is machine learning?"
        collector = streaming_chunk_collector()

        # Act
        result = await graph_rag_streaming.query(
            query=query,
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=collector.collect
        )

        # Assert
        assert_streaming_chunks_valid(collector.chunks, min_chunks=1)
        assert_callback_invoked(AsyncMock(call_count=len(collector.chunks)), min_calls=1)

        # Verify streaming protocol compliance
        collector.verify_streaming_protocol()

        # Verify full response matches concatenated chunks
        full_from_chunks = collector.get_full_text()
        assert result == full_from_chunks

        # Verify content is reasonable
        assert "machine" in result.lower() or "learning" in result.lower()

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_vs_non_streaming(self, graph_rag_streaming):
        """Test that streaming and non-streaming produce equivalent results"""
        # Arrange
        query = "What is machine learning?"
        user = "test_user"
        collection = "test_collection"

        # Act - Non-streaming
        non_streaming_result = await graph_rag_streaming.query(
            query=query,
            user=user,
            collection=collection,
            streaming=False
        )

        # Act - Streaming
        streaming_chunks = []

        async def collect(chunk, end_of_stream):
            streaming_chunks.append(chunk)

        streaming_result = await graph_rag_streaming.query(
            query=query,
            user=user,
            collection=collection,
            streaming=True,
            chunk_callback=collect
        )

        # Assert - Results should be equivalent
        assert streaming_result == non_streaming_result
        assert len(streaming_chunks) > 0
        assert "".join(streaming_chunks) == streaming_result

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_callback_invocation(self, graph_rag_streaming):
        """Test that chunk callback is invoked correctly"""
        # Arrange
        callback = AsyncMock()

        # Act
        result = await graph_rag_streaming.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=callback
        )

        # Assert
        assert callback.call_count > 0
        assert result is not None

        # Verify all callback invocations had string arguments
        for call in callback.call_args_list:
            assert isinstance(call.args[0], str)

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_without_callback(self, graph_rag_streaming):
        """Test streaming parameter without callback (should fall back to non-streaming)"""
        # Arrange & Act
        result = await graph_rag_streaming.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=None  # No callback provided
        )

        # Assert - Should complete without error
        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_with_empty_kg(self, graph_rag_streaming,
                                                      mock_graph_embeddings_client):
        """Test streaming with empty knowledge graph"""
        # Arrange
        mock_graph_embeddings_client.query.return_value = []  # No entities
        callback = AsyncMock()

        # Act
        result = await graph_rag_streaming.query(
            query="unknown topic",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=callback
        )

        # Assert - Should still produce streamed response
        assert result is not None
        assert callback.call_count > 0

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_error_propagation(self, graph_rag_streaming,
                                                          mock_embeddings_client):
        """Test that errors during streaming are properly propagated"""
        # Arrange
        mock_embeddings_client.embed.side_effect = Exception("Embeddings error")
        callback = AsyncMock()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await graph_rag_streaming.query(
                query="test query",
                user="test_user",
                collection="test_collection",
                streaming=True,
                chunk_callback=callback
            )

        assert "Embeddings error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_preserves_parameters(self, graph_rag_streaming,
                                                             mock_graph_embeddings_client):
        """Test that streaming preserves all query parameters"""
        # Arrange
        callback = AsyncMock()
        entity_limit = 25
        triple_limit = 15

        # Act
        await graph_rag_streaming.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            streaming=True,
            chunk_callback=callback
        )

        # Assert - Verify parameters were passed to underlying services
        call_args = mock_graph_embeddings_client.query.call_args
        assert call_args.kwargs['limit'] == entity_limit
