"""
Integration tests for RAG service streaming protocol compliance.

These tests verify that RAG services correctly forward end_of_stream flags
and don't duplicate final chunks, ensuring proper streaming semantics.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call
from trustgraph.retrieval.graph_rag.graph_rag import GraphRag
from trustgraph.retrieval.document_rag.document_rag import DocumentRag


class TestGraphRagStreamingProtocol:
    """Integration tests for GraphRAG streaming protocol"""

    @pytest.fixture
    def mock_embeddings_client(self):
        """Mock embeddings client"""
        client = AsyncMock()
        client.embed.return_value = [[0.1, 0.2, 0.3]]
        return client

    @pytest.fixture
    def mock_graph_embeddings_client(self):
        """Mock graph embeddings client"""
        client = AsyncMock()
        client.query.return_value = ["entity1", "entity2"]
        return client

    @pytest.fixture
    def mock_triples_client(self):
        """Mock triples client"""
        client = AsyncMock()
        client.query.return_value = []
        return client

    @pytest.fixture
    def mock_streaming_prompt_client(self):
        """Mock prompt client that simulates realistic streaming with end_of_stream flags"""
        client = AsyncMock()

        async def kg_prompt_side_effect(query, kg, timeout=600, streaming=False, chunk_callback=None):
            if streaming and chunk_callback:
                # Simulate realistic streaming: chunks with end_of_stream=False, then final with end_of_stream=True
                await chunk_callback("The", False)
                await chunk_callback(" answer", False)
                await chunk_callback(" is here.", False)
                await chunk_callback("", True)  # Empty final chunk with end_of_stream=True
                return ""  # Return value not used since callback handles everything
            else:
                return "The answer is here."

        client.kg_prompt.side_effect = kg_prompt_side_effect
        return client

    @pytest.fixture
    def graph_rag(self, mock_embeddings_client, mock_graph_embeddings_client,
                  mock_triples_client, mock_streaming_prompt_client):
        """Create GraphRag instance with mocked dependencies"""
        return GraphRag(
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            prompt_client=mock_streaming_prompt_client,
            verbose=False
        )

    @pytest.mark.asyncio
    async def test_callback_receives_end_of_stream_parameter(self, graph_rag):
        """Test that callback receives end_of_stream parameter"""
        # Arrange
        callback = AsyncMock()

        # Act
        await graph_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=callback
        )

        # Assert - callback should receive (chunk, end_of_stream) signature
        assert callback.call_count == 4
        # All calls should have 2 arguments
        for call_args in callback.call_args_list:
            assert len(call_args.args) == 2, "Callback should receive (chunk, end_of_stream)"

    @pytest.mark.asyncio
    async def test_end_of_stream_flag_forwarded_correctly(self, graph_rag):
        """Test that end_of_stream flags are forwarded correctly"""
        # Arrange
        chunks_with_flags = []

        async def collect(chunk, end_of_stream):
            chunks_with_flags.append((chunk, end_of_stream))

        # Act
        await graph_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=collect
        )

        # Assert
        assert len(chunks_with_flags) == 4

        # First three chunks should have end_of_stream=False
        assert chunks_with_flags[0] == ("The", False)
        assert chunks_with_flags[1] == (" answer", False)
        assert chunks_with_flags[2] == (" is here.", False)

        # Final chunk should have end_of_stream=True
        assert chunks_with_flags[3] == ("", True)

    @pytest.mark.asyncio
    async def test_no_duplicate_final_chunk(self, graph_rag):
        """Test that final chunk is not duplicated"""
        # Arrange
        chunks = []

        async def collect(chunk, end_of_stream):
            chunks.append(chunk)

        # Act
        await graph_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=collect
        )

        # Assert - should have exactly 4 chunks, no duplicates
        assert len(chunks) == 4
        assert chunks == ["The", " answer", " is here.", ""]

        # The last chunk appears exactly once
        assert chunks.count("") == 1

    @pytest.mark.asyncio
    async def test_exactly_one_end_of_stream_true(self, graph_rag):
        """Test that exactly one message has end_of_stream=True"""
        # Arrange
        end_of_stream_flags = []

        async def collect(chunk, end_of_stream):
            end_of_stream_flags.append(end_of_stream)

        # Act
        await graph_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=collect
        )

        # Assert - exactly one True
        assert end_of_stream_flags.count(True) == 1
        assert end_of_stream_flags.count(False) == 3

    @pytest.mark.asyncio
    async def test_empty_final_chunk_preserved(self, graph_rag):
        """Test that empty final chunks are preserved and forwarded"""
        # Arrange
        final_chunk = None
        final_flag = None

        async def collect(chunk, end_of_stream):
            nonlocal final_chunk, final_flag
            if end_of_stream:
                final_chunk = chunk
                final_flag = end_of_stream

        # Act
        await graph_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=collect
        )

        # Assert
        assert final_flag is True
        assert final_chunk == "", "Empty final chunk should be preserved"


class TestDocumentRagStreamingProtocol:
    """Integration tests for DocumentRAG streaming protocol"""

    @pytest.fixture
    def mock_embeddings_client(self):
        """Mock embeddings client"""
        client = AsyncMock()
        client.embed.return_value = [[0.1, 0.2, 0.3]]
        return client

    @pytest.fixture
    def mock_doc_embeddings_client(self):
        """Mock document embeddings client"""
        client = AsyncMock()
        client.query.return_value = ["doc1", "doc2"]
        return client

    @pytest.fixture
    def mock_streaming_prompt_client(self):
        """Mock prompt client with streaming support"""
        client = AsyncMock()

        async def document_prompt_side_effect(query, documents, timeout=600, streaming=False, chunk_callback=None):
            if streaming and chunk_callback:
                # Simulate streaming with non-empty final chunk (some LLMs do this)
                await chunk_callback("Document", False)
                await chunk_callback(" summary", False)
                await chunk_callback(".", True)  # Non-empty final chunk
                return ""
            else:
                return "Document summary."

        client.document_prompt.side_effect = document_prompt_side_effect
        return client

    @pytest.fixture
    def document_rag(self, mock_embeddings_client, mock_doc_embeddings_client,
                     mock_streaming_prompt_client):
        """Create DocumentRag instance with mocked dependencies"""
        return DocumentRag(
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            prompt_client=mock_streaming_prompt_client,
            verbose=False
        )

    @pytest.mark.asyncio
    async def test_callback_receives_end_of_stream_parameter(self, document_rag):
        """Test that callback receives end_of_stream parameter"""
        # Arrange
        callback = AsyncMock()

        # Act
        await document_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=callback
        )

        # Assert
        assert callback.call_count == 3
        for call_args in callback.call_args_list:
            assert len(call_args.args) == 2

    @pytest.mark.asyncio
    async def test_non_empty_final_chunk_preserved(self, document_rag):
        """Test that non-empty final chunks are preserved with correct flag"""
        # Arrange
        chunks_with_flags = []

        async def collect(chunk, end_of_stream):
            chunks_with_flags.append((chunk, end_of_stream))

        # Act
        await document_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=collect
        )

        # Assert
        assert len(chunks_with_flags) == 3
        assert chunks_with_flags[0] == ("Document", False)
        assert chunks_with_flags[1] == (" summary", False)
        assert chunks_with_flags[2] == (".", True)  # Non-empty final chunk

    @pytest.mark.asyncio
    async def test_no_duplicate_final_chunk(self, document_rag):
        """Test that final chunk is not duplicated"""
        # Arrange
        chunks = []

        async def collect(chunk, end_of_stream):
            chunks.append(chunk)

        # Act
        await document_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            streaming=True,
            chunk_callback=collect
        )

        # Assert - final "." appears exactly once
        assert chunks.count(".") == 1
        assert chunks == ["Document", " summary", "."]


class TestStreamingProtocolEdgeCases:
    """Test edge cases in streaming protocol"""

    @pytest.mark.asyncio
    async def test_multiple_empty_chunks_before_final(self):
        """Test handling of multiple empty chunks (edge case)"""
        # Arrange
        client = AsyncMock()

        async def kg_prompt_with_empties(query, kg, timeout=600, streaming=False, chunk_callback=None):
            if streaming and chunk_callback:
                await chunk_callback("text", False)
                await chunk_callback("", False)  # Empty but not final
                await chunk_callback("more", False)
                await chunk_callback("", True)  # Empty and final
                return ""
            else:
                return "textmore"

        client.kg_prompt.side_effect = kg_prompt_with_empties

        rag = GraphRag(
            embeddings_client=AsyncMock(embed=AsyncMock(return_value=[[0.1]])),
            graph_embeddings_client=AsyncMock(query=AsyncMock(return_value=[])),
            triples_client=AsyncMock(query=AsyncMock(return_value=[])),
            prompt_client=client,
            verbose=False
        )

        chunks_with_flags = []

        async def collect(chunk, end_of_stream):
            chunks_with_flags.append((chunk, end_of_stream))

        # Act
        await rag.query(
            query="test",
            streaming=True,
            chunk_callback=collect
        )

        # Assert
        assert len(chunks_with_flags) == 4
        assert chunks_with_flags[-1] == ("", True)  # Final empty chunk
        end_of_stream_flags = [f for c, f in chunks_with_flags]
        assert end_of_stream_flags.count(True) == 1
