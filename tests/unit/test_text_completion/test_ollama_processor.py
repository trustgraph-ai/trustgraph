"""
Unit tests for trustgraph.model.text_completion.ollama
Following the same successful pattern as VertexAI tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.ollama.llm import Processor
from trustgraph.base import LlmResult


class TestOllamaProcessorSimple(IsolatedAsyncioTestCase):
    """Test Ollama processor functionality"""

    @patch('trustgraph.model.text_completion.ollama.llm.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_client_class):
        """Test basic processor initialization"""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock the parent class initialization
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'llama2',
            'ollama': 'http://localhost:11434',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'llama2'
        assert hasattr(processor, 'llm')
        mock_client_class.assert_called_once_with(host='http://localhost:11434')

    @patch('trustgraph.model.text_completion.ollama.llm.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_client_class):
        """Test successful content generation"""
        # Arrange
        mock_client = MagicMock()
        mock_response = {
            'response': 'Generated response from Ollama',
            'prompt_eval_count': 15,
            'eval_count': 8
        }
        mock_client.generate.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'llama2',
            'ollama': 'http://localhost:11434',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Generated response from Ollama"
        assert result.in_token == 15
        assert result.out_token == 8
        assert result.model == 'llama2'
        mock_client.generate.assert_called_once_with('llama2', "System prompt\n\nUser prompt")

    @patch('trustgraph.model.text_completion.ollama.llm.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_client_class):
        """Test handling of generic exceptions"""
        # Arrange
        mock_client = MagicMock()
        mock_client.generate.side_effect = Exception("Connection error")
        mock_client_class.return_value = mock_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'llama2',
            'ollama': 'http://localhost:11434',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="Connection error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.ollama.llm.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_client_class):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'mistral',
            'ollama': 'http://192.168.1.100:11434',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'mistral'
        mock_client_class.assert_called_once_with(host='http://192.168.1.100:11434')

    @patch('trustgraph.model.text_completion.ollama.llm.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_llm_init, mock_async_init, mock_client_class):
        """Test processor initialization with default values"""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        # Don't provide model or ollama - should use defaults
        config = {
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'gemma2:9b'  # default_model
        # Should use default_ollama (http://localhost:11434 or from OLLAMA_HOST env)
        mock_client_class.assert_called_once()

    @patch('trustgraph.model.text_completion.ollama.llm.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_client_class):
        """Test content generation with empty prompts"""
        # Arrange
        mock_client = MagicMock()
        mock_response = {
            'response': 'Default response',
            'prompt_eval_count': 2,
            'eval_count': 3
        }
        mock_client.generate.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'llama2',
            'ollama': 'http://localhost:11434',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("", "")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Default response"
        assert result.in_token == 2
        assert result.out_token == 3
        assert result.model == 'llama2'
        
        # The prompt should be "" + "\n\n" + "" = "\n\n"
        mock_client.generate.assert_called_once_with('llama2', "\n\n")

    @patch('trustgraph.model.text_completion.ollama.llm.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_token_counting(self, mock_llm_init, mock_async_init, mock_client_class):
        """Test token counting from Ollama response"""
        # Arrange
        mock_client = MagicMock()
        mock_response = {
            'response': 'Test response',
            'prompt_eval_count': 50,
            'eval_count': 25
        }
        mock_client.generate.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'llama2',
            'ollama': 'http://localhost:11434',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Test response"
        assert result.in_token == 50
        assert result.out_token == 25
        assert result.model == 'llama2'

    @patch('trustgraph.model.text_completion.ollama.llm.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_ollama_client_initialization(self, mock_llm_init, mock_async_init, mock_client_class):
        """Test that Ollama client is initialized correctly"""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'codellama',
            'ollama': 'http://ollama-server:11434',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify Client was called with correct host
        mock_client_class.assert_called_once_with(host='http://ollama-server:11434')
        
        # Verify processor has the client
        assert processor.llm == mock_client

    @patch('trustgraph.model.text_completion.ollama.llm.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_prompt_construction(self, mock_llm_init, mock_async_init, mock_client_class):
        """Test prompt construction with system and user prompts"""
        # Arrange
        mock_client = MagicMock()
        mock_response = {
            'response': 'Response with system instructions',
            'prompt_eval_count': 25,
            'eval_count': 15
        }
        mock_client.generate.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'llama2',
            'ollama': 'http://localhost:11434',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("You are a helpful assistant", "What is AI?")

        # Assert
        assert result.text == "Response with system instructions"
        assert result.in_token == 25
        assert result.out_token == 15
        
        # Verify the combined prompt
        mock_client.generate.assert_called_once_with('llama2', "You are a helpful assistant\n\nWhat is AI?")


if __name__ == '__main__':
    pytest.main([__file__])