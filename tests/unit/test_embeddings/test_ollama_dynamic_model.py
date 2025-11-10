"""
Unit tests for Ollama dynamic model loading

Tests the dynamic model selection functionality for Ollama embeddings service.
Since Ollama is server-side, no model caching is needed on the client side.
"""

import pytest
from unittest.mock import Mock, patch
from trustgraph.embeddings.ollama.processor import Processor


class TestOllamaDynamicModelLoading:
    """Test Ollama dynamic model selection"""

    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client"""
        mock = Mock()
        mock_response = Mock()
        mock_response.embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock.embed.return_value = mock_response
        return mock

    @pytest.fixture
    def base_params(self):
        """Base parameters for processor initialization"""
        return {
            "id": "test-embeddings",
            "concurrency": 1,
            "model": "test-model",
            "ollama": "http://localhost:11434"
        }

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_client_initialized_with_host(self, mock_client_class, base_params, mock_ollama_client):
        """Test that Ollama client is initialized with correct host"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client

        # Act
        processor = Processor(**base_params)

        # Assert
        mock_client_class.assert_called_once_with(host="http://localhost:11434")
        assert processor.default_model == "test-model"

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_initialization_with_default_host(self, mock_client_class, mock_ollama_client):
        """Test initialization uses default OLLAMA_HOST when not specified"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client

        # Act
        processor = Processor(
            id="test-embeddings",
            concurrency=1
        )

        # Assert
        # Should use default from module (localhost:11434 or from env)
        mock_client_class.assert_called_once()
        assert processor.client is not None

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @pytest.mark.asyncio
    async def test_on_embeddings_uses_default_model(self, mock_client_class, base_params, mock_ollama_client):
        """Test that on_embeddings uses default model when no model specified"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client
        processor = Processor(**base_params)

        # Act
        result = await processor.on_embeddings("test text")

        # Assert
        mock_ollama_client.embed.assert_called_once_with(
            model="test-model",
            input="test text"
        )
        assert result == [[0.1, 0.2, 0.3, 0.4, 0.5]]

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @pytest.mark.asyncio
    async def test_on_embeddings_uses_specified_model(self, mock_client_class, base_params, mock_ollama_client):
        """Test that on_embeddings uses specified model when provided"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client
        processor = Processor(**base_params)

        # Act
        result = await processor.on_embeddings("test text", model="custom-model")

        # Assert
        mock_ollama_client.embed.assert_called_once_with(
            model="custom-model",
            input="test text"
        )
        assert result == [[0.1, 0.2, 0.3, 0.4, 0.5]]

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @pytest.mark.asyncio
    async def test_multiple_model_switches(self, mock_client_class, base_params, mock_ollama_client):
        """Test switching between multiple models"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client
        processor = Processor(**base_params)

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
    @pytest.mark.asyncio
    async def test_none_model_uses_default(self, mock_client_class, base_params, mock_ollama_client):
        """Test that None model parameter falls back to default"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client
        processor = Processor(**base_params)

        # Act
        result = await processor.on_embeddings("test text", model=None)

        # Assert
        mock_ollama_client.embed.assert_called_once_with(
            model="test-model",
            input="test text"
        )

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @pytest.mark.asyncio
    async def test_empty_string_model_uses_default(self, mock_client_class, base_params, mock_ollama_client):
        """Test that empty string model parameter falls back to default"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client
        processor = Processor(**base_params)

        # Act
        result = await processor.on_embeddings("test text", model="")

        # Assert
        mock_ollama_client.embed.assert_called_once_with(
            model="test-model",
            input="test text"
        )

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_initialization_with_custom_model(self, mock_client_class, mock_ollama_client):
        """Test initialization with custom model parameter"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client

        # Act
        processor = Processor(
            id="test-embeddings",
            concurrency=1,
            model="custom-init-model",
            ollama="http://custom:11434"
        )

        # Assert
        mock_client_class.assert_called_once_with(host="http://custom:11434")
        assert processor.default_model == "custom-init-model"

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_initialization_without_model_uses_default(self, mock_client_class, mock_ollama_client):
        """Test initialization without model parameter uses module default"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client

        # Act
        processor = Processor(
            id="test-embeddings",
            concurrency=1
        )

        # Assert
        # Should use default_model from module
        expected_default = "mxbai-embed-large"
        assert processor.default_model == expected_default

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @pytest.mark.asyncio
    async def test_different_text_inputs(self, mock_client_class, base_params, mock_ollama_client):
        """Test with different text inputs"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client
        processor = Processor(**base_params)

        test_texts = [
            "Simple text",
            "Text with\nnewlines",
            "Unicode: 世界 🌍",
            "",
            "Very " * 1000 + "long text"
        ]

        # Act & Assert
        for text in test_texts:
            result = await processor.on_embeddings(text, model="test-model")
            # Verify embed was called with the text
            assert mock_ollama_client.embed.called
            last_call = mock_ollama_client.embed.call_args
            assert last_call[1]['input'] == text

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @pytest.mark.asyncio
    async def test_concurrent_requests_with_different_models(self, mock_client_class, base_params, mock_ollama_client):
        """Test that concurrent requests with different models work correctly"""
        # Arrange
        import asyncio
        mock_client_class.return_value = mock_ollama_client
        processor = Processor(**base_params)

        # Act - simulate concurrent requests
        tasks = [
            processor.on_embeddings("text1", model="model-a"),
            processor.on_embeddings("text2", model="model-b"),
            processor.on_embeddings("text3", model="model-a"),
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        calls = mock_ollama_client.embed.call_args_list
        assert len(calls) == 3
        # Each call should use its specified model
        assert calls[0][1]['model'] == "model-a"
        assert calls[1][1]['model'] == "model-b"
        assert calls[2][1]['model'] == "model-a"

    @patch('trustgraph.embeddings.ollama.processor.Client')
    @pytest.mark.asyncio
    async def test_embeddings_response_format(self, mock_client_class, base_params, mock_ollama_client):
        """Test that embeddings response is properly formatted"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client
        processor = Processor(**base_params)

        # Act
        result = await processor.on_embeddings("test text")

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert all(isinstance(x, float) for x in result[0])

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_custom_ollama_host_from_params(self, mock_client_class, mock_ollama_client):
        """Test that custom Ollama host from params is used"""
        # Arrange
        mock_client_class.return_value = mock_ollama_client
        custom_host = "http://custom-ollama:8080"

        # Act
        processor = Processor(
            id="test-embeddings",
            concurrency=1,
            ollama=custom_host
        )

        # Assert
        mock_client_class.assert_called_once_with(host=custom_host)
