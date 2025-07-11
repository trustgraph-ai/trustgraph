"""
Shared fixtures for storage tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def base_storage_config():
    """Base configuration for storage processors"""
    return {
        'taskgroup': AsyncMock(),
        'id': 'test-storage-processor'
    }


@pytest.fixture
def qdrant_storage_config(base_storage_config):
    """Configuration for Qdrant storage processors"""
    return base_storage_config | {
        'store_uri': 'http://localhost:6333',
        'api_key': 'test-api-key'
    }


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client"""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    mock_client.create_collection.return_value = None
    mock_client.upsert.return_value = None
    return mock_client


@pytest.fixture
def mock_uuid():
    """Mock UUID generation"""
    mock_uuid = MagicMock()
    mock_uuid.uuid4.return_value = MagicMock()
    mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value='test-uuid-123')
    return mock_uuid


# Document embeddings fixtures
@pytest.fixture
def mock_document_embeddings_message():
    """Mock document embeddings message"""
    mock_message = MagicMock()
    mock_message.metadata.user = 'test_user'
    mock_message.metadata.collection = 'test_collection'
    
    mock_chunk = MagicMock()
    mock_chunk.chunk.decode.return_value = 'test document chunk'
    mock_chunk.vectors = [[0.1, 0.2, 0.3]]
    
    mock_message.chunks = [mock_chunk]
    return mock_message


@pytest.fixture
def mock_document_embeddings_multiple_chunks():
    """Mock document embeddings message with multiple chunks"""
    mock_message = MagicMock()
    mock_message.metadata.user = 'multi_user'
    mock_message.metadata.collection = 'multi_collection'
    
    mock_chunk1 = MagicMock()
    mock_chunk1.chunk.decode.return_value = 'first document chunk'
    mock_chunk1.vectors = [[0.1, 0.2]]
    
    mock_chunk2 = MagicMock()
    mock_chunk2.chunk.decode.return_value = 'second document chunk'
    mock_chunk2.vectors = [[0.3, 0.4]]
    
    mock_message.chunks = [mock_chunk1, mock_chunk2]
    return mock_message


@pytest.fixture
def mock_document_embeddings_multiple_vectors():
    """Mock document embeddings message with multiple vectors per chunk"""
    mock_message = MagicMock()
    mock_message.metadata.user = 'vector_user'
    mock_message.metadata.collection = 'vector_collection'
    
    mock_chunk = MagicMock()
    mock_chunk.chunk.decode.return_value = 'multi-vector document chunk'
    mock_chunk.vectors = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
        [0.7, 0.8, 0.9]
    ]
    
    mock_message.chunks = [mock_chunk]
    return mock_message


@pytest.fixture
def mock_document_embeddings_empty_chunk():
    """Mock document embeddings message with empty chunk"""
    mock_message = MagicMock()
    mock_message.metadata.user = 'empty_user'
    mock_message.metadata.collection = 'empty_collection'
    
    mock_chunk = MagicMock()
    mock_chunk.chunk.decode.return_value = ""  # Empty string
    mock_chunk.vectors = [[0.1, 0.2]]
    
    mock_message.chunks = [mock_chunk]
    return mock_message


# Graph embeddings fixtures
@pytest.fixture
def mock_graph_embeddings_message():
    """Mock graph embeddings message"""
    mock_message = MagicMock()
    mock_message.metadata.user = 'test_user'
    mock_message.metadata.collection = 'test_collection'
    
    mock_entity = MagicMock()
    mock_entity.entity.value = 'test_entity'
    mock_entity.vectors = [[0.1, 0.2, 0.3]]
    
    mock_message.entities = [mock_entity]
    return mock_message


@pytest.fixture
def mock_graph_embeddings_multiple_entities():
    """Mock graph embeddings message with multiple entities"""
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
    return mock_message


@pytest.fixture
def mock_graph_embeddings_empty_entity():
    """Mock graph embeddings message with empty entity"""
    mock_message = MagicMock()
    mock_message.metadata.user = 'empty_user'
    mock_message.metadata.collection = 'empty_collection'
    
    mock_entity = MagicMock()
    mock_entity.entity.value = ""  # Empty string
    mock_entity.vectors = [[0.1, 0.2]]
    
    mock_message.entities = [mock_entity]
    return mock_message