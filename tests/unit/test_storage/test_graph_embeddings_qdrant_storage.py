"""
Unit tests for trustgraph.storage.graph_embeddings.qdrant.write
Starting small with a single test to verify basic functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.storage.graph_embeddings.qdrant.write import Processor


class TestQdrantGraphEmbeddingsStorage(IsolatedAsyncioTestCase):
    """Test Qdrant graph embeddings storage functionality"""

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
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
            'id': 'test-qdrant-processor'
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

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_get_collection_validates_existence(self, mock_base_init, mock_qdrant_client):
        """Test get_collection validates that collection exists"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = False
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(ValueError, match="Collection .* does not exist"):
            processor.get_collection(user='test_user', collection='test_collection')

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.graph_embeddings.qdrant.write.uuid')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_store_graph_embeddings_basic(self, mock_base_init, mock_uuid, mock_qdrant_client):
        """Test storing graph embeddings with basic message"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True  # Collection already exists
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value.return_value = 'test-uuid-123'
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)
        
        # Create mock message with entities and vectors
        mock_message = MagicMock()
        mock_message.metadata.user = 'test_user'
        mock_message.metadata.collection = 'test_collection'
        
        mock_entity = MagicMock()
        mock_entity.entity.value = 'test_entity'
        mock_entity.vectors = [[0.1, 0.2, 0.3]]  # Single vector with 3 dimensions
        
        mock_message.entities = [mock_entity]
        
        # Act
        await processor.store_graph_embeddings(mock_message)

        # Assert
        # Verify collection existence was checked
        expected_collection = 't_test_user_test_collection'
        mock_qdrant_instance.collection_exists.assert_called_once_with(expected_collection)
        
        # Verify upsert was called
        mock_qdrant_instance.upsert.assert_called_once()
        
        # Verify upsert parameters
        upsert_call_args = mock_qdrant_instance.upsert.call_args
        assert upsert_call_args[1]['collection_name'] == expected_collection
        assert len(upsert_call_args[1]['points']) == 1
        
        point = upsert_call_args[1]['points'][0]
        assert point.vector == [0.1, 0.2, 0.3]
        assert point.payload['entity'] == 'test_entity'

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_get_collection_uses_existing_collection(self, mock_base_init, mock_qdrant_client):
        """Test get_collection uses existing collection without creating new one"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True  # Collection exists
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)

        # Act
        collection_name = processor.get_collection(user='existing_user', collection='existing_collection')

        # Assert
        expected_name = 't_existing_user_existing_collection'
        assert collection_name == expected_name

        # Verify collection existence check was performed
        mock_qdrant_instance.collection_exists.assert_called_once_with(expected_name)
        # Verify create_collection was NOT called
        mock_qdrant_instance.create_collection.assert_not_called()

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_get_collection_validates_on_each_call(self, mock_base_init, mock_qdrant_client):
        """Test get_collection validates collection existence on each call"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)

        # First call
        collection_name1 = processor.get_collection(user='cache_user', collection='cache_collection')

        # Reset mock to track second call
        mock_qdrant_instance.reset_mock()
        mock_qdrant_instance.collection_exists.return_value = True

        # Act - Second call with same parameters
        collection_name2 = processor.get_collection(user='cache_user', collection='cache_collection')

        # Assert
        expected_name = 't_cache_user_cache_collection'
        assert collection_name1 == expected_name
        assert collection_name2 == expected_name

        # Verify collection existence check happens on each call
        mock_qdrant_instance.collection_exists.assert_called_once_with(expected_name)
        mock_qdrant_instance.create_collection.assert_not_called()

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_get_collection_creation_exception(self, mock_base_init, mock_qdrant_client):
        """Test get_collection raises ValueError when collection doesn't exist"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = False
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(ValueError, match="Collection .* does not exist"):
            processor.get_collection(user='error_user', collection='error_collection')

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.graph_embeddings.qdrant.write.uuid')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_store_graph_embeddings_multiple_entities(self, mock_base_init, mock_uuid, mock_qdrant_client):
        """Test storing graph embeddings with multiple entities"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value.return_value = 'test-uuid'
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)
        
        # Create mock message with multiple entities
        mock_message = MagicMock()
        mock_message.metadata.user = 'multi_user'
        mock_message.metadata.collection = 'multi_collection'
        
        mock_entity1 = MagicMock()
        mock_entity1.entity.value = 'entity_one'
        mock_entity1.vectors = [[0.1, 0.2]]
        
        mock_entity2 = MagicMock()
        mock_entity2.entity.value = 'entity_two'
        mock_entity2.vectors = [[0.3, 0.4]]
        
        mock_message.entities = [mock_entity1, mock_entity2]
        
        # Act
        await processor.store_graph_embeddings(mock_message)

        # Assert
        # Should be called twice (once per entity)
        assert mock_qdrant_instance.upsert.call_count == 2
        
        # Verify both entities were processed
        upsert_calls = mock_qdrant_instance.upsert.call_args_list
        
        # First entity
        first_call = upsert_calls[0]
        first_point = first_call[1]['points'][0]
        assert first_point.vector == [0.1, 0.2]
        assert first_point.payload['entity'] == 'entity_one'
        
        # Second entity
        second_call = upsert_calls[1]
        second_point = second_call[1]['points'][0]
        assert second_point.vector == [0.3, 0.4]
        assert second_point.payload['entity'] == 'entity_two'

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.graph_embeddings.qdrant.write.uuid')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_store_graph_embeddings_multiple_vectors_per_entity(self, mock_base_init, mock_uuid, mock_qdrant_client):
        """Test storing graph embeddings with multiple vectors per entity"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value.return_value = 'test-uuid'
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)
        
        # Create mock message with entity having multiple vectors
        mock_message = MagicMock()
        mock_message.metadata.user = 'vector_user'
        mock_message.metadata.collection = 'vector_collection'
        
        mock_entity = MagicMock()
        mock_entity.entity.value = 'multi_vector_entity'
        mock_entity.vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        
        mock_message.entities = [mock_entity]
        
        # Act
        await processor.store_graph_embeddings(mock_message)

        # Assert
        # Should be called 3 times (once per vector)
        assert mock_qdrant_instance.upsert.call_count == 3
        
        # Verify all vectors were processed
        upsert_calls = mock_qdrant_instance.upsert.call_args_list
        
        expected_vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6], 
            [0.7, 0.8, 0.9]
        ]
        
        for i, call in enumerate(upsert_calls):
            point = call[1]['points'][0]
            assert point.vector == expected_vectors[i]
            assert point.payload['entity'] == 'multi_vector_entity'

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_store_graph_embeddings_empty_entity_value(self, mock_base_init, mock_qdrant_client):
        """Test storing graph embeddings skips empty entity values"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)
        
        # Create mock message with empty entity value
        mock_message = MagicMock()
        mock_message.metadata.user = 'empty_user'
        mock_message.metadata.collection = 'empty_collection'
        
        mock_entity_empty = MagicMock()
        mock_entity_empty.entity.value = ""  # Empty string
        mock_entity_empty.vectors = [[0.1, 0.2]]
        
        mock_entity_none = MagicMock()
        mock_entity_none.entity.value = None  # None value
        mock_entity_none.vectors = [[0.3, 0.4]]
        
        mock_message.entities = [mock_entity_empty, mock_entity_none]
        
        # Act
        await processor.store_graph_embeddings(mock_message)

        # Assert
        # Should not call upsert for empty entities
        mock_qdrant_instance.upsert.assert_not_called()
        mock_qdrant_instance.collection_exists.assert_not_called()

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_base_init, mock_qdrant_client):
        """Test processor initialization with default values"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
            # No store_uri or api_key provided - should use defaults
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify QdrantClient was created with default URI and None API key
        mock_qdrant_client.assert_called_once_with(url='http://localhost:6333', api_key=None)

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_add_args_calls_parent(self, mock_base_init, mock_qdrant_client):
        """Test that add_args() calls parent add_args method"""
        # Arrange
        mock_base_init.return_value = None
        mock_qdrant_client.return_value = MagicMock()
        mock_parser = MagicMock()
        
        # Act
        with patch('trustgraph.base.GraphEmbeddingsStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(mock_parser)

        # Assert
        mock_parent_add_args.assert_called_once_with(mock_parser)
        
        # Verify processor-specific arguments were added
        assert mock_parser.add_argument.call_count >= 2  # At least store-uri and api-key


if __name__ == '__main__':
    pytest.main([__file__])