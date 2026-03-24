"""
Unit tests for trustgraph.model.text_completion.minimax
Following the same successful pattern as OpenAI and other provider tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.minimax.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestMiniMaxProcessorSimple(IsolatedAsyncioTestCase):
    """Test MiniMax processor functionality"""

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
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
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 1.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'MiniMax-M2.7'
        assert processor.temperature == 1.0
        assert processor.max_output == 4096
        assert hasattr(processor, 'openai')
        mock_openai_class.assert_called_once_with(base_url='https://api.minimax.io/v1', api_key='test-api-key')

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test successful content generation"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response from MiniMax"
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 12

        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 1.0,
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
        assert result.text == "Generated response from MiniMax"
        assert result.in_token == 20
        assert result.out_token == 12
        assert result.model == 'MiniMax-M2.7'

        # Verify the API call
        mock_openai_client.chat.completions.create.assert_called_once_with(
            model='MiniMax-M2.7',
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": "System prompt\n\nUser prompt"
                }]
            }],
            temperature=1.0,
            max_tokens=4096
        )

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
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
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 1.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(TooManyRequests):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
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
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 1.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="API connection error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_api_key(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test processor initialization without API key (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'MiniMax-M2.7',
            'api_key': None,  # No API key provided
            'url': 'https://api.minimax.io/v1',
            'temperature': 1.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="MiniMax API key not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
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
            'model': 'MiniMax-M2.7-highspeed',
            'api_key': 'custom-api-key',
            'url': 'https://custom-minimax-url.com/v1',
            'temperature': 0.7,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'MiniMax-M2.7-highspeed'
        assert processor.temperature == 0.7
        assert processor.max_output == 2048
        mock_openai_class.assert_called_once_with(base_url='https://custom-minimax-url.com/v1', api_key='custom-api-key')

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
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
        assert processor.default_model == 'MiniMax-M2.7'  # default_model
        assert processor.temperature == 1.0  # default_temperature
        assert processor.max_output == 4096  # default_max_output
        mock_openai_class.assert_called_once_with(base_url='https://api.minimax.io/v1', api_key='test-api-key')

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_temperature_clamping_zero(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that temperature 0.0 is clamped to 0.01"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 0.0,  # Should be clamped to 0.01
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.temperature == 0.01  # Clamped from 0.0

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_temperature_clamping_above_one(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that temperature above 1.0 is clamped to 1.0"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 1.5,  # Should be clamped to 1.0
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.temperature == 1.0  # Clamped from 1.5

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_temperature_clamping_at_runtime(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that runtime temperature override is also clamped"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 0.5,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override temperature with 0.0 at runtime
        await processor.generate_content("System", "User", temperature=0.0)

        # Assert - temperature should be clamped to 0.01
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['temperature'] == 0.01

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_temperature_override(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test temperature parameter override functionality"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response with custom temperature"
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 10

        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 1.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override temperature at runtime
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model=None,
            temperature=0.9
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Response with custom temperature"
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['temperature'] == 0.9
        assert call_kwargs['model'] == 'MiniMax-M2.7'

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_model_override(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test model parameter override functionality"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response with custom model"
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 10

        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 0.5,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override model at runtime
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model="MiniMax-M2.7-highspeed",
            temperature=None
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Response with custom model"
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'MiniMax-M2.7-highspeed'
        assert call_kwargs['temperature'] == 0.5

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_supports_streaming(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that MiniMax provider reports streaming support"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 1.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Assert
        assert processor.supports_streaming() is True

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
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
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
            'temperature': 1.0,
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
        call_args = mock_openai_client.chat.completions.create.call_args
        expected_prompt = "\n\n"
        assert call_args[1]['messages'][0]['content'][0]['text'] == expected_prompt

    @patch('trustgraph.model.text_completion.minimax.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_message_structure(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that messages are structured correctly"""
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
            'model': 'MiniMax-M2.7',
            'api_key': 'test-api-key',
            'url': 'https://api.minimax.io/v1',
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

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'][0]['type'] == 'text'
        assert messages[0]['content'][0]['text'] == "You are a helpful assistant\n\nWhat is AI?"

        assert call_args[1]['model'] == 'MiniMax-M2.7'
        assert call_args[1]['temperature'] == 0.5
        assert call_args[1]['max_tokens'] == 1024


if __name__ == '__main__':
    pytest.main([__file__])
