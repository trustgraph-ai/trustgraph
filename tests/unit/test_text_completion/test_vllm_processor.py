"""
Unit tests for trustgraph.model.text_completion.vllm
Following the same successful pattern as previous tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.vllm.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestVLLMProcessorSimple(IsolatedAsyncioTestCase):
    """Test vLLM processor functionality"""

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test basic processor initialization"""
        # Arrange
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'TheBloke/Mistral-7B-v0.1-AWQ',
            'url': 'http://vllm-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'TheBloke/Mistral-7B-v0.1-AWQ'
        assert processor.base_url == 'http://vllm-service:8899/v1'
        assert processor.temperature == 0.0
        assert processor.max_output == 2048
        assert hasattr(processor, 'session')
        mock_session_class.assert_called_once()

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test successful content generation"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'text': 'Generated response from vLLM'
            }],
            'usage': {
                'prompt_tokens': 20,
                'completion_tokens': 12
            }
        })
        
        # Mock the async context manager
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'TheBloke/Mistral-7B-v0.1-AWQ',
            'url': 'http://vllm-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Generated response from vLLM"
        assert result.in_token == 20
        assert result.out_token == 12
        assert result.model == 'TheBloke/Mistral-7B-v0.1-AWQ'
        
        # Verify the vLLM API call
        mock_session.post.assert_called_once_with(
            'http://vllm-service:8899/v1/completions',
            headers={'Content-Type': 'application/json'},
            json={
                'model': 'TheBloke/Mistral-7B-v0.1-AWQ',
                'prompt': 'System prompt\n\nUser prompt',
                'max_tokens': 2048,
                'temperature': 0.0
            }
        )

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_http_error(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test HTTP error handling"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 500
        
        # Mock the async context manager
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'TheBloke/Mistral-7B-v0.1-AWQ',
            'url': 'http://vllm-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(RuntimeError, match="Bad status: 500"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test handling of generic exceptions"""
        # Arrange
        mock_session = MagicMock()
        mock_session.post.side_effect = Exception("Connection error")
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'TheBloke/Mistral-7B-v0.1-AWQ',
            'url': 'http://vllm-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="Connection error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'custom-model',
            'url': 'http://custom-vllm:8080/v1',
            'temperature': 0.7,
            'max_output': 1024,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'custom-model'
        assert processor.base_url == 'http://custom-vllm:8080/v1'
        assert processor.temperature == 0.7
        assert processor.max_output == 1024
        mock_session_class.assert_called_once()

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test processor initialization with default values"""
        # Arrange
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        # Only provide required fields, should use defaults
        config = {
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'TheBloke/Mistral-7B-v0.1-AWQ'  # default_model
        assert processor.base_url == 'http://vllm-service:8899/v1'  # default_base_url
        assert processor.temperature == 0.0  # default_temperature
        assert processor.max_output == 2048  # default_max_output
        mock_session_class.assert_called_once()

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test content generation with empty prompts"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'text': 'Default response'
            }],
            'usage': {
                'prompt_tokens': 2,
                'completion_tokens': 3
            }
        })
        
        # Mock the async context manager
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'TheBloke/Mistral-7B-v0.1-AWQ',
            'url': 'http://vllm-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
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
        assert result.model == 'TheBloke/Mistral-7B-v0.1-AWQ'
        
        # Verify the combined prompt is sent correctly
        call_args = mock_session.post.call_args
        expected_prompt = "\n\n"  # Empty system + "\n\n" + empty user
        assert call_args[1]['json']['prompt'] == expected_prompt

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_request_structure(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test that vLLM request is structured correctly"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'text': 'Response with proper structure'
            }],
            'usage': {
                'prompt_tokens': 25,
                'completion_tokens': 15
            }
        })
        
        # Mock the async context manager
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'TheBloke/Mistral-7B-v0.1-AWQ',
            'url': 'http://vllm-service:8899/v1',
            'temperature': 0.5,
            'max_output': 1024,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("You are a helpful assistant", "What is AI?")

        # Assert
        assert result.text == "Response with proper structure"
        assert result.in_token == 25
        assert result.out_token == 15
        
        # Verify the request structure
        call_args = mock_session.post.call_args
        
        # Check URL
        assert call_args[0][0] == 'http://vllm-service:8899/v1/completions'
        
        # Check headers
        assert call_args[1]['headers']['Content-Type'] == 'application/json'
        
        # Check request body
        request_data = call_args[1]['json']
        assert request_data['model'] == 'TheBloke/Mistral-7B-v0.1-AWQ'
        assert request_data['prompt'] == "You are a helpful assistant\n\nWhat is AI?"
        assert request_data['temperature'] == 0.5
        assert request_data['max_tokens'] == 1024

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_vllm_session_initialization(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test that aiohttp session is initialized correctly"""
        # Arrange
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'test-model',
            'url': 'http://test-vllm:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify ClientSession was created
        mock_session_class.assert_called_once()
        
        # Verify processor has the session
        assert processor.session == mock_session

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_response_parsing(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test response parsing from vLLM API"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'text': 'Parsed response text'
            }],
            'usage': {
                'prompt_tokens': 35,
                'completion_tokens': 25
            }
        })
        
        # Mock the async context manager
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'TheBloke/Mistral-7B-v0.1-AWQ',
            'url': 'http://vllm-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System", "User query")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Parsed response text"
        assert result.in_token == 35
        assert result.out_token == 25
        assert result.model == 'TheBloke/Mistral-7B-v0.1-AWQ'

    @patch('trustgraph.model.text_completion.vllm.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_prompt_construction(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test prompt construction with system and user prompts"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'text': 'Response with system instructions'
            }],
            'usage': {
                'prompt_tokens': 40,
                'completion_tokens': 30
            }
        })
        
        # Mock the async context manager
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'TheBloke/Mistral-7B-v0.1-AWQ',
            'url': 'http://vllm-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("You are a helpful assistant", "What is machine learning?")

        # Assert
        assert result.text == "Response with system instructions"
        assert result.in_token == 40
        assert result.out_token == 30
        
        # Verify the combined prompt
        call_args = mock_session.post.call_args
        expected_prompt = "You are a helpful assistant\n\nWhat is machine learning?"
        assert call_args[1]['json']['prompt'] == expected_prompt


if __name__ == '__main__':
    pytest.main([__file__])