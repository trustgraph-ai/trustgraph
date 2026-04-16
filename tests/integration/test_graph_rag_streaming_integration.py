"""
Integration tests for GraphRAG streaming functionality

These tests verify the streaming behavior of GraphRAG, testing token-by-token
response delivery through the complete pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from trustgraph.retrieval.graph_rag.graph_rag import GraphRag
from trustgraph.schema import EntityMatch, Term, IRI
from trustgraph.base import PromptResult
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
        # New batch format: [[[vectors_for_text1]]]
        client.embed.return_value = [[[0.1, 0.2, 0.3, 0.4, 0.5]]]
        return client

    @pytest.fixture
    def mock_graph_embeddings_client(self):
        """Mock graph embeddings client"""
        client = AsyncMock()
        client.query.return_value = [
            EntityMatch(entity=Term(type=IRI, iri="http://trustgraph.ai/e/machine-learning"), score=0.95),
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
        """Mock prompt client with streaming support for two-stage GraphRAG"""
        client = AsyncMock()

        # Full synthesis text
        full_text = "Machine learning is a subset of artificial intelligence that focuses on algorithms that learn from data."

        async def prompt_side_effect(prompt_id, variables, streaming=False, chunk_callback=None, **kwargs):
            if prompt_id == "extract-concepts":
                return PromptResult(response_type="text", text="")
            elif prompt_id == "kg-edge-scoring":
                # Edge scoring returns JSONL with IDs and scores
                return PromptResult(response_type="text", text='{"id": "abc12345", "score": 0.9}\n')
            elif prompt_id == "kg-edge-reasoning":
                return PromptResult(response_type="text", text='{"id": "abc12345", "reasoning": "Relevant to query"}\n')
            elif prompt_id == "kg-synthesis":
                if streaming and chunk_callback:
                    # Simulate streaming chunks with end_of_stream flags
                    chunks = []
                    async for chunk in mock_streaming_llm_response():
                        chunks.append(chunk)

                    # Send all chunks with end_of_stream=False except the last
                    for i, chunk in enumerate(chunks):
                        is_final = (i == len(chunks) - 1)
                        await chunk_callback(chunk, is_final)

                    return PromptResult(response_type="text", text=full_text)
                else:
                    return PromptResult(response_type="text", text=full_text)
            return PromptResult(response_type="text", text="")

        client.prompt.side_effect = prompt_side_effect
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
        """Test basic GraphRAG streaming functionality with real-time provenance"""
        # Arrange
        query = "What is machine learning?"
        collector = streaming_chunk_collector()

        # Collect provenance events
        provenance_events = []

        async def collect_provenance(triples, prov_id):
            provenance_events.append((triples, prov_id))

        # Act - query() returns response, provenance via callback
        response = await graph_rag_streaming.query(
            query=query,
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=collector.collect,
            explain_callback=collect_provenance
        )

        # Assert
        response, usage = response
        assert_streaming_chunks_valid(collector.chunks, min_chunks=1)
        assert_callback_invoked(AsyncMock(call_count=len(collector.chunks)), min_calls=1)

        # Verify streaming protocol compliance
        collector.verify_streaming_protocol()

        # Verify full response matches concatenated chunks
        full_from_chunks = collector.get_full_text()
        assert response == full_from_chunks

        # Verify content is reasonable
        assert "machine" in response.lower() or "learning" in response.lower()

        # Verify provenance was emitted in real-time (5 events: question, grounding, exploration, focus, synthesis)
        assert len(provenance_events) == 5
        for triples, prov_id in provenance_events:
            assert prov_id.startswith("urn:trustgraph:")

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_vs_non_streaming(self, graph_rag_streaming):
        """Test that streaming and non-streaming produce equivalent results"""
        # Arrange
        query = "What is machine learning?"
        user = "test_user"
        collection = "test_collection"

        # Act - Non-streaming
        non_streaming_response = await graph_rag_streaming.query(
            query=query,
            user=user,
            collection=collection,
            streaming=False
        )

        # Act - Streaming
        streaming_chunks = []

        async def collect(chunk, end_of_stream):
            streaming_chunks.append(chunk)

        streaming_response = await graph_rag_streaming.query(
            query=query,
            user=user,
            collection=collection,
            streaming=True,
            chunk_callback=collect
        )

        # Assert - Results should be equivalent
        non_streaming_text, _ = non_streaming_response
        streaming_text, _ = streaming_response
        assert streaming_text == non_streaming_text
        assert len(streaming_chunks) > 0
        assert "".join(streaming_chunks) == streaming_text

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_callback_invocation(self, graph_rag_streaming):
        """Test that chunk callback is invoked correctly"""
        # Arrange
        callback = AsyncMock()

        # Act
        response = await graph_rag_streaming.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=callback
        )

        # Assert
        assert callback.call_count > 0
        assert response is not None

        # Verify all callback invocations had string arguments
        for call in callback.call_args_list:
            assert isinstance(call.args[0], str)

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_without_callback(self, graph_rag_streaming):
        """Test streaming parameter without callback (should fall back to non-streaming)"""
        # Arrange & Act
        response = await graph_rag_streaming.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=None  # No callback provided
        )

        # Assert - Should complete without error
        assert response is not None
        response_text, usage = response
        assert isinstance(response_text, str)

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_with_empty_kg(self, graph_rag_streaming,
                                                      mock_graph_embeddings_client):
        """Test streaming with empty knowledge graph"""
        # Arrange
        mock_graph_embeddings_client.query.return_value = []  # No entities
        callback = AsyncMock()

        # Act
        response = await graph_rag_streaming.query(
            query="unknown topic",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=callback
        )

        # Assert - Should still produce streamed response
        assert response is not None
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
