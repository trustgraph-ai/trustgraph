"""
Integration tests for GraphRAG retrieval system

These tests verify the end-to-end functionality of the GraphRAG system,
testing the coordination between concept extraction, knowledge retrieval,
triple querying, and prompt services.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from trustgraph.retrieval.graph_rag.graph_rag import GraphRag
from trustgraph.schema import KnowledgeRetrievalResponse, RetrievedEdge
from trustgraph.base import PromptResult


@pytest.mark.integration
class TestGraphRagIntegration:
    """Integration tests for GraphRAG system coordination"""

    @pytest.fixture
    def mock_concept_extraction_client(self):
        """Mock concept extraction client that returns realistic concepts"""
        client = AsyncMock()
        client.extract.return_value = [
            "machine learning", "artificial intelligence",
        ]
        return client

    @pytest.fixture
    def mock_knowledge_retrieval_client(self):
        """Mock knowledge retrieval client that returns realistic edges"""
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
            seed_entities=[
                "http://trustgraph.ai/e/machine-learning",
                "http://trustgraph.ai/e/artificial-intelligence",
            ],
        )
        return client

    @pytest.fixture
    def mock_triples_client(self):
        """Mock triples client for document tracing"""
        client = AsyncMock()
        client.query.return_value = []
        return client

    @pytest.fixture
    def mock_prompt_client(self):
        """Mock prompt client that generates realistic synthesis responses"""
        client = AsyncMock()

        async def mock_prompt(prompt_name, variables=None, streaming=False, chunk_callback=None):
            if prompt_name == "kg-synthesis":
                return PromptResult(
                    response_type="text",
                    text=(
                        "Machine learning is a subset of artificial intelligence that enables computers "
                        "to learn from data without being explicitly programmed. It uses algorithms "
                        "and statistical models to find patterns in data."
                    )
                )
            return PromptResult(response_type="text", text="")

        client.prompt.side_effect = mock_prompt
        return client

    @pytest.fixture
    def graph_rag(self, mock_concept_extraction_client,
                  mock_knowledge_retrieval_client,
                  mock_triples_client, mock_prompt_client):
        """Create GraphRag instance with mocked dependencies"""
        return GraphRag(
            concept_extraction_client=mock_concept_extraction_client,
            knowledge_retrieval_client=mock_knowledge_retrieval_client,
            triples_client=mock_triples_client,
            prompt_client=mock_prompt_client,
            verbose=True
        )

    @pytest.mark.asyncio
    async def test_graph_rag_end_to_end_flow(self, graph_rag,
                                             mock_concept_extraction_client,
                                             mock_knowledge_retrieval_client,
                                             mock_triples_client,
                                             mock_prompt_client):
        """Test complete GraphRAG pipeline from query to response with real-time provenance"""
        # Arrange
        query = "What is machine learning?"
        collection = "ml_knowledge"
        entity_limit = 50
        triple_limit = 30

        provenance_events = []

        async def collect_provenance(triples, prov_id):
            provenance_events.append((triples, prov_id))

        # Act
        response = await graph_rag.query(
            query=query,
            collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            explain_callback=collect_provenance
        )

        # Assert - Verify service coordination

        # 1. Should extract concepts from the query
        mock_concept_extraction_client.extract.assert_called_once_with(
            query, timeout=300,
        )

        # 2. Should retrieve knowledge using extracted concepts
        mock_knowledge_retrieval_client.retrieve.assert_called_once()
        call_args = mock_knowledge_retrieval_client.retrieve.call_args
        assert call_args.kwargs['concepts'] == [
            "machine learning", "artificial intelligence",
        ]
        assert call_args.kwargs['entity_limit'] == entity_limit
        assert call_args.kwargs['triple_limit'] == triple_limit

        # 3. Should call prompt once (kg-synthesis only)
        assert mock_prompt_client.prompt.call_count == 1

        # Verify final response
        response, usage, sources = response
        assert response is not None
        assert isinstance(response, str)
        assert "machine learning" in response.lower()

        # Verify provenance was emitted in real-time
        # (5 events: question, grounding, exploration, focus, synthesis)
        assert len(provenance_events) == 5
        for triples, prov_id in provenance_events:
            assert isinstance(triples, list)
            assert prov_id.startswith("urn:trustgraph:")

    @pytest.mark.asyncio
    async def test_graph_rag_with_different_limits(self, graph_rag,
                                                    mock_knowledge_retrieval_client):
        """Test GraphRAG with various entity and triple limits"""
        # Arrange
        query = "Explain neural networks"
        test_configs = [
            {"entity_limit": 10, "triple_limit": 10},
            {"entity_limit": 50, "triple_limit": 30},
            {"entity_limit": 100, "triple_limit": 100},
        ]

        for config in test_configs:
            mock_knowledge_retrieval_client.reset_mock()
            mock_knowledge_retrieval_client.retrieve.return_value = (
                KnowledgeRetrievalResponse(edges=[], seed_entities=[])
            )

            # Act
            await graph_rag.query(
                query=query,
                collection="test_collection",
                entity_limit=config["entity_limit"],
                triple_limit=config["triple_limit"]
            )

            # Assert
            call_args = mock_knowledge_retrieval_client.retrieve.call_args
            assert call_args.kwargs['entity_limit'] == config["entity_limit"]
            assert call_args.kwargs['triple_limit'] == config["triple_limit"]

    @pytest.mark.asyncio
    async def test_graph_rag_error_propagation(self, graph_rag,
                                               mock_concept_extraction_client):
        """Test that errors from underlying services are properly propagated"""
        # Arrange
        mock_concept_extraction_client.extract.side_effect = Exception(
            "Concept extraction service error"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await graph_rag.query(
                query="test query",
                collection="test_collection"
            )

        assert "Concept extraction service error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_graph_rag_with_empty_knowledge_graph(self, graph_rag,
                                                         mock_knowledge_retrieval_client,
                                                         mock_prompt_client):
        """Test GraphRAG handles empty knowledge graph gracefully"""
        # Arrange
        mock_knowledge_retrieval_client.retrieve.return_value = (
            KnowledgeRetrievalResponse(edges=[], seed_entities=[])
        )

        provenance_events = []

        async def collect_provenance(triples, prov_id):
            provenance_events.append((triples, prov_id))

        # Act
        response = await graph_rag.query(
            query="unknown topic",
            collection="test_collection",
            explain_callback=collect_provenance
        )

        # Assert
        assert response is not None
        # Provenance should still be emitted (5 events)
        assert len(provenance_events) == 5

    @pytest.mark.asyncio
    async def test_graph_rag_document_tracing(self, graph_rag,
                                              mock_triples_client):
        """Test that document tracing queries are made for retrieved edges"""
        # Arrange
        query = "What is machine learning?"

        # Act
        await graph_rag.query(
            query=query,
            collection="test_collection"
        )

        # Assert - triples_client.query should be called for document tracing
        assert mock_triples_client.query.call_count > 0

    @pytest.mark.asyncio
    async def test_graph_rag_multi_collection_isolation(self, graph_rag,
                                                        mock_triples_client):
        """Test that different collections propagate through to document tracing.

        Workspace isolation is enforced by flow.workspace at the service
        boundary — not by parameters on GraphRag.query — so this test
        verifies collection routing only.
        """
        # Arrange
        query = "test query"
        collection1 = "collection1"
        collection2 = "collection2"

        # Act
        await graph_rag.query(query=query, collection=collection1)
        await graph_rag.query(query=query, collection=collection2)

        # Assert - Each call should propagate its collection to triples queries
        collections_seen = set()
        for c in mock_triples_client.query.call_args_list:
            if 'collection' in c.kwargs:
                collections_seen.add(c.kwargs['collection'])

        assert collection1 in collections_seen
        assert collection2 in collections_seen
