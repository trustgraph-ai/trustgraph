"""
Integration tests for DocumentRAG retrieval system

These tests verify the end-to-end functionality of the DocumentRAG system,
testing the coordination between embeddings, document retrieval, and prompt services.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from testcontainers.compose import DockerCompose
from trustgraph.retrieval.document_rag.document_rag import DocumentRag


@pytest.mark.integration
class TestDocumentRagIntegration:
    """Integration tests for DocumentRAG system coordination"""

    @pytest.fixture
    def mock_embeddings_client(self):
        """Mock embeddings client that returns realistic vector embeddings"""
        client = AsyncMock()
        client.embed.return_value = [
            [0.1, 0.2, 0.3, 0.4, 0.5],  # Realistic 5-dimensional embedding
            [0.6, 0.7, 0.8, 0.9, 1.0]   # Second embedding for testing
        ]
        return client

    @pytest.fixture
    def mock_doc_embeddings_client(self):
        """Mock document embeddings client that returns realistic document chunks"""
        client = AsyncMock()
        client.query.return_value = [
            "Machine learning is a subset of artificial intelligence that focuses on algorithms that learn from data.",
            "Deep learning uses neural networks with multiple layers to model complex patterns in data.",
            "Supervised learning algorithms learn from labeled training data to make predictions on new data."
        ]
        return client

    @pytest.fixture
    def mock_prompt_client(self):
        """Mock prompt client that generates realistic responses"""
        client = AsyncMock()
        client.document_prompt.return_value = (
            "Machine learning is a field of artificial intelligence that enables computers to learn "
            "and improve from experience without being explicitly programmed. It uses algorithms "
            "to find patterns in data and make predictions or decisions."
        )
        return client

    @pytest.fixture
    def document_rag(self, mock_embeddings_client, mock_doc_embeddings_client, mock_prompt_client):
        """Create DocumentRag instance with mocked dependencies"""
        return DocumentRag(
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            prompt_client=mock_prompt_client,
            verbose=True
        )

    @pytest.mark.asyncio
    async def test_document_rag_end_to_end_flow(self, document_rag, mock_embeddings_client, 
                                                mock_doc_embeddings_client, mock_prompt_client):
        """Test complete DocumentRAG pipeline from query to response"""
        # Arrange
        query = "What is machine learning?"
        user = "test_user"
        collection = "ml_knowledge"
        doc_limit = 10

        # Act
        result = await document_rag.query(
            query=query,
            user=user,
            collection=collection,
            doc_limit=doc_limit
        )

        # Assert - Verify service coordination
        mock_embeddings_client.embed.assert_called_once_with(query)
        
        mock_doc_embeddings_client.query.assert_called_once_with(
            [[0.1, 0.2, 0.3, 0.4, 0.5], [0.6, 0.7, 0.8, 0.9, 1.0]],
            limit=doc_limit,
            user=user,
            collection=collection
        )
        
        mock_prompt_client.document_prompt.assert_called_once_with(
            query=query,
            documents=[
                "Machine learning is a subset of artificial intelligence that focuses on algorithms that learn from data.",
                "Deep learning uses neural networks with multiple layers to model complex patterns in data.",
                "Supervised learning algorithms learn from labeled training data to make predictions on new data."
            ]
        )

        # Verify final response
        assert result is not None
        assert isinstance(result, str)
        assert "machine learning" in result.lower()
        assert "artificial intelligence" in result.lower()

    @pytest.mark.asyncio
    async def test_document_rag_with_no_documents_found(self, mock_embeddings_client, 
                                                        mock_doc_embeddings_client, mock_prompt_client):
        """Test DocumentRAG behavior when no documents are retrieved"""
        # Arrange
        mock_doc_embeddings_client.query.return_value = []  # No documents found
        mock_prompt_client.document_prompt.return_value = "I couldn't find any relevant documents for your query."
        
        document_rag = DocumentRag(
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            prompt_client=mock_prompt_client,
            verbose=False
        )

        # Act
        result = await document_rag.query("very obscure query")

        # Assert
        mock_embeddings_client.embed.assert_called_once()
        mock_doc_embeddings_client.query.assert_called_once()
        mock_prompt_client.document_prompt.assert_called_once_with(
            query="very obscure query",
            documents=[]
        )
        
        assert result == "I couldn't find any relevant documents for your query."

    @pytest.mark.asyncio
    async def test_document_rag_embeddings_service_failure(self, mock_embeddings_client, 
                                                          mock_doc_embeddings_client, mock_prompt_client):
        """Test DocumentRAG error handling when embeddings service fails"""
        # Arrange
        mock_embeddings_client.embed.side_effect = Exception("Embeddings service unavailable")
        
        document_rag = DocumentRag(
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            prompt_client=mock_prompt_client,
            verbose=False
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await document_rag.query("test query")
        
        assert "Embeddings service unavailable" in str(exc_info.value)
        mock_embeddings_client.embed.assert_called_once()
        mock_doc_embeddings_client.query.assert_not_called()
        mock_prompt_client.document_prompt.assert_not_called()

    @pytest.mark.asyncio
    async def test_document_rag_document_service_failure(self, mock_embeddings_client, 
                                                        mock_doc_embeddings_client, mock_prompt_client):
        """Test DocumentRAG error handling when document service fails"""
        # Arrange
        mock_doc_embeddings_client.query.side_effect = Exception("Document service connection failed")
        
        document_rag = DocumentRag(
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            prompt_client=mock_prompt_client,
            verbose=False
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await document_rag.query("test query")
        
        assert "Document service connection failed" in str(exc_info.value)
        mock_embeddings_client.embed.assert_called_once()
        mock_doc_embeddings_client.query.assert_called_once()
        mock_prompt_client.document_prompt.assert_not_called()

    @pytest.mark.asyncio
    async def test_document_rag_prompt_service_failure(self, mock_embeddings_client, 
                                                      mock_doc_embeddings_client, mock_prompt_client):
        """Test DocumentRAG error handling when prompt service fails"""
        # Arrange
        mock_prompt_client.document_prompt.side_effect = Exception("LLM service rate limited")
        
        document_rag = DocumentRag(
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            prompt_client=mock_prompt_client,
            verbose=False
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await document_rag.query("test query")
        
        assert "LLM service rate limited" in str(exc_info.value)
        mock_embeddings_client.embed.assert_called_once()
        mock_doc_embeddings_client.query.assert_called_once()
        mock_prompt_client.document_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_document_rag_with_different_document_limits(self, document_rag, 
                                                              mock_doc_embeddings_client):
        """Test DocumentRAG with various document limit configurations"""
        # Test different document limits
        test_cases = [1, 5, 10, 25, 50]
        
        for limit in test_cases:
            # Reset mock call history
            mock_doc_embeddings_client.reset_mock()
            
            # Act
            await document_rag.query(f"query with limit {limit}", doc_limit=limit)
            
            # Assert
            mock_doc_embeddings_client.query.assert_called_once()
            call_args = mock_doc_embeddings_client.query.call_args
            assert call_args.kwargs['limit'] == limit

    @pytest.mark.asyncio
    async def test_document_rag_multi_user_isolation(self, document_rag, mock_doc_embeddings_client):
        """Test DocumentRAG properly isolates queries by user and collection"""
        # Arrange
        test_scenarios = [
            ("user1", "collection1"),
            ("user2", "collection2"),
            ("user1", "collection2"),  # Same user, different collection
            ("user2", "collection1"),  # Different user, same collection
        ]

        for user, collection in test_scenarios:
            # Reset mock call history
            mock_doc_embeddings_client.reset_mock()
            
            # Act
            await document_rag.query(
                f"query from {user} in {collection}",
                user=user,
                collection=collection
            )
            
            # Assert
            mock_doc_embeddings_client.query.assert_called_once()
            call_args = mock_doc_embeddings_client.query.call_args
            assert call_args.kwargs['user'] == user
            assert call_args.kwargs['collection'] == collection

    @pytest.mark.asyncio
    async def test_document_rag_verbose_logging(self, mock_embeddings_client, 
                                               mock_doc_embeddings_client, mock_prompt_client, 
                                               caplog):
        """Test DocumentRAG verbose logging functionality"""
        import logging
        
        # Arrange - Configure logging to capture debug messages
        caplog.set_level(logging.DEBUG)
        
        document_rag = DocumentRag(
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            prompt_client=mock_prompt_client,
            verbose=True
        )

        # Act
        await document_rag.query("test query for verbose logging")

        # Assert - Check for new logging messages
        log_messages = caplog.text
        assert "DocumentRag initialized" in log_messages
        assert "Constructing prompt..." in log_messages
        assert "Computing embeddings..." in log_messages
        assert "Getting documents..." in log_messages
        assert "Invoking LLM..." in log_messages
        assert "Query processing complete" in log_messages

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_document_rag_performance_with_large_document_set(self, document_rag, 
                                                                   mock_doc_embeddings_client):
        """Test DocumentRAG performance with large document retrieval"""
        # Arrange - Mock large document set (100 documents)
        large_doc_set = [f"Document {i} content about machine learning and AI" for i in range(100)]
        mock_doc_embeddings_client.query.return_value = large_doc_set

        # Act
        import time
        start_time = time.time()
        
        result = await document_rag.query("performance test query", doc_limit=100)
        
        end_time = time.time()
        execution_time = end_time - start_time

        # Assert
        assert result is not None
        assert execution_time < 5.0  # Should complete within 5 seconds
        mock_doc_embeddings_client.query.assert_called_once()
        call_args = mock_doc_embeddings_client.query.call_args
        assert call_args.kwargs['limit'] == 100

    @pytest.mark.asyncio
    async def test_document_rag_default_parameters(self, document_rag, mock_doc_embeddings_client):
        """Test DocumentRAG uses correct default parameters"""
        # Act
        await document_rag.query("test query with defaults")

        # Assert
        mock_doc_embeddings_client.query.assert_called_once()
        call_args = mock_doc_embeddings_client.query.call_args
        assert call_args.kwargs['user'] == "trustgraph"
        assert call_args.kwargs['collection'] == "default"
        assert call_args.kwargs['limit'] == 20