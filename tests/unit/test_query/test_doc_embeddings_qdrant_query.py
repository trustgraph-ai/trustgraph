"""
Unit tests for trustgraph.query.doc_embeddings.qdrant.service
Testing document embeddings query functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.query.doc_embeddings.qdrant.service import Processor


class TestQdrantDocEmbeddingsQuery(IsolatedAsyncioTestCase):
    """Test Qdrant document embeddings query functionality"""

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_processor_initialization_basic(self, mock_base_init, mock_qdrant_client):
        """Test basic Qdrant processor initialization"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-query-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify base class initialization was called
        mock_base_init.assert_called_once()
        
        # Verify QdrantClient was created with correct parameters
        mock_qdrant_client.assert_called_once_with(url='http://localhost:6333', api_key='test-api-key')
        
        # Verify processor attributes
        assert hasattr(processor, 'qdrant')
        assert processor.qdrant == mock_qdrant_instance

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_base_init, mock_qdrant_client):
        """Test processor initialization with default values"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-doc-query-processor'
            # No store_uri or api_key provided - should use defaults
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify QdrantClient was created with default URI and None API key
        mock_qdrant_client.assert_called_once_with(url='http://localhost:6333', api_key=None)

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_single_vector(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings with single vector"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response
        mock_point1 = MagicMock()
        mock_point1.payload = {'doc': 'first document chunk'}
        mock_point2 = MagicMock()
        mock_point2.payload = {'doc': 'second document chunk'}
        
        mock_response = MagicMock()
        mock_response.points = [mock_point1, mock_point2]
        mock_qdrant_instance.query_points.return_value = mock_response
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2, 0.3]]
        mock_message.limit = 5
        mock_message.user = 'test_user'
        mock_message.collection = 'test_collection'
        
        # Act
        result = await processor.query_document_embeddings(mock_message)

        # Assert
        # Verify query was called with correct parameters
        expected_collection = 'd_test_user_test_collection_3'
        mock_qdrant_instance.query_points.assert_called_once_with(
            collection_name=expected_collection,
            query=[0.1, 0.2, 0.3],
            limit=5,  # Direct limit, no multiplication
            with_payload=True
        )
        
        # Verify result contains expected documents
        assert len(result) == 2
        # Results should be strings (document chunks)
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)
        # Verify content
        assert result[0] == 'first document chunk'
        assert result[1] == 'second document chunk'

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_multiple_vectors(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings with multiple vectors"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query responses for different vectors
        mock_point1 = MagicMock()
        mock_point1.payload = {'doc': 'document from vector 1'}
        mock_point2 = MagicMock()
        mock_point2.payload = {'doc': 'document from vector 2'}
        mock_point3 = MagicMock()
        mock_point3.payload = {'doc': 'another document from vector 2'}
        
        mock_response1 = MagicMock()
        mock_response1.points = [mock_point1]
        mock_response2 = MagicMock()
        mock_response2.points = [mock_point2, mock_point3]
        mock_qdrant_instance.query_points.side_effect = [mock_response1, mock_response2]
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message with multiple vectors
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2], [0.3, 0.4]]
        mock_message.limit = 3
        mock_message.user = 'multi_user'
        mock_message.collection = 'multi_collection'
        
        # Act
        result = await processor.query_document_embeddings(mock_message)

        # Assert
        # Verify query was called twice
        assert mock_qdrant_instance.query_points.call_count == 2
        
        # Verify both collections were queried
        expected_collection = 'd_multi_user_multi_collection_2'
        calls = mock_qdrant_instance.query_points.call_args_list
        assert calls[0][1]['collection_name'] == expected_collection
        assert calls[1][1]['collection_name'] == expected_collection
        assert calls[0][1]['query'] == [0.1, 0.2]
        assert calls[1][1]['query'] == [0.3, 0.4]
        
        # Verify results from both vectors are combined
        assert len(result) == 3
        assert 'document from vector 1' in result
        assert 'document from vector 2' in result
        assert 'another document from vector 2' in result

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_with_limit(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings respects limit parameter"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response with many results
        mock_points = []
        for i in range(10):
            mock_point = MagicMock()
            mock_point.payload = {'doc': f'document chunk {i}'}
            mock_points.append(mock_point)
        
        mock_response = MagicMock()
        mock_response.points = mock_points
        mock_qdrant_instance.query_points.return_value = mock_response
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message with limit
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2, 0.3]]
        mock_message.limit = 3  # Should only return 3 results
        mock_message.user = 'limit_user'
        mock_message.collection = 'limit_collection'
        
        # Act
        result = await processor.query_document_embeddings(mock_message)

        # Assert
        # Verify query was called with exact limit (no multiplication)
        mock_qdrant_instance.query_points.assert_called_once()
        call_args = mock_qdrant_instance.query_points.call_args
        assert call_args[1]['limit'] == 3  # Direct limit
        
        # Verify result contains all returned documents (limit applied by Qdrant)
        assert len(result) == 10  # All results returned by mock

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_empty_results(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings with empty results"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock empty query response
        mock_response = MagicMock()
        mock_response.points = []
        mock_qdrant_instance.query_points.return_value = mock_response
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2]]
        mock_message.limit = 5
        mock_message.user = 'empty_user'
        mock_message.collection = 'empty_collection'
        
        # Act
        result = await processor.query_document_embeddings(mock_message)

        # Assert
        assert result == []

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_different_dimensions(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings with different vector dimensions"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query responses
        mock_point1 = MagicMock()
        mock_point1.payload = {'doc': 'document from 2D vector'}
        mock_point2 = MagicMock()
        mock_point2.payload = {'doc': 'document from 3D vector'}
        
        mock_response1 = MagicMock()
        mock_response1.points = [mock_point1]
        mock_response2 = MagicMock()
        mock_response2.points = [mock_point2]
        mock_qdrant_instance.query_points.side_effect = [mock_response1, mock_response2]
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message with different dimension vectors
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2], [0.3, 0.4, 0.5]]  # 2D and 3D
        mock_message.limit = 5
        mock_message.user = 'dim_user'
        mock_message.collection = 'dim_collection'
        
        # Act
        result = await processor.query_document_embeddings(mock_message)

        # Assert
        # Verify query was called twice with different collections
        assert mock_qdrant_instance.query_points.call_count == 2
        calls = mock_qdrant_instance.query_points.call_args_list
        
        # First call should use 2D collection
        assert calls[0][1]['collection_name'] == 'd_dim_user_dim_collection_2'
        assert calls[0][1]['query'] == [0.1, 0.2]
        
        # Second call should use 3D collection
        assert calls[1][1]['collection_name'] == 'd_dim_user_dim_collection_3'
        assert calls[1][1]['query'] == [0.3, 0.4, 0.5]
        
        # Verify results
        assert len(result) == 2
        assert 'document from 2D vector' in result
        assert 'document from 3D vector' in result

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_utf8_encoding(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings with UTF-8 content"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response with UTF-8 content
        mock_point1 = MagicMock()
        mock_point1.payload = {'doc': 'Document with UTF-8: café, naïve, résumé'}
        mock_point2 = MagicMock()
        mock_point2.payload = {'doc': 'Chinese text: 你好世界'}
        
        mock_response = MagicMock()
        mock_response.points = [mock_point1, mock_point2]
        mock_qdrant_instance.query_points.return_value = mock_response
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2]]
        mock_message.limit = 5
        mock_message.user = 'utf8_user'
        mock_message.collection = 'utf8_collection'
        
        # Act
        result = await processor.query_document_embeddings(mock_message)

        # Assert
        assert len(result) == 2
        
        # Verify UTF-8 content works correctly
        assert 'Document with UTF-8: café, naïve, résumé' in result
        assert 'Chinese text: 你好世界' in result

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_qdrant_error(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings handles Qdrant errors"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock Qdrant error
        mock_qdrant_instance.query_points.side_effect = Exception("Qdrant connection failed")
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2]]
        mock_message.limit = 5
        mock_message.user = 'error_user'
        mock_message.collection = 'error_collection'
        
        # Act & Assert
        with pytest.raises(Exception, match="Qdrant connection failed"):
            await processor.query_document_embeddings(mock_message)

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_zero_limit(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings with zero limit"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response
        mock_point = MagicMock()
        mock_point.payload = {'doc': 'document chunk'}
        mock_response = MagicMock()
        mock_response.points = [mock_point]
        mock_qdrant_instance.query_points.return_value = mock_response
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message with zero limit
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2]]
        mock_message.limit = 0
        mock_message.user = 'zero_user'
        mock_message.collection = 'zero_collection'
        
        # Act
        result = await processor.query_document_embeddings(mock_message)

        # Assert
        # Should still query (with limit 0)
        mock_qdrant_instance.query_points.assert_called_once()
        call_args = mock_qdrant_instance.query_points.call_args
        assert call_args[1]['limit'] == 0
        
        # Result should contain all returned documents
        assert len(result) == 1
        assert result[0] == 'document chunk'

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_large_limit(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings with large limit"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response with fewer results than limit
        mock_point1 = MagicMock()
        mock_point1.payload = {'doc': 'document 1'}
        mock_point2 = MagicMock()
        mock_point2.payload = {'doc': 'document 2'}
        
        mock_response = MagicMock()
        mock_response.points = [mock_point1, mock_point2]
        mock_qdrant_instance.query_points.return_value = mock_response
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message with large limit
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2]]
        mock_message.limit = 1000  # Large limit
        mock_message.user = 'large_user'
        mock_message.collection = 'large_collection'
        
        # Act
        result = await processor.query_document_embeddings(mock_message)

        # Assert
        # Should query with full limit
        mock_qdrant_instance.query_points.assert_called_once()
        call_args = mock_qdrant_instance.query_points.call_args
        assert call_args[1]['limit'] == 1000
        
        # Result should contain all available documents
        assert len(result) == 2
        assert 'document 1' in result
        assert 'document 2' in result

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_query_document_embeddings_missing_payload(self, mock_base_init, mock_qdrant_client):
        """Test querying document embeddings with missing payload data"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response with missing 'doc' key
        mock_point1 = MagicMock()
        mock_point1.payload = {'doc': 'valid document'}
        mock_point2 = MagicMock()
        mock_point2.payload = {}  # Missing 'doc' key
        mock_point3 = MagicMock()
        mock_point3.payload = {'other_key': 'invalid'}  # Wrong key
        
        mock_response = MagicMock()
        mock_response.points = [mock_point1, mock_point2, mock_point3]
        mock_qdrant_instance.query_points.return_value = mock_response
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.vectors = [[0.1, 0.2]]
        mock_message.limit = 5
        mock_message.user = 'payload_user'
        mock_message.collection = 'payload_collection'
        
        # Act & Assert
        # This should raise a KeyError when trying to access payload['doc']
        with pytest.raises(KeyError):
            await processor.query_document_embeddings(mock_message)

    @patch('trustgraph.query.doc_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.DocumentEmbeddingsQueryService.__init__')
    async def test_add_args_calls_parent(self, mock_base_init, mock_qdrant_client):
        """Test that add_args() calls parent add_args method"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_client.return_value = MagicMock()
        mock_parser = MagicMock()
        
        # Act
        with patch('trustgraph.base.DocumentEmbeddingsQueryService.add_args') as mock_parent_add_args:
            Processor.add_args(mock_parser)

        # Assert
        mock_parent_add_args.assert_called_once_with(mock_parser)
        
        # Verify processor-specific arguments were added
        assert mock_parser.add_argument.call_count >= 2  # At least store-uri and api-key


if __name__ == '__main__':
    pytest.main([__file__])