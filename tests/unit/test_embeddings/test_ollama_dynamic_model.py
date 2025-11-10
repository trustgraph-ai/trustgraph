"""
Unit tests for Ollama dynamic model loading

Tests the dynamic model selection functionality for Ollama embeddings service.
Since Ollama is server-side, no model caching is needed on the client side.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from unittest import IsolatedAsyncioTestCase
from trustgraph.embeddings.ollama.processor import Processor


class TestOllamaDynamicModelLoading(IsolatedAsyncioTestCase):
    """Test Ollama dynamic model selection"""

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_client_initialized_with_host(self, mock_embeddings_init, mock_async_init, mock_client_class):
        """Test that Ollama client is initialized with correct host"""
        # Arrange
        mock_ollama_client = Mock()
        mock_response = Mock()
        mock_response.embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_ollama_client.embed.return_value = mock_response
        mock_client_class.return_value = mock_ollama_client
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        # Act
        processor = Processor(id="test", concurrency=1, model="test-model",
                            ollama="http://localhost:11434", taskgroup=AsyncMock())

        # Assert
        mock_client_class.assert_called_once_with(host="http://localhost:11434")
        assert processor.default_model == "test-model"

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_on_embeddings_uses_default_model(self, mock_embeddings_init, mock_async_init, mock_client_class):
        """Test that on_embeddings uses default model when no model specified"""
        # Arrange
        mock_ollama_client = Mock()
        mock_response = Mock()
        mock_response.embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_ollama_client.embed.return_value = mock_response
        mock_client_class.return_value = mock_ollama_client
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())

        # Act
        result = await processor.on_embeddings("test text")

        # Assert
        mock_ollama_client.embed.assert_called_once_with(
            model="test-model",
            input="test text"
        )
        assert result == [[0.1, 0.2, 0.3, 0.4, 0.5]]

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_on_embeddings_uses_specified_model(self, mock_embeddings_init, mock_async_init, mock_client_class):
        """Test that on_embeddings uses specified model when provided"""
        # Arrange
        mock_ollama_client = Mock()
        mock_response = Mock()
        mock_response.embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_ollama_client.embed.return_value = mock_response
        mock_client_class.return_value = mock_ollama_client
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())

        # Act
        result = await processor.on_embeddings("test text", model="custom-model")

        # Assert
        mock_ollama_client.embed.assert_called_once_with(
            model="custom-model",
            input="test text"
        )
        assert result == [[0.1, 0.2, 0.3, 0.4, 0.5]]

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_multiple_model_switches(self, mock_embeddings_init, mock_async_init, mock_client_class):
        """Test switching between multiple models"""
        # Arrange
        mock_ollama_client = Mock()
        mock_response = Mock()
        mock_response.embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_ollama_client.embed.return_value = mock_response
        mock_client_class.return_value = mock_ollama_client
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())

        # Act - switch between different models
        await processor.on_embeddings("text1", model="model-a")
        await processor.on_embeddings("text2", model="model-b")
        await processor.on_embeddings("text3", model="model-a")
        await processor.on_embeddings("text4")  # Use default

        # Assert
        calls = mock_ollama_client.embed.call_args_list
        assert len(calls) == 4
        assert calls[0][1]['model'] == "model-a"
        assert calls[1][1]['model'] == "model-b"
        assert calls[2][1]['model'] == "model-a"
        assert calls[3][1]['model'] == "test-model"  # Default

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_none_model_uses_default(self, mock_embeddings_init, mock_async_init, mock_client_class):
        """Test that None model parameter falls back to default"""
        # Arrange
        mock_ollama_client = Mock()
        mock_response = Mock()
        mock_response.embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_ollama_client.embed.return_value = mock_response
        mock_client_class.return_value = mock_ollama_client
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())

        # Act
        result = await processor.on_embeddings("test text", model=None)

        # Assert
        mock_ollama_client.embed.assert_called_once_with(
            model="test-model",
            input="test text"
        )

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_initialization_without_model_uses_default(self, mock_embeddings_init, mock_async_init, mock_client_class):
        """Test initialization without model parameter uses module default"""
        # Arrange
        mock_ollama_client = Mock()
        mock_client_class.return_value = mock_ollama_client
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        # Act
        processor = Processor(id="test-embeddings", concurrency=1, taskgroup=AsyncMock())

        # Assert
        # Should use default_model from module
        expected_default = "mxbai-embed-large"
        assert processor.default_model == expected_default


if __name__ == '__main__':
    pytest.main([__file__])
