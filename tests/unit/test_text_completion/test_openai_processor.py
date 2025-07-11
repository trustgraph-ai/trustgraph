"""
Unit tests for trustgraph.model.text_completion.openai
Following the same successful pattern as VertexAI and Ollama tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.openai.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestOpenAIProcessorSimple(IsolatedAsyncioTestCase):
    """Test OpenAI processor functionality"""

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test basic processor initialization"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-api-key',
            'url': 'https://api.openai.com/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'gpt-3.5-turbo'
        assert processor.temperature == 0.0
        assert processor.max_output == 4096
        assert hasattr(processor, 'openai')
        mock_openai_class.assert_called_once_with(base_url='https://api.openai.com/v1', api_key='test-api-key')

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test successful content generation"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response from OpenAI"
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 12
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-api-key',
            'url': 'https://api.openai.com/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Generated response from OpenAI"
        assert result.in_token == 20
        assert result.out_token == 12
        assert result.model == 'gpt-3.5-turbo'
        
        # Verify the OpenAI API call
        mock_openai_client.chat.completions.create.assert_called_once_with(
            model='gpt-3.5-turbo',
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": "System prompt\n\nUser prompt"
                }]
            }],
            temperature=0.0,
            max_tokens=4096,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            response_format={"type": "text"}
        )

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_rate_limit_error(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test rate limit error handling"""
        # Arrange
        from openai import RateLimitError
        
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-api-key',
            'url': 'https://api.openai.com/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(TooManyRequests):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test handling of generic exceptions"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = Exception("API connection error")
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-api-key',
            'url': 'https://api.openai.com/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="API connection error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_api_key(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test processor initialization without API key (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-3.5-turbo',
            'api_key': None,  # No API key provided
            'url': 'https://api.openai.com/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="OpenAI API key not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-4',
            'api_key': 'custom-api-key',
            'url': 'https://custom-openai-url.com/v1',
            'temperature': 0.7,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'gpt-4'
        assert processor.temperature == 0.7
        assert processor.max_output == 2048
        mock_openai_class.assert_called_once_with(base_url='https://custom-openai-url.com/v1', api_key='custom-api-key')

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test processor initialization with default values"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        # Only provide required fields, should use defaults
        config = {
            'api_key': 'test-api-key',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'gpt-3.5-turbo'  # default_model
        assert processor.temperature == 0.0  # default_temperature
        assert processor.max_output == 4096  # default_max_output
        mock_openai_class.assert_called_once_with(base_url='https://api.openai.com/v1', api_key='test-api-key')

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test content generation with empty prompts"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Default response"
        mock_response.usage.prompt_tokens = 2
        mock_response.usage.completion_tokens = 3
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-api-key',
            'url': 'https://api.openai.com/v1',
            'temperature': 0.0,
            'max_output': 4096,
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
        assert result.model == 'gpt-3.5-turbo'
        
        # Verify the combined prompt is sent correctly
        call_args = mock_openai_client.chat.completions.create.call_args
        expected_prompt = "\n\n"  # Empty system + "\n\n" + empty user
        assert call_args[1]['messages'][0]['content'][0]['text'] == expected_prompt

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_openai_client_initialization_without_base_url(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test OpenAI client initialization without base_url"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-api-key',
            'url': None,  # No base URL
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert - should be called without base_url when it's None
        mock_openai_class.assert_called_once_with(api_key='test-api-key')

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_message_structure(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that OpenAI messages are structured correctly"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response with proper structure"
        mock_response.usage.prompt_tokens = 25
        mock_response.usage.completion_tokens = 15
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-api-key',
            'url': 'https://api.openai.com/v1',
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
        
        # Verify the message structure matches OpenAI Chat API format
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'][0]['type'] == 'text'
        assert messages[0]['content'][0]['text'] == "You are a helpful assistant\n\nWhat is AI?"
        
        # Verify other parameters
        assert call_args[1]['model'] == 'gpt-3.5-turbo'
        assert call_args[1]['temperature'] == 0.5
        assert call_args[1]['max_tokens'] == 1024
        assert call_args[1]['top_p'] == 1
        assert call_args[1]['frequency_penalty'] == 0
        assert call_args[1]['presence_penalty'] == 0
        assert call_args[1]['response_format'] == {"type": "text"}


if __name__ == '__main__':
    pytest.main([__file__])