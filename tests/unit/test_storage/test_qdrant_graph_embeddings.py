"""
Unit tests for trustgraph.storage.graph_embeddings.qdrant.write
Starting small with a single test to verify basic functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.storage.graph_embeddings.qdrant.write import Processor


class TestQdrantGraphEmbeddingsSimple(IsolatedAsyncioTestCase):
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
        assert hasattr(processor, 'last_collection')
        assert processor.last_collection is None

    @patch('trustgraph.storage.graph_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.base.GraphEmbeddingsStoreService.__init__')
    async def test_get_collection_creates_new_collection(self, mock_base_init, mock_qdrant_client):
        """Test get_collection creates a new collection when it doesn't exist"""
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
        
        # Act
        collection_name = processor.get_collection(dim=512, user='test_user', collection='test_collection')

        # Assert
        expected_name = 't_test_user_test_collection_512'
        assert collection_name == expected_name
        assert processor.last_collection == expected_name
        
        # Verify collection existence check and creation
        mock_qdrant_instance.collection_exists.assert_called_once_with(expected_name)
        mock_qdrant_instance.create_collection.assert_called_once()
        
        # Verify create_collection was called with correct parameters
        create_call_args = mock_qdrant_instance.create_collection.call_args
        assert create_call_args[1]['collection_name'] == expected_name

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
        expected_collection = 't_test_user_test_collection_3'
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


if __name__ == '__main__':
    pytest.main([__file__])