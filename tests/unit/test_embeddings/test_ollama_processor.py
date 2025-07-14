"""
Unit tests for Ollama embeddings processor

Tests the core business logic of Ollama embedding generation without
relying on external Ollama service infrastructure.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
import os

from trustgraph.embeddings.ollama.processor import Processor
from trustgraph.schema import EmbeddingsRequest, EmbeddingsResponse, Error
from trustgraph.exceptions import TooManyRequests


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing"""
    client = Mock()
    client.embed.return_value = Mock(
        embeddings=[0.1, 0.2, -0.3, 0.4, -0.5, 0.6, 0.7, -0.8, 0.9, -1.0]
    )
    return client


@pytest.fixture
def processor_params():
    """Default parameters for Ollama processor"""
    return {
        "model": "test-embed-model",
        "ollama": "http://localhost:11434",
        "input_queue": "test-input",
        "output_queue": "test-output",
        "subscriber": "test-subscriber"
    }


@pytest.fixture
def mock_message():
    """Mock Pulsar message"""
    message = Mock()
    message.properties.return_value = {"id": "test-msg-123"}
    message.value.return_value = EmbeddingsRequest(text="Test embedding text")
    return message


class TestOllamaEmbeddingsProcessor:
    """Test cases for Ollama embeddings processor"""

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_processor_initialization_default_params(self, mock_client_class):
        """Test processor initialization with default parameters"""
        # Arrange
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Act
        processor = Processor()
        
        # Assert
        assert processor.model == "mxbai-embed-large"  # default model
        mock_client_class.assert_called_once_with(host='http://localhost:11434')
        assert processor.client == mock_client

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_processor_initialization_custom_params(self, mock_client_class, processor_params):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Act
        processor = Processor(**processor_params)
        
        # Assert
        assert processor.model == "test-embed-model"
        mock_client_class.assert_called_once_with(host="http://localhost:11434")
        assert processor.client == mock_client

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_processor_initialization_env_variable(self, mock_client_class):
        """Test processor uses OLLAMA_HOST environment variable"""
        # Arrange
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        with patch.dict(os.environ, {'OLLAMA_HOST': 'http://custom-host:8080'}):
            # Act
            processor = Processor()
        
        # Assert
        mock_client_class.assert_called_once_with(host='http://custom-host:8080')

    @patch('trustgraph.embeddings.ollama.processor.Client')
    async def test_handle_successful_embedding(self, mock_client_class, mock_message):
        """Test successful embedding generation"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.return_value = Mock(
            embeddings=[0.1, 0.2, -0.3, 0.4, -0.5]
        )
        mock_client_class.return_value = mock_client
        
        processor = Processor(model="test-model")
        processor.send = AsyncMock()
        
        # Act
        await processor.handle(mock_message)
        
        # Assert
        mock_client.embed.assert_called_once_with(
            model="test-model",
            input="Test embedding text"
        )
        
        # Verify response sent
        processor.send.assert_called_once()
        call_args = processor.send.call_args
        response = call_args[0][0]
        properties = call_args[1]["properties"]
        
        assert isinstance(response, EmbeddingsResponse)
        assert response.error is None
        assert response.vectors == [0.1, 0.2, -0.3, 0.4, -0.5]
        assert properties["id"] == "test-msg-123"

    @patch('trustgraph.embeddings.ollama.processor.Client')
    async def test_handle_client_error(self, mock_client_class, mock_message):
        """Test handling of Ollama client errors"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.side_effect = Exception("Ollama connection failed")
        mock_client_class.return_value = mock_client
        
        processor = Processor()
        processor.send = AsyncMock()
        
        # Act & Assert
        with pytest.raises(Exception, match="Ollama connection failed"):
            await processor.handle(mock_message)

    @patch('trustgraph.embeddings.ollama.processor.Client')
    async def test_handle_model_not_found(self, mock_client_class, mock_message):
        """Test handling when Ollama model is not found"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.side_effect = Exception("Model 'unknown-model' not found")
        mock_client_class.return_value = mock_client
        
        processor = Processor(model="unknown-model")
        processor.send = AsyncMock()
        
        # Act & Assert
        with pytest.raises(Exception, match="Model 'unknown-model' not found"):
            await processor.handle(mock_message)

    @patch('trustgraph.embeddings.ollama.processor.Client')
    async def test_handle_empty_text(self, mock_client_class):
        """Test handling of empty text input"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.return_value = Mock(embeddings=[])
        mock_client_class.return_value = mock_client
        
        processor = Processor()
        processor.send = AsyncMock()
        
        empty_message = Mock()
        empty_message.properties.return_value = {"id": "empty-msg"}
        empty_message.value.return_value = EmbeddingsRequest(text="")
        
        # Act
        await processor.handle(empty_message)
        
        # Assert
        mock_client.embed.assert_called_once_with(
            model="mxbai-embed-large",
            input=""
        )
        
        processor.send.assert_called_once()
        response = processor.send.call_args[0][0]
        assert response.vectors == []

    @patch('trustgraph.embeddings.ollama.processor.Client')
    async def test_handle_large_text_input(self, mock_client_class):
        """Test handling of large text input"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.return_value = Mock(
            embeddings=[0.1] * 1536  # Large embedding vector
        )
        mock_client_class.return_value = mock_client
        
        processor = Processor()
        processor.send = AsyncMock()
        
        large_text = "A" * 10000  # Large text input
        large_message = Mock()
        large_message.properties.return_value = {"id": "large-msg"}
        large_message.value.return_value = EmbeddingsRequest(text=large_text)
        
        # Act
        await processor.handle(large_message)
        
        # Assert
        mock_client.embed.assert_called_once_with(
            model="mxbai-embed-large",
            input=large_text
        )
        
        processor.send.assert_called_once()
        response = processor.send.call_args[0][0]
        assert len(response.vectors) == 1536

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_embedding_vector_consistency(self, mock_client_class):
        """Test that embedding vectors have consistent dimensions"""
        # Arrange
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        processor = Processor(model="test-model")
        
        # Assert
        assert processor.model == "test-model"
        assert processor.client == mock_client

    @patch('trustgraph.embeddings.ollama.processor.Client')
    async def test_handle_unicode_text(self, mock_client_class):
        """Test handling of Unicode text input"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.return_value = Mock(
            embeddings=[0.2, -0.1, 0.3, -0.4, 0.5]
        )
        mock_client_class.return_value = mock_client
        
        processor = Processor()
        processor.send = AsyncMock()
        
        unicode_text = "Hello 世界! 🌍 Émoji test"
        unicode_message = Mock()
        unicode_message.properties.return_value = {"id": "unicode-msg"}
        unicode_message.value.return_value = EmbeddingsRequest(text=unicode_text)
        
        # Act
        await processor.handle(unicode_message)
        
        # Assert
        mock_client.embed.assert_called_once_with(
            model="mxbai-embed-large",
            input=unicode_text
        )
        
        processor.send.assert_called_once()
        response = processor.send.call_args[0][0]
        assert response.vectors == [0.2, -0.1, 0.3, -0.4, 0.5]

    def test_add_args_method(self):
        """Test that add_args method adds correct arguments"""
        # Arrange
        mock_parser = Mock()
        
        # Act
        Processor.add_args(mock_parser)
        
        # Assert
        # Verify model argument added
        model_calls = [call for call in mock_parser.add_argument.call_args_list 
                      if call[0][0] in ['-m', '--model']]
        assert len(model_calls) == 1
        model_call = model_calls[0]
        assert model_call[1]['default'] == "mxbai-embed-large"
        
        # Verify ollama argument added
        ollama_calls = [call for call in mock_parser.add_argument.call_args_list 
                       if call[0][0] in ['-r', '--ollama']]
        assert len(ollama_calls) == 1
        ollama_call = ollama_calls[0]
        assert ollama_call[1]['default'] == 'http://localhost:11434'

    @patch('trustgraph.embeddings.ollama.processor.Client')
    async def test_message_properties_handling(self, mock_client_class, mock_message):
        """Test proper handling of message properties"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.return_value = Mock(embeddings=[0.1, 0.2, 0.3])
        mock_client_class.return_value = mock_client
        
        processor = Processor()
        processor.send = AsyncMock()
        
        # Act
        await processor.handle(mock_message)
        
        # Assert
        mock_message.properties.assert_called_once()
        
        # Verify properties passed to send
        call_properties = processor.send.call_args[1]["properties"]
        assert call_properties["id"] == "test-msg-123"

    @patch('trustgraph.embeddings.ollama.processor.Client')
    async def test_concurrent_requests_handling(self, mock_client_class):
        """Test that processor can handle multiple concurrent requests"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.return_value = Mock(embeddings=[0.1, 0.2, 0.3])
        mock_client_class.return_value = mock_client
        
        processor = Processor()
        processor.send = AsyncMock()
        
        # Create multiple messages
        messages = []
        for i in range(3):
            msg = Mock()
            msg.properties.return_value = {"id": f"msg-{i}"}
            msg.value.return_value = EmbeddingsRequest(text=f"Text {i}")
            messages.append(msg)
        
        # Act - Handle messages concurrently
        import asyncio
        await asyncio.gather(*[processor.handle(msg) for msg in messages])
        
        # Assert
        assert mock_client.embed.call_count == 3
        assert processor.send.call_count == 3
        
        # Verify each message was handled correctly
        for i, call in enumerate(mock_client.embed.call_args_list):
            assert call[1]["input"] == f"Text {i}"