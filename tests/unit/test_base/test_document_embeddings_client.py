"""
Unit tests for trustgraph.base.document_embeddings_client
Testing async document embeddings client functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.base.document_embeddings_client import DocumentEmbeddingsClient, DocumentEmbeddingsClientSpec
from trustgraph.schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse, Error


class TestDocumentEmbeddingsClient(IsolatedAsyncioTestCase):
    """Test async document embeddings client functionality"""

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_query_success_with_chunks(self, mock_parent_init):
        """Test successful query returning chunks"""
        # Arrange
        mock_parent_init.return_value = None
        client = DocumentEmbeddingsClient()
        mock_response = MagicMock(spec=DocumentEmbeddingsResponse)
        mock_response.error = None
        mock_response.chunks = ["chunk1", "chunk2", "chunk3"]
        
        # Mock the request method
        client.request = AsyncMock(return_value=mock_response)
        
        vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        
        # Act
        result = await client.query(
            vectors=vectors,
            limit=10,
            user="test_user",
            collection="test_collection",
            timeout=30
        )
        
        # Assert
        assert result == ["chunk1", "chunk2", "chunk3"]
        client.request.assert_called_once()
        call_args = client.request.call_args[0][0]
        assert isinstance(call_args, DocumentEmbeddingsRequest)
        assert call_args.vectors == vectors
        assert call_args.limit == 10
        assert call_args.user == "test_user"
        assert call_args.collection == "test_collection"

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_query_with_error_raises_exception(self, mock_parent_init):
        """Test query raises RuntimeError when response contains error"""
        # Arrange
        mock_parent_init.return_value = None
        client = DocumentEmbeddingsClient()
        mock_response = MagicMock(spec=DocumentEmbeddingsResponse)
        mock_response.error = MagicMock()
        mock_response.error.message = "Database connection failed"
        
        client.request = AsyncMock(return_value=mock_response)
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Database connection failed"):
            await client.query(
                vectors=[[0.1, 0.2, 0.3]],
                limit=5
            )

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_query_with_empty_chunks(self, mock_parent_init):
        """Test query with empty chunks list"""
        # Arrange
        mock_parent_init.return_value = None
        client = DocumentEmbeddingsClient()
        mock_response = MagicMock(spec=DocumentEmbeddingsResponse)
        mock_response.error = None
        mock_response.chunks = []
        
        client.request = AsyncMock(return_value=mock_response)
        
        # Act
        result = await client.query(vectors=[[0.1, 0.2, 0.3]])
        
        # Assert
        assert result == []

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_query_with_default_parameters(self, mock_parent_init):
        """Test query uses correct default parameters"""
        # Arrange
        mock_parent_init.return_value = None
        client = DocumentEmbeddingsClient()
        mock_response = MagicMock(spec=DocumentEmbeddingsResponse)
        mock_response.error = None
        mock_response.chunks = ["test_chunk"]
        
        client.request = AsyncMock(return_value=mock_response)
        
        # Act
        result = await client.query(vectors=[[0.1, 0.2, 0.3]])
        
        # Assert
        client.request.assert_called_once()
        call_args = client.request.call_args[0][0]
        assert call_args.limit == 20  # Default limit
        assert call_args.user == "trustgraph"  # Default user
        assert call_args.collection == "default"  # Default collection

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_query_with_custom_timeout(self, mock_parent_init):
        """Test query passes custom timeout to request"""
        # Arrange
        mock_parent_init.return_value = None
        client = DocumentEmbeddingsClient()
        mock_response = MagicMock(spec=DocumentEmbeddingsResponse)
        mock_response.error = None
        mock_response.chunks = ["chunk1"]
        
        client.request = AsyncMock(return_value=mock_response)
        
        # Act
        await client.query(
            vectors=[[0.1, 0.2, 0.3]],
            timeout=60
        )
        
        # Assert
        assert client.request.call_args[1]["timeout"] == 60

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_query_logging(self, mock_parent_init):
        """Test query logs response for debugging"""
        # Arrange
        mock_parent_init.return_value = None
        client = DocumentEmbeddingsClient()
        mock_response = MagicMock(spec=DocumentEmbeddingsResponse)
        mock_response.error = None
        mock_response.chunks = ["test_chunk"]
        
        client.request = AsyncMock(return_value=mock_response)
        
        # Act
        with patch('trustgraph.base.document_embeddings_client.logger') as mock_logger:
            result = await client.query(vectors=[[0.1, 0.2, 0.3]])
            
            # Assert
            mock_logger.debug.assert_called_once()
            assert "Document embeddings response" in str(mock_logger.debug.call_args)
            assert result == ["test_chunk"]


class TestDocumentEmbeddingsClientSpec(IsolatedAsyncioTestCase):
    """Test DocumentEmbeddingsClientSpec configuration"""

    def test_spec_initialization(self):
        """Test DocumentEmbeddingsClientSpec initialization"""
        # Act
        spec = DocumentEmbeddingsClientSpec(
            request_name="test-request",
            response_name="test-response"
        )
        
        # Assert
        assert spec.request_name == "test-request"
        assert spec.response_name == "test-response"
        assert spec.request_schema == DocumentEmbeddingsRequest
        assert spec.response_schema == DocumentEmbeddingsResponse
        assert spec.impl == DocumentEmbeddingsClient

    @patch('trustgraph.base.request_response_spec.RequestResponseSpec.__init__')
    def test_spec_calls_parent_init(self, mock_parent_init):
        """Test spec properly calls parent class initialization"""
        # Arrange
        mock_parent_init.return_value = None
        
        # Act
        spec = DocumentEmbeddingsClientSpec(
            request_name="test-request",
            response_name="test-response"
        )
        
        # Assert
        mock_parent_init.assert_called_once_with(
            request_name="test-request",
            request_schema=DocumentEmbeddingsRequest,
            response_name="test-response",
            response_schema=DocumentEmbeddingsResponse,
            impl=DocumentEmbeddingsClient
        )