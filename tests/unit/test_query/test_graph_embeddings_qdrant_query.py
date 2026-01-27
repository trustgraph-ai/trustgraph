"""
Unit tests for trustgraph.query.graph_embeddings.qdrant.service
Testing graph embeddings query functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.query.graph_embeddings.qdrant.service import Processor
from trustgraph.schema import IRI, LITERAL


class TestQdrantGraphEmbeddingsQuery(IsolatedAsyncioTestCase):
    """Test Qdrant graph embeddings query functionality"""

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
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
            'id': 'test-graph-query-processor'
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

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_base_init, mock_qdrant_client):
        """Test processor initialization with default values"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-graph-query-processor'
            # No store_uri or api_key provided - should use defaults
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify QdrantClient was created with default URI and None API key
        mock_qdrant_client.assert_called_once_with(url='http://localhost:6333', api_key=None)

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_create_value_http_uri(self, mock_base_init, mock_qdrant_client):
        """Test create_value with HTTP URI"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_client.return_value = MagicMock()
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Act
        value = processor.create_value('http://example.com/entity')

        # Assert
        assert hasattr(value, 'iri')
        assert value.iri == 'http://example.com/entity'
        assert hasattr(value, 'type')
        assert value.type == IRI

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_create_value_https_uri(self, mock_base_init, mock_qdrant_client):
        """Test create_value with HTTPS URI"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_client.return_value = MagicMock()
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Act
        value = processor.create_value('https://secure.example.com/entity')

        # Assert
        assert hasattr(value, 'iri')
        assert value.iri == 'https://secure.example.com/entity'
        assert hasattr(value, 'type')
        assert value.type == IRI

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_create_value_regular_string(self, mock_base_init, mock_qdrant_client):
        """Test create_value with regular string (non-URI)"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_client.return_value = MagicMock()
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        
        # Act
        value = processor.create_value('regular entity name')

        # Assert
        assert hasattr(value, 'value')
        assert value.value == 'regular entity name'
        assert hasattr(value, 'type')
        assert value.type == LITERAL

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_query_graph_embeddings_single_vector(self, mock_base_init, mock_qdrant_client):
        """Test querying graph embeddings with single vector"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response
        mock_point1 = MagicMock()
        mock_point1.payload = {'entity': 'entity1'}
        mock_point2 = MagicMock()
        mock_point2.payload = {'entity': 'entity2'}
        
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
        result = await processor.query_graph_embeddings(mock_message)

        # Assert
        # Verify query was called with correct parameters (with dimension suffix)
        expected_collection = 't_test_user_test_collection_3'  # 3 dimensions
        mock_qdrant_instance.query_points.assert_called_once_with(
            collection_name=expected_collection,
            query=[0.1, 0.2, 0.3],
            limit=10,  # limit * 2 for deduplication
            with_payload=True
        )
        
        # Verify result contains expected entities
        assert len(result) == 2
        assert all(hasattr(entity, 'value') for entity in result)
        entity_values = [entity.value for entity in result]
        assert 'entity1' in entity_values
        assert 'entity2' in entity_values

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_query_graph_embeddings_multiple_vectors(self, mock_base_init, mock_qdrant_client):
        """Test querying graph embeddings with multiple vectors"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query responses for different vectors
        mock_point1 = MagicMock()
        mock_point1.payload = {'entity': 'entity1'}
        mock_point2 = MagicMock()
        mock_point2.payload = {'entity': 'entity2'}
        mock_point3 = MagicMock()
        mock_point3.payload = {'entity': 'entity3'}
        
        mock_response1 = MagicMock()
        mock_response1.points = [mock_point1, mock_point2]
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
        result = await processor.query_graph_embeddings(mock_message)

        # Assert
        # Verify query was called twice
        assert mock_qdrant_instance.query_points.call_count == 2

        # Verify both collections were queried (both 2-dimensional vectors)
        expected_collection = 't_multi_user_multi_collection_2'  # 2 dimensions
        calls = mock_qdrant_instance.query_points.call_args_list
        assert calls[0][1]['collection_name'] == expected_collection
        assert calls[1][1]['collection_name'] == expected_collection
        assert calls[0][1]['query'] == [0.1, 0.2]
        assert calls[1][1]['query'] == [0.3, 0.4]
        
        # Verify deduplication - entity2 appears in both results but should only appear once
        entity_values = [entity.value for entity in result]
        assert len(set(entity_values)) == len(entity_values)  # All unique
        assert 'entity1' in entity_values
        assert 'entity2' in entity_values
        assert 'entity3' in entity_values

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_query_graph_embeddings_with_limit(self, mock_base_init, mock_qdrant_client):
        """Test querying graph embeddings respects limit parameter"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response with more results than limit
        mock_points = []
        for i in range(10):
            mock_point = MagicMock()
            mock_point.payload = {'entity': f'entity{i}'}
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
        result = await processor.query_graph_embeddings(mock_message)

        # Assert
        # Verify query was called with limit * 2
        mock_qdrant_instance.query_points.assert_called_once()
        call_args = mock_qdrant_instance.query_points.call_args
        assert call_args[1]['limit'] == 6  # 3 * 2
        
        # Verify result is limited to requested limit
        assert len(result) == 3

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_query_graph_embeddings_empty_results(self, mock_base_init, mock_qdrant_client):
        """Test querying graph embeddings with empty results"""
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
        result = await processor.query_graph_embeddings(mock_message)

        # Assert
        assert result == []

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_query_graph_embeddings_different_dimensions(self, mock_base_init, mock_qdrant_client):
        """Test querying graph embeddings with different vector dimensions"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query responses
        mock_point1 = MagicMock()
        mock_point1.payload = {'entity': 'entity2d'}
        mock_point2 = MagicMock()
        mock_point2.payload = {'entity': 'entity3d'}
        
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
        result = await processor.query_graph_embeddings(mock_message)

        # Assert
        # Verify query was called twice with different collections
        assert mock_qdrant_instance.query_points.call_count == 2
        calls = mock_qdrant_instance.query_points.call_args_list

        # First call should use 2D collection
        assert calls[0][1]['collection_name'] == 't_dim_user_dim_collection_2'  # 2 dimensions
        assert calls[0][1]['query'] == [0.1, 0.2]

        # Second call should use 3D collection
        assert calls[1][1]['collection_name'] == 't_dim_user_dim_collection_3'  # 3 dimensions
        assert calls[1][1]['query'] == [0.3, 0.4, 0.5]
        
        # Verify results
        entity_values = [entity.value for entity in result]
        assert 'entity2d' in entity_values
        assert 'entity3d' in entity_values

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_query_graph_embeddings_uri_detection(self, mock_base_init, mock_qdrant_client):
        """Test querying graph embeddings with URI detection"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response with URIs and regular strings
        mock_point1 = MagicMock()
        mock_point1.payload = {'entity': 'http://example.com/entity1'}
        mock_point2 = MagicMock()
        mock_point2.payload = {'entity': 'https://secure.example.com/entity2'}
        mock_point3 = MagicMock()
        mock_point3.payload = {'entity': 'regular entity'}
        
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
        mock_message.user = 'uri_user'
        mock_message.collection = 'uri_collection'
        
        # Act
        result = await processor.query_graph_embeddings(mock_message)

        # Assert
        assert len(result) == 3
        
        # Check URI entities
        uri_entities = [entity for entity in result if entity.type == IRI]
        assert len(uri_entities) == 2
        uri_values = [entity.iri for entity in uri_entities]
        assert 'http://example.com/entity1' in uri_values
        assert 'https://secure.example.com/entity2' in uri_values

        # Check regular entities
        regular_entities = [entity for entity in result if entity.type == LITERAL]
        assert len(regular_entities) == 1
        assert regular_entities[0].value == 'regular entity'

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_query_graph_embeddings_qdrant_error(self, mock_base_init, mock_qdrant_client):
        """Test querying graph embeddings handles Qdrant errors"""
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
            await processor.query_graph_embeddings(mock_message)

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_query_graph_embeddings_zero_limit(self, mock_base_init, mock_qdrant_client):
        """Test querying graph embeddings with zero limit"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        # Mock query response - even with zero limit, Qdrant might return results
        mock_point = MagicMock()
        mock_point.payload = {'entity': 'entity1'}
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
        result = await processor.query_graph_embeddings(mock_message)

        # Assert
        # Should still query (with limit 0)
        mock_qdrant_instance.query_points.assert_called_once()
        call_args = mock_qdrant_instance.query_points.call_args
        assert call_args[1]['limit'] == 0  # 0 * 2 = 0
        
        # With zero limit, the logic still adds one entity before checking the limit
        # So it returns one result (current behavior, not ideal but actual)
        assert len(result) == 1
        assert result[0].value == 'entity1'

    @patch('trustgraph.query.graph_embeddings.qdrant.service.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsQueryService.__init__')
    async def test_add_args_calls_parent(self, mock_base_init, mock_qdrant_client):
        """Test that add_args() calls parent add_args method"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_client.return_value = MagicMock()
        mock_parser = MagicMock()
        
        # Act
        with patch('trustgraph.base.GraphEmbeddingsQueryService.add_args') as mock_parent_add_args:
            Processor.add_args(mock_parser)

        # Assert
        mock_parent_add_args.assert_called_once_with(mock_parser)
        
        # Verify processor-specific arguments were added
        assert mock_parser.add_argument.call_count >= 2  # At least store-uri and api-key


if __name__ == '__main__':
    pytest.main([__file__])