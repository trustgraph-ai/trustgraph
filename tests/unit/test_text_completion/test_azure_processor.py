"""
Unit tests for trustgraph.model.text_completion.azure
Following the same successful pattern as previous tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.azure.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestAzureProcessorSimple(IsolatedAsyncioTestCase):
    """Test Azure processor functionality"""

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_requests):
        """Test basic processor initialization"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': 'test-token',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.endpoint == 'https://test.inference.ai.azure.com/v1/chat/completions'
        assert processor.token == 'test-token'
        assert processor.temperature == 0.0
        assert processor.max_output == 4192
        assert processor.default_model == 'AzureAI'

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_requests):
        """Test successful content generation"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Generated response from Azure'
                }
            }],
            'usage': {
                'prompt_tokens': 20,
                'completion_tokens': 12
            }
        }
        mock_requests.post.return_value = mock_response
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': 'test-token',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Generated response from Azure"
        assert result.in_token == 20
        assert result.out_token == 12
        assert result.model == 'AzureAI'
        
        # Verify the API call was made correctly
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        
        # Check URL
        assert call_args[0][0] == 'https://test.inference.ai.azure.com/v1/chat/completions'
        
        # Check headers
        headers = call_args[1]['headers']
        assert headers['Content-Type'] == 'application/json'
        assert headers['Authorization'] == 'Bearer test-token'

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_rate_limit_error(self, mock_llm_init, mock_async_init, mock_requests):
        """Test rate limit error handling"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_requests.post.return_value = mock_response
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': 'test-token',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(TooManyRequests):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_http_error(self, mock_llm_init, mock_async_init, mock_requests):
        """Test HTTP error handling"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests.post.return_value = mock_response
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': 'test-token',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(RuntimeError, match="LLM failure"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_requests):
        """Test handling of generic exceptions"""
        # Arrange
        mock_requests.post.side_effect = Exception("Connection error")
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': 'test-token',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="Connection error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_endpoint(self, mock_llm_init, mock_async_init, mock_requests):
        """Test processor initialization without endpoint (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': None,  # No endpoint provided
            'token': 'test-token',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="Azure endpoint not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_token(self, mock_llm_init, mock_async_init, mock_requests):
        """Test processor initialization without token (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': None,  # No token provided
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="Azure token not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_requests):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://custom.inference.ai.azure.com/v1/chat/completions',
            'token': 'custom-token',
            'temperature': 0.7,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.endpoint == 'https://custom.inference.ai.azure.com/v1/chat/completions'
        assert processor.token == 'custom-token'
        assert processor.temperature == 0.7
        assert processor.max_output == 2048
        assert processor.default_model == 'AzureAI'

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_llm_init, mock_async_init, mock_requests):
        """Test processor initialization with default values"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        # Only provide required fields, should use defaults
        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': 'test-token',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.endpoint == 'https://test.inference.ai.azure.com/v1/chat/completions'
        assert processor.token == 'test-token'
        assert processor.temperature == 0.0  # default_temperature
        assert processor.max_output == 4192  # default_max_output
        assert processor.default_model == 'AzureAI'  # default_model

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_requests):
        """Test content generation with empty prompts"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Default response'
                }
            }],
            'usage': {
                'prompt_tokens': 2,
                'completion_tokens': 3
            }
        }
        mock_requests.post.return_value = mock_response
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': 'test-token',
            'temperature': 0.0,
            'max_output': 4192,
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
        assert result.model == 'AzureAI'

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_build_prompt_structure(self, mock_llm_init, mock_async_init, mock_requests):
        """Test that build_prompt creates correct message structure"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Response with proper structure'
                }
            }],
            'usage': {
                'prompt_tokens': 25,
                'completion_tokens': 15
            }
        }
        mock_requests.post.return_value = mock_response
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': 'test-token',
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
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        
        # Parse the request body
        import json
        request_body = json.loads(call_args[1]['data'])
        
        # Verify message structure
        assert 'messages' in request_body
        assert len(request_body['messages']) == 2
        
        # Check system message
        assert request_body['messages'][0]['role'] == 'system'
        assert request_body['messages'][0]['content'] == 'You are a helpful assistant'
        
        # Check user message
        assert request_body['messages'][1]['role'] == 'user'
        assert request_body['messages'][1]['content'] == 'What is AI?'
        
        # Check parameters
        assert request_body['temperature'] == 0.5
        assert request_body['max_tokens'] == 1024
        assert request_body['top_p'] == 1

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_call_llm_method(self, mock_llm_init, mock_async_init, mock_requests):
        """Test the call_llm method directly"""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Test response'
                }
            }],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 5
            }
        }
        mock_requests.post.return_value = mock_response
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
            'token': 'test-token',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = processor.call_llm('{"test": "body"}')

        # Assert
        assert result == mock_response.json.return_value
        
        # Verify the request was made correctly
        mock_requests.post.assert_called_once_with(
            'https://test.inference.ai.azure.com/v1/chat/completions',
            data='{"test": "body"}',
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer test-token'
            }
        )


if __name__ == '__main__':
    pytest.main([__file__])