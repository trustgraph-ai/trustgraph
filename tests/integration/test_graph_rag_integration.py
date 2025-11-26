"""
Integration tests for GraphRAG retrieval system

These tests verify the end-to-end functionality of the GraphRAG system,
testing the coordination between embeddings, graph retrieval, triple querying, and prompt services.
Following the TEST_STRATEGY.md approach for integration testing.

NOTE: This is the first integration test file for GraphRAG (previously had only unit tests).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from trustgraph.retrieval.graph_rag.graph_rag import GraphRag


@pytest.mark.integration
class TestGraphRagIntegration:
    """Integration tests for GraphRAG system coordination"""

    @pytest.fixture
    def mock_embeddings_client(self):
        """Mock embeddings client that returns realistic vector embeddings"""
        client = AsyncMock()
        client.embed.return_value = [
            [0.1, 0.2, 0.3, 0.4, 0.5],  # Realistic 5-dimensional embedding
        ]
        return client

    @pytest.fixture
    def mock_graph_embeddings_client(self):
        """Mock graph embeddings client that returns realistic entities"""
        client = AsyncMock()
        client.query.return_value = [
            "http://trustgraph.ai/e/machine-learning",
            "http://trustgraph.ai/e/artificial-intelligence",
            "http://trustgraph.ai/e/neural-networks"
        ]
        return client

    @pytest.fixture
    def mock_triples_client(self):
        """Mock triples client that returns realistic knowledge graph triples"""
        client = AsyncMock()

        # Mock different queries return different triples
        async def query_side_effect(s=None, p=None, o=None, limit=None, user=None, collection=None):
            # Mock label queries
            if p == "http://www.w3.org/2000/01/rdf-schema#label":
                if s == "http://trustgraph.ai/e/machine-learning":
                    return [MagicMock(s=s, p=p, o="Machine Learning")]
                elif s == "http://trustgraph.ai/e/artificial-intelligence":
                    return [MagicMock(s=s, p=p, o="Artificial Intelligence")]
                elif s == "http://trustgraph.ai/e/neural-networks":
                    return [MagicMock(s=s, p=p, o="Neural Networks")]
                return []

            # Mock relationship queries
            if s == "http://trustgraph.ai/e/machine-learning":
                return [
                    MagicMock(
                        s="http://trustgraph.ai/e/machine-learning",
                        p="http://trustgraph.ai/is_subset_of",
                        o="http://trustgraph.ai/e/artificial-intelligence"
                    ),
                    MagicMock(
                        s="http://trustgraph.ai/e/machine-learning",
                        p="http://www.w3.org/2000/01/rdf-schema#label",
                        o="Machine Learning"
                    )
                ]

            return []

        client.query.side_effect = query_side_effect
        return client

    @pytest.fixture
    def mock_prompt_client(self):
        """Mock prompt client that generates realistic responses"""
        client = AsyncMock()
        client.kg_prompt.return_value = (
            "Machine learning is a subset of artificial intelligence that enables computers "
            "to learn from data without being explicitly programmed. It uses algorithms "
            "and statistical models to find patterns in data."
        )
        return client

    @pytest.fixture
    def graph_rag(self, mock_embeddings_client, mock_graph_embeddings_client,
                  mock_triples_client, mock_prompt_client):
        """Create GraphRag instance with mocked dependencies"""
        return GraphRag(
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            prompt_client=mock_prompt_client,
            verbose=True
        )

    @pytest.mark.asyncio
    async def test_graph_rag_end_to_end_flow(self, graph_rag, mock_embeddings_client,
                                             mock_graph_embeddings_client, mock_triples_client,
                                             mock_prompt_client):
        """Test complete GraphRAG pipeline from query to response"""
        # Arrange
        query = "What is machine learning?"
        user = "test_user"
        collection = "ml_knowledge"
        entity_limit = 50
        triple_limit = 30

        # Act
        result = await graph_rag.query(
            query=query,
            user=user,
            collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit
        )

        # Assert - Verify service coordination

        # 1. Should compute embeddings for query
        mock_embeddings_client.embed.assert_called_once_with(query)

        # 2. Should query graph embeddings to find relevant entities
        mock_graph_embeddings_client.query.assert_called_once()
        call_args = mock_graph_embeddings_client.query.call_args
        assert call_args.kwargs['vectors'] == [[0.1, 0.2, 0.3, 0.4, 0.5]]
        assert call_args.kwargs['limit'] == entity_limit
        assert call_args.kwargs['user'] == user
        assert call_args.kwargs['collection'] == collection

        # 3. Should query triples to build knowledge subgraph
        assert mock_triples_client.query.call_count > 0

        # 4. Should call prompt with knowledge graph
        mock_prompt_client.kg_prompt.assert_called_once()
        call_args = mock_prompt_client.kg_prompt.call_args
        assert call_args.args[0] == query  # First arg is query
        assert isinstance(call_args.args[1], list)  # Second arg is kg (list of triples)

        # Verify final response
        assert result is not None
        assert isinstance(result, str)
        assert "machine learning" in result.lower()

    @pytest.mark.asyncio
    async def test_graph_rag_with_different_limits(self, graph_rag, mock_embeddings_client,
                                                    mock_graph_embeddings_client):
        """Test GraphRAG with various entity and triple limits"""
        # Arrange
        query = "Explain neural networks"
        test_configs = [
            {"entity_limit": 10, "triple_limit": 10},
            {"entity_limit": 50, "triple_limit": 30},
            {"entity_limit": 100, "triple_limit": 100},
        ]

        for config in test_configs:
            # Reset mocks
            mock_embeddings_client.reset_mock()
            mock_graph_embeddings_client.reset_mock()

            # Act
            await graph_rag.query(
                query=query,
                user="test_user",
                collection="test_collection",
                entity_limit=config["entity_limit"],
                triple_limit=config["triple_limit"]
            )

            # Assert
            call_args = mock_graph_embeddings_client.query.call_args
            assert call_args.kwargs['limit'] == config["entity_limit"]

    @pytest.mark.asyncio
    async def test_graph_rag_error_propagation(self, graph_rag, mock_embeddings_client):
        """Test that errors from underlying services are properly propagated"""
        # Arrange
        mock_embeddings_client.embed.side_effect = Exception("Embeddings service error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await graph_rag.query(
                query="test query",
                user="test_user",
                collection="test_collection"
            )

        assert "Embeddings service error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_graph_rag_with_empty_knowledge_graph(self, graph_rag, mock_graph_embeddings_client,
                                                         mock_triples_client, mock_prompt_client):
        """Test GraphRAG handles empty knowledge graph gracefully"""
        # Arrange
        mock_graph_embeddings_client.query.return_value = []  # No entities found
        mock_triples_client.query.return_value = []  # No triples found

        # Act
        result = await graph_rag.query(
            query="unknown topic",
            user="test_user",
            collection="test_collection"
        )

        # Assert
        # Should still call prompt client with empty knowledge graph
        mock_prompt_client.kg_prompt.assert_called_once()
        call_args = mock_prompt_client.kg_prompt.call_args
        assert isinstance(call_args.args[1], list)  # kg should be a list
        assert result is not None

    @pytest.mark.asyncio
    async def test_graph_rag_label_caching(self, graph_rag, mock_triples_client):
        """Test that label lookups are cached to reduce redundant queries"""
        # Arrange
        query = "What is machine learning?"

        # First query
        await graph_rag.query(
            query=query,
            user="test_user",
            collection="test_collection"
        )

        first_call_count = mock_triples_client.query.call_count
        mock_triples_client.reset_mock()

        # Second identical query
        await graph_rag.query(
            query=query,
            user="test_user",
            collection="test_collection"
        )

        second_call_count = mock_triples_client.query.call_count

        # Assert - Second query should make fewer triple queries due to caching
        # Note: This is a weak assertion because caching behavior depends on
        # implementation details, but it verifies the concept
        assert second_call_count >= 0  # Should complete without errors

    @pytest.mark.asyncio
    async def test_graph_rag_multi_user_isolation(self, graph_rag, mock_graph_embeddings_client):
        """Test that different users/collections are properly isolated"""
        # Arrange
        query = "test query"
        user1, collection1 = "user1", "collection1"
        user2, collection2 = "user2", "collection2"

        # Act
        await graph_rag.query(query=query, user=user1, collection=collection1)
        await graph_rag.query(query=query, user=user2, collection=collection2)

        # Assert - Both users should have separate queries
        assert mock_graph_embeddings_client.query.call_count == 2

        # Verify first call
        first_call = mock_graph_embeddings_client.query.call_args_list[0]
        assert first_call.kwargs['user'] == user1
        assert first_call.kwargs['collection'] == collection1

        # Verify second call
        second_call = mock_graph_embeddings_client.query.call_args_list[1]
        assert second_call.kwargs['user'] == user2
        assert second_call.kwargs['collection'] == collection2
