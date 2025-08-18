"""
Shared fixtures for query tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def base_query_config():
    """Base configuration for query processors"""
    return {
        'taskgroup': AsyncMock(),
        'id': 'test-query-processor'
    }


@pytest.fixture
def qdrant_query_config(base_query_config):
    """Configuration for Qdrant query processors"""
    return base_query_config | {
        'store_uri': 'http://localhost:6333',
        'api_key': 'test-api-key'
    }


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client"""
    mock_client = MagicMock()
    mock_client.query_points.return_value = []
    return mock_client


# Graph embeddings query fixtures
@pytest.fixture
def mock_graph_embeddings_request():
    """Mock graph embeddings request message"""
    mock_message = MagicMock()
    mock_message.vectors = [[0.1, 0.2, 0.3]]
    mock_message.limit = 5
    mock_message.user = 'test_user'
    mock_message.collection = 'test_collection'
    return mock_message


@pytest.fixture
def mock_graph_embeddings_multiple_vectors():
    """Mock graph embeddings request with multiple vectors"""
    mock_message = MagicMock()
    mock_message.vectors = [[0.1, 0.2], [0.3, 0.4]]
    mock_message.limit = 3
    mock_message.user = 'multi_user'
    mock_message.collection = 'multi_collection'
    return mock_message


@pytest.fixture
def mock_graph_embeddings_query_response():
    """Mock graph embeddings query response from Qdrant"""
    mock_point1 = MagicMock()
    mock_point1.payload = {'entity': 'entity1'}
    mock_point2 = MagicMock()
    mock_point2.payload = {'entity': 'entity2'}
    return [mock_point1, mock_point2]


@pytest.fixture
def mock_graph_embeddings_uri_response():
    """Mock graph embeddings query response with URIs"""
    mock_point1 = MagicMock()
    mock_point1.payload = {'entity': 'http://example.com/entity1'}
    mock_point2 = MagicMock()
    mock_point2.payload = {'entity': 'https://secure.example.com/entity2'}
    mock_point3 = MagicMock()
    mock_point3.payload = {'entity': 'regular entity'}
    return [mock_point1, mock_point2, mock_point3]


# Document embeddings query fixtures
@pytest.fixture
def mock_document_embeddings_request():
    """Mock document embeddings request message"""
    mock_message = MagicMock()
    mock_message.vectors = [[0.1, 0.2, 0.3]]
    mock_message.limit = 5
    mock_message.user = 'test_user'
    mock_message.collection = 'test_collection'
    return mock_message


@pytest.fixture
def mock_document_embeddings_multiple_vectors():
    """Mock document embeddings request with multiple vectors"""
    mock_message = MagicMock()
    mock_message.vectors = [[0.1, 0.2], [0.3, 0.4]]
    mock_message.limit = 3
    mock_message.user = 'multi_user'
    mock_message.collection = 'multi_collection'
    return mock_message


@pytest.fixture
def mock_document_embeddings_query_response():
    """Mock document embeddings query response from Qdrant"""
    mock_point1 = MagicMock()
    mock_point1.payload = {'doc': 'first document chunk'}
    mock_point2 = MagicMock()
    mock_point2.payload = {'doc': 'second document chunk'}
    return [mock_point1, mock_point2]


@pytest.fixture
def mock_document_embeddings_utf8_response():
    """Mock document embeddings query response with UTF-8 content"""
    mock_point1 = MagicMock()
    mock_point1.payload = {'doc': 'Document with UTF-8: café, naïve, résumé'}
    mock_point2 = MagicMock()
    mock_point2.payload = {'doc': 'Chinese text: 你好世界'}
    return [mock_point1, mock_point2]


@pytest.fixture
def mock_empty_query_response():
    """Mock empty query response"""
    return []


@pytest.fixture
def mock_large_query_response():
    """Mock large query response with many results"""
    mock_points = []
    for i in range(10):
        mock_point = MagicMock()
        mock_point.payload = {'doc': f'document chunk {i}'}
        mock_points.append(mock_point)
    return mock_points


@pytest.fixture
def mock_mixed_dimension_vectors():
    """Mock request with vectors of different dimensions"""
    mock_message = MagicMock()
    mock_message.vectors = [[0.1, 0.2], [0.3, 0.4, 0.5]]  # 2D and 3D
    mock_message.limit = 5
    mock_message.user = 'dim_user'
    mock_message.collection = 'dim_collection'
    return mock_message