"""
Contract tests for EmbeddingsService base class

Tests the contract between the EmbeddingsService base class and its
implementations, ensuring proper integration of the model parameter handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from unittest import IsolatedAsyncioTestCase
from trustgraph.base import EmbeddingsService
from trustgraph.schema import EmbeddingsRequest, EmbeddingsResponse, Error


class ConcreteEmbeddingsService(EmbeddingsService):
    """Concrete implementation for testing the abstract base class"""

    def __init__(self, **params):
        self.on_embeddings_calls = []
        self.default_model = params.get("model", "default-test-model")
        # Don't call super().__init__ to avoid taskgroup requirements in tests
        # We're only testing the on_embeddings interface

    async def on_embeddings(self, text, model=None):
        """Implementation that tracks calls"""
        self.on_embeddings_calls.append({
            "text": text,
            "model": model
        })
        # Return a simple embedding
        return [[0.1, 0.2, 0.3]]


class TestEmbeddingsServiceModelParameterContract(IsolatedAsyncioTestCase):
    """Test the model parameter contract in embeddings implementations"""

    async def test_on_embeddings_accepts_model_parameter(self):
        """Test that on_embeddings method accepts optional model parameter"""
        # Arrange
        service = ConcreteEmbeddingsService(model="default-model")

        # Act
        result1 = await service.on_embeddings("test text")
        result2 = await service.on_embeddings("test text", model="custom-model")
        result3 = await service.on_embeddings("test text", model=None)

        # Assert
        assert len(service.on_embeddings_calls) == 3
        assert service.on_embeddings_calls[0]["model"] is None  # No model specified
        assert service.on_embeddings_calls[1]["model"] == "custom-model"
        assert service.on_embeddings_calls[2]["model"] is None

    async def test_implementation_tracks_model_changes(self):
        """Test that implementations properly track which model is requested"""
        # Arrange
        service = ConcreteEmbeddingsService(model="default-model")

        # Act - multiple requests with different models
        await service.on_embeddings("text1", model="model-a")
        await service.on_embeddings("text2", model="model-b")
        await service.on_embeddings("text3")  # Use default (None passed)
        await service.on_embeddings("text4", model="model-a")

        # Assert
        assert len(service.on_embeddings_calls) == 4
        assert service.on_embeddings_calls[0]["model"] == "model-a"
        assert service.on_embeddings_calls[1]["model"] == "model-b"
        assert service.on_embeddings_calls[2]["model"] is None
        assert service.on_embeddings_calls[3]["model"] == "model-a"

    async def test_model_parameter_with_various_text_inputs(self):
        """Test model parameter works with different text inputs"""
        # Arrange
        service = ConcreteEmbeddingsService(model="default-model")

        test_cases = [
            ("Simple text", "model-1"),
            ("", "model-2"),
            ("Unicode: 世界 🌍", "model-3"),
            ("Very " * 100 + "long text", None),
        ]

        # Act
        for text, model in test_cases:
            await service.on_embeddings(text, model=model)

        # Assert
        assert len(service.on_embeddings_calls) == len(test_cases)
        for i, (text, model) in enumerate(test_cases):
            assert service.on_embeddings_calls[i]["text"] == text
            assert service.on_embeddings_calls[i]["model"] == model

    async def test_embeddings_return_format(self):
        """Test that embeddings are returned in correct format"""
        # Arrange
        service = ConcreteEmbeddingsService(model="default-model")

        # Act
        result = await service.on_embeddings("test text", model="test-model")

        # Assert
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], list)
        assert all(isinstance(x, float) for x in result[0])


class TestEmbeddingsResponseSchema:
    """Test the EmbeddingsResponse schema contract"""

    def test_success_response(self):
        """Test creating success response"""
        # Act
        response = EmbeddingsResponse(
            error=None,
            vectors=[[0.1, 0.2, 0.3]]
        )

        # Assert
        assert response.error is None
        assert response.vectors == [[0.1, 0.2, 0.3]]

    def test_error_response(self):
        """Test creating error response"""
        # Act
        error = Error(type="test-error", message="Test message")
        response = EmbeddingsResponse(
            error=error,
            vectors=None
        )

        # Assert
        assert response.error is not None
        assert response.error.type == "test-error"
        assert response.error.message == "Test message"
        assert response.vectors is None

    def test_response_with_multiple_vectors(self):
        """Test response with multiple embedding vectors"""
        # Act
        vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        response = EmbeddingsResponse(
            error=None,
            vectors=vectors
        )

        # Assert
        assert len(response.vectors) == 3
        assert response.vectors[0] == [0.1, 0.2, 0.3]


if __name__ == '__main__':
    pytest.main([__file__])
