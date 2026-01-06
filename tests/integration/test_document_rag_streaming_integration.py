"""
Integration tests for DocumentRAG streaming functionality

These tests verify the streaming behavior of DocumentRAG, testing token-by-token
response delivery through the complete pipeline.
"""

import pytest
from unittest.mock import AsyncMock
from trustgraph.retrieval.document_rag.document_rag import DocumentRag
from tests.utils.streaming_assertions import (
    assert_streaming_chunks_valid,
    assert_callback_invoked,
)


@pytest.mark.integration
class TestDocumentRagStreaming:
    """Integration tests for DocumentRAG streaming"""

    @pytest.fixture
    def mock_embeddings_client(self):
        """Mock embeddings client"""
        client = AsyncMock()
        client.embed.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        return client

    @pytest.fixture
    def mock_doc_embeddings_client(self):
        """Mock document embeddings client"""
        client = AsyncMock()
        client.query.return_value = [
            "Machine learning is a subset of AI.",
            "Deep learning uses neural networks.",
            "Supervised learning needs labeled data."
        ]
        return client

    @pytest.fixture
    def mock_streaming_prompt_client(self, mock_streaming_llm_response):
        """Mock prompt client with streaming support"""
        client = AsyncMock()

        async def document_prompt_side_effect(query, documents, timeout=600, streaming=False, chunk_callback=None):
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

        client.document_prompt.side_effect = document_prompt_side_effect
        return client

    @pytest.fixture
    def document_rag_streaming(self, mock_embeddings_client, mock_doc_embeddings_client,
                                mock_streaming_prompt_client):
        """Create DocumentRag instance with streaming support"""
        return DocumentRag(
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            prompt_client=mock_streaming_prompt_client,
            verbose=True
        )

    @pytest.mark.asyncio
    async def test_document_rag_streaming_basic(self, document_rag_streaming, streaming_chunk_collector):
        """Test basic DocumentRAG streaming functionality"""
        # Arrange
        query = "What is machine learning?"
        collector = streaming_chunk_collector()

        # Act
        result = await document_rag_streaming.query(
            query=query,
            user="test_user",
            collection="test_collection",
            doc_limit=10,
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
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_document_rag_streaming_vs_non_streaming(self, document_rag_streaming):
        """Test that streaming and non-streaming produce equivalent results"""
        # Arrange
        query = "What is machine learning?"
        user = "test_user"
        collection = "test_collection"
        doc_limit = 10

        # Act - Non-streaming
        non_streaming_result = await document_rag_streaming.query(
            query=query,
            user=user,
            collection=collection,
            doc_limit=doc_limit,
            streaming=False
        )

        # Act - Streaming
        streaming_chunks = []

        async def collect(chunk):
            streaming_chunks.append(chunk)

        streaming_result = await document_rag_streaming.query(
            query=query,
            user=user,
            collection=collection,
            doc_limit=doc_limit,
            streaming=True,
            chunk_callback=collect
        )

        # Assert - Results should be equivalent
        assert streaming_result == non_streaming_result
        assert len(streaming_chunks) > 0
        assert "".join(streaming_chunks) == streaming_result

    @pytest.mark.asyncio
    async def test_document_rag_streaming_callback_invocation(self, document_rag_streaming):
        """Test that chunk callback is invoked correctly"""
        # Arrange
        callback = AsyncMock()

        # Act
        result = await document_rag_streaming.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            doc_limit=5,
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
    async def test_document_rag_streaming_without_callback(self, document_rag_streaming):
        """Test streaming parameter without callback (should fall back to non-streaming)"""
        # Arrange & Act
        result = await document_rag_streaming.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            doc_limit=5,
            streaming=True,
            chunk_callback=None  # No callback provided
        )

        # Assert - Should complete without error
        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_document_rag_streaming_with_no_documents(self, document_rag_streaming,
                                                             mock_doc_embeddings_client):
        """Test streaming with no documents found"""
        # Arrange
        mock_doc_embeddings_client.query.return_value = []  # No documents
        callback = AsyncMock()

        # Act
        result = await document_rag_streaming.query(
            query="unknown topic",
            user="test_user",
            collection="test_collection",
            doc_limit=10,
            streaming=True,
            chunk_callback=callback
        )

        # Assert - Should still produce streamed response
        assert result is not None
        assert callback.call_count > 0

    @pytest.mark.asyncio
    async def test_document_rag_streaming_error_propagation(self, document_rag_streaming,
                                                              mock_embeddings_client):
        """Test that errors during streaming are properly propagated"""
        # Arrange
        mock_embeddings_client.embed.side_effect = Exception("Embeddings error")
        callback = AsyncMock()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await document_rag_streaming.query(
                query="test query",
                user="test_user",
                collection="test_collection",
                doc_limit=5,
                streaming=True,
                chunk_callback=callback
            )

        assert "Embeddings error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_document_rag_streaming_with_different_doc_limits(self, document_rag_streaming,
                                                                      mock_doc_embeddings_client):
        """Test streaming with various document limits"""
        # Arrange
        callback = AsyncMock()
        doc_limits = [1, 5, 10, 20]

        for limit in doc_limits:
            # Reset mocks
            mock_doc_embeddings_client.reset_mock()
            callback.reset_mock()

            # Act
            result = await document_rag_streaming.query(
                query="test query",
                user="test_user",
                collection="test_collection",
                doc_limit=limit,
                streaming=True,
                chunk_callback=callback
            )

            # Assert
            assert result is not None
            assert callback.call_count > 0

            # Verify doc_limit was passed correctly
            call_args = mock_doc_embeddings_client.query.call_args
            assert call_args.kwargs['limit'] == limit

    @pytest.mark.asyncio
    async def test_document_rag_streaming_preserves_user_collection(self, document_rag_streaming,
                                                                      mock_doc_embeddings_client):
        """Test that streaming preserves user/collection isolation"""
        # Arrange
        callback = AsyncMock()
        user = "test_user_123"
        collection = "test_collection_456"

        # Act
        await document_rag_streaming.query(
            query="test query",
            user=user,
            collection=collection,
            doc_limit=10,
            streaming=True,
            chunk_callback=callback
        )

        # Assert - Verify user/collection were passed to document embeddings client
        call_args = mock_doc_embeddings_client.query.call_args
        assert call_args.kwargs['user'] == user
        assert call_args.kwargs['collection'] == collection
