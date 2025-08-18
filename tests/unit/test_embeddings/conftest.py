"""
Shared fixtures for embeddings unit tests
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, MagicMock
from trustgraph.schema import EmbeddingsRequest, EmbeddingsResponse, Error


@pytest.fixture
def sample_text():
    """Sample text for embedding tests"""
    return "This is a sample text for embedding generation."


@pytest.fixture
def sample_embedding_vector():
    """Sample embedding vector for mocking"""
    return [0.1, 0.2, -0.3, 0.4, -0.5, 0.6, 0.7, -0.8, 0.9, -1.0]


@pytest.fixture
def sample_batch_embeddings():
    """Sample batch of embedding vectors"""
    return [
        [0.1, 0.2, -0.3, 0.4, -0.5],
        [0.6, 0.7, -0.8, 0.9, -1.0],
        [-0.1, -0.2, 0.3, -0.4, 0.5]
    ]


@pytest.fixture
def sample_embeddings_request():
    """Sample EmbeddingsRequest for testing"""
    return EmbeddingsRequest(
        text="Test text for embedding"
    )


@pytest.fixture
def sample_embeddings_response(sample_embedding_vector):
    """Sample successful EmbeddingsResponse"""
    return EmbeddingsResponse(
        error=None,
        vectors=sample_embedding_vector
    )


@pytest.fixture
def sample_error_response():
    """Sample error EmbeddingsResponse"""
    return EmbeddingsResponse(
        error=Error(type="embedding-error", message="Model not found"),
        vectors=None
    )


@pytest.fixture
def mock_message():
    """Mock Pulsar message for testing"""
    message = Mock()
    message.properties.return_value = {"id": "test-message-123"}
    return message


@pytest.fixture
def mock_flow():
    """Mock flow for producer/consumer testing"""
    flow = Mock()
    flow.return_value.send = AsyncMock()
    flow.producer = {"response": Mock()}
    flow.producer["response"].send = AsyncMock()
    return flow


@pytest.fixture
def mock_consumer():
    """Mock Pulsar consumer"""
    return AsyncMock()


@pytest.fixture
def mock_producer():
    """Mock Pulsar producer"""
    return AsyncMock()


@pytest.fixture
def mock_fastembed_embedding():
    """Mock FastEmbed TextEmbedding"""
    mock = Mock()
    mock.embed.return_value = [np.array([0.1, 0.2, -0.3, 0.4, -0.5])]
    return mock


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client"""
    mock = Mock()
    mock.embed.return_value = Mock(
        embeddings=[0.1, 0.2, -0.3, 0.4, -0.5]
    )
    return mock


@pytest.fixture
def embedding_test_params():
    """Common parameters for embedding processor testing"""
    return {
        "model": "test-model",
        "concurrency": 1,
        "id": "test-embeddings"
    }