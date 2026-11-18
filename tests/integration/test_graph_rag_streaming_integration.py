"""
Integration tests for GraphRAG streaming functionality

These tests verify the streaming behavior of GraphRAG, testing token-by-token
response delivery through the complete pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from trustgraph.retrieval.graph_rag.graph_rag import GraphRag
from trustgraph.schema import KnowledgeRetrievalResponse, RetrievedEdge
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
    def mock_concept_extraction_client(self):
        """Mock concept extraction client"""
        client = AsyncMock()
        client.extract.return_value = ["machine learning"]
        return client

    @pytest.fixture
    def mock_knowledge_retrieval_client(self):
        """Mock knowledge retrieval client"""
        client = AsyncMock()
        client.retrieve.return_value = KnowledgeRetrievalResponse(
            edges=[
                RetrievedEdge(
                    s="http://trustgraph.ai/e/machine-learning",
                    p="http://trustgraph.ai/is_subset_of",
                    o="http://trustgraph.ai/e/artificial-intelligence",
                    s_label="Machine Learning",
                    p_label="is subset of",
                    o_label="Artificial Intelligence",
                    score=0.95,
                    concept="machine learning",
                ),
            ],
            seed_entities=["http://trustgraph.ai/e/machine-learning"],
        )
        return client

    @pytest.fixture
    def mock_triples_client(self):
        """Mock triples client for document tracing"""
        client = AsyncMock()
        client.query.return_value = []
        return client

    @pytest.fixture
    def mock_streaming_prompt_client(self, mock_streaming_llm_response):
        """Mock prompt client with streaming support"""
        client = AsyncMock()

        full_text = "Machine learning is a subset of artificial intelligence that focuses on algorithms that learn from data."

        async def prompt_side_effect(prompt_id, variables, streaming=False, chunk_callback=None, **kwargs):
            if prompt_id == "kg-synthesis":
                if streaming and chunk_callback:
                    chunks = []
                    async for chunk in mock_streaming_llm_response():
                        chunks.append(chunk)

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
    def graph_rag_streaming(self, mock_concept_extraction_client,
                            mock_knowledge_retrieval_client,
                            mock_triples_client,
                            mock_streaming_prompt_client):
        """Create GraphRag instance with streaming support"""
        return GraphRag(
            concept_extraction_client=mock_concept_extraction_client,
            knowledge_retrieval_client=mock_knowledge_retrieval_client,
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

        provenance_events = []

        async def collect_provenance(triples, prov_id):
            provenance_events.append((triples, prov_id))

        # Act
        response = await graph_rag_streaming.query(
            query=query,
            collection="test_collection",
            streaming=True,
            chunk_callback=collector.collect,
            explain_callback=collect_provenance
        )

        # Assert
        response, usage, sources = response
        assert_streaming_chunks_valid(collector.chunks, min_chunks=1)
        assert_callback_invoked(AsyncMock(call_count=len(collector.chunks)), min_calls=1)

        collector.verify_streaming_protocol()

        full_from_chunks = collector.get_full_text()
        assert response == full_from_chunks

        assert "machine" in response.lower() or "learning" in response.lower()

        # Verify provenance (5 events)
        assert len(provenance_events) == 5
        for triples, prov_id in provenance_events:
            assert prov_id.startswith("urn:trustgraph:")

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_vs_non_streaming(self, graph_rag_streaming):
        """Test that streaming and non-streaming produce equivalent results"""
        # Arrange
        query = "What is machine learning?"
        collection = "test_collection"

        # Act - Non-streaming
        non_streaming_response = await graph_rag_streaming.query(
            query=query,
            collection=collection,
            streaming=False
        )

        # Act - Streaming
        streaming_chunks = []

        async def collect(chunk, end_of_stream):
            streaming_chunks.append(chunk)

        streaming_response = await graph_rag_streaming.query(
            query=query,
            collection=collection,
            streaming=True,
            chunk_callback=collect
        )

        # Assert
        non_streaming_text, _, _ = non_streaming_response
        streaming_text, _, _ = streaming_response
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
            collection="test_collection",
            streaming=True,
            chunk_callback=callback
        )

        # Assert
        assert callback.call_count > 0
        assert response is not None

        for call in callback.call_args_list:
            assert isinstance(call.args[0], str)

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_without_callback(self, graph_rag_streaming):
        """Test streaming parameter without callback (should fall back to non-streaming)"""
        # Act
        response = await graph_rag_streaming.query(
            query="test query",
            collection="test_collection",
            streaming=True,
            chunk_callback=None
        )

        # Assert
        assert response is not None
        response_text, usage, sources = response
        assert isinstance(response_text, str)

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_with_empty_kg(self, graph_rag_streaming,
                                                      mock_knowledge_retrieval_client):
        """Test streaming with empty knowledge graph"""
        # Arrange
        mock_knowledge_retrieval_client.retrieve.return_value = (
            KnowledgeRetrievalResponse(edges=[], seed_entities=[])
        )
        callback = AsyncMock()

        # Act
        response = await graph_rag_streaming.query(
            query="unknown topic",
            collection="test_collection",
            streaming=True,
            chunk_callback=callback
        )

        # Assert
        assert response is not None
        assert callback.call_count > 0

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_error_propagation(self, graph_rag_streaming,
                                                          mock_concept_extraction_client):
        """Test that errors during streaming are properly propagated"""
        # Arrange
        mock_concept_extraction_client.extract.side_effect = Exception(
            "Concept extraction error"
        )
        callback = AsyncMock()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await graph_rag_streaming.query(
                query="test query",
                collection="test_collection",
                streaming=True,
                chunk_callback=callback
            )

        assert "Concept extraction error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_graph_rag_streaming_preserves_parameters(self, graph_rag_streaming,
                                                             mock_knowledge_retrieval_client):
        """Test that streaming preserves all query parameters"""
        # Arrange
        callback = AsyncMock()
        entity_limit = 25
        triple_limit = 15

        # Act
        await graph_rag_streaming.query(
            query="test query",
            collection="test_collection",
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            streaming=True,
            chunk_callback=callback
        )

        # Assert
        call_args = mock_knowledge_retrieval_client.retrieve.call_args
        assert call_args.kwargs['entity_limit'] == entity_limit
        assert call_args.kwargs['triple_limit'] == triple_limit
