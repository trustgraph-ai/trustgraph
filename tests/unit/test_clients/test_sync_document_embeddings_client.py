"""
Unit tests for trustgraph.clients.document_embeddings_client
Testing synchronous document embeddings client functionality
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.clients.document_embeddings_client import DocumentEmbeddingsClient
from trustgraph.schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse


class TestSyncDocumentEmbeddingsClient:
    """Test synchronous document embeddings client functionality"""

    @patch('trustgraph.clients.document_embeddings_client.BaseClient.__init__')
    def test_client_initialization(self, mock_base_init):
        """Test client initialization with correct parameters"""
        # Arrange
        mock_base_init.return_value = None
        
        # Act
        client = DocumentEmbeddingsClient(
            log_level=1,
            subscriber="test-subscriber",
            input_queue="test-input",
            output_queue="test-output",
            pulsar_host="pulsar://test:6650",
            pulsar_api_key="test-key"
        )
        
        # Assert
        mock_base_init.assert_called_once_with(
            log_level=1,
            subscriber="test-subscriber",
            input_queue="test-input",
            output_queue="test-output",
            pulsar_host="pulsar://test:6650",
            pulsar_api_key="test-key",
            input_schema=DocumentEmbeddingsRequest,
            output_schema=DocumentEmbeddingsResponse
        )

    @patch('trustgraph.clients.document_embeddings_client.BaseClient.__init__')
    def test_client_initialization_with_defaults(self, mock_base_init):
        """Test client initialization uses default queues when not specified"""
        # Arrange
        mock_base_init.return_value = None
        
        # Act
        client = DocumentEmbeddingsClient()
        
        # Assert
        call_args = mock_base_init.call_args[1]
        # Check that default queues are used
        assert call_args['input_queue'] is not None
        assert call_args['output_queue'] is not None
        assert call_args['input_schema'] == DocumentEmbeddingsRequest
        assert call_args['output_schema'] == DocumentEmbeddingsResponse

    @patch('trustgraph.clients.document_embeddings_client.BaseClient.__init__')
    def test_request_returns_chunks(self, mock_base_init):
        """Test request method returns chunks from response"""
        # Arrange
        mock_base_init.return_value = None
        client = DocumentEmbeddingsClient()
        
        # Mock the call method to return a response with chunks
        mock_response = MagicMock()
        mock_response.chunks = ["chunk1", "chunk2", "chunk3"]
        client.call = MagicMock(return_value=mock_response)
        
        vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        
        # Act
        result = client.request(
            vectors=vectors,
            user="test_user",
            collection="test_collection",
            limit=10,
            timeout=300
        )
        
        # Assert
        assert result == ["chunk1", "chunk2", "chunk3"]
        client.call.assert_called_once_with(
            user="test_user",
            collection="test_collection",
            vectors=vectors,
            limit=10,
            timeout=300
        )

    @patch('trustgraph.clients.document_embeddings_client.BaseClient.__init__')
    def test_request_with_default_parameters(self, mock_base_init):
        """Test request uses correct default parameters"""
        # Arrange
        mock_base_init.return_value = None
        client = DocumentEmbeddingsClient()
        
        mock_response = MagicMock()
        mock_response.chunks = ["test_chunk"]
        client.call = MagicMock(return_value=mock_response)
        
        vectors = [[0.1, 0.2, 0.3]]
        
        # Act
        result = client.request(vectors=vectors)
        
        # Assert
        assert result == ["test_chunk"]
        client.call.assert_called_once_with(
            user="trustgraph",
            collection="default",
            vectors=vectors,
            limit=10,
            timeout=300
        )

    @patch('trustgraph.clients.document_embeddings_client.BaseClient.__init__')
    def test_request_with_empty_chunks(self, mock_base_init):
        """Test request handles empty chunks list"""
        # Arrange
        mock_base_init.return_value = None
        client = DocumentEmbeddingsClient()
        
        mock_response = MagicMock()
        mock_response.chunks = []
        client.call = MagicMock(return_value=mock_response)
        
        # Act
        result = client.request(vectors=[[0.1, 0.2, 0.3]])
        
        # Assert
        assert result == []

    @patch('trustgraph.clients.document_embeddings_client.BaseClient.__init__')
    def test_request_with_none_chunks(self, mock_base_init):
        """Test request handles None chunks gracefully"""
        # Arrange
        mock_base_init.return_value = None
        client = DocumentEmbeddingsClient()
        
        mock_response = MagicMock()
        mock_response.chunks = None
        client.call = MagicMock(return_value=mock_response)
        
        # Act
        result = client.request(vectors=[[0.1, 0.2, 0.3]])
        
        # Assert
        assert result is None

    @patch('trustgraph.clients.document_embeddings_client.BaseClient.__init__')
    def test_request_with_custom_timeout(self, mock_base_init):
        """Test request passes custom timeout correctly"""
        # Arrange
        mock_base_init.return_value = None
        client = DocumentEmbeddingsClient()
        
        mock_response = MagicMock()
        mock_response.chunks = ["chunk1"]
        client.call = MagicMock(return_value=mock_response)
        
        # Act
        client.request(
            vectors=[[0.1, 0.2, 0.3]],
            timeout=600
        )
        
        # Assert
        assert client.call.call_args[1]["timeout"] == 600