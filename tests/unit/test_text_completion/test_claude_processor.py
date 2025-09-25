"""
Unit tests for trustgraph.model.text_completion.claude
Following the same successful pattern as previous tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.claude.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestClaudeProcessorSimple(IsolatedAsyncioTestCase):
    """Test Claude processor functionality"""

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test basic processor initialization"""
        # Arrange
        mock_claude_client = MagicMock()
        mock_anthropic_class.return_value = mock_claude_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-5-sonnet-20240620',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'claude-3-5-sonnet-20240620'
        assert processor.temperature == 0.0
        assert processor.max_output == 8192
        assert hasattr(processor, 'claude')
        mock_anthropic_class.assert_called_once_with(api_key='test-api-key')

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test successful content generation"""
        # Arrange
        mock_claude_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Generated response from Claude"
        mock_response.usage.input_tokens = 25
        mock_response.usage.output_tokens = 15
        
        mock_claude_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_claude_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-5-sonnet-20240620',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Generated response from Claude"
        assert result.in_token == 25
        assert result.out_token == 15
        assert result.model == 'claude-3-5-sonnet-20240620'
        
        # Verify the Claude API call
        mock_claude_client.messages.create.assert_called_once_with(
            model='claude-3-5-sonnet-20240620',
            max_tokens=8192,
            temperature=0.0,
            system="System prompt",
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": "User prompt"
                }]
            }]
        )

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_rate_limit_error(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test rate limit error handling"""
        # Arrange
        import anthropic
        
        mock_claude_client = MagicMock()
        mock_claude_client.messages.create.side_effect = anthropic.RateLimitError(
            "Rate limit exceeded", 
            response=MagicMock(), 
            body=None
        )
        mock_anthropic_class.return_value = mock_claude_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-5-sonnet-20240620',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(TooManyRequests):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test handling of generic exceptions"""
        # Arrange
        mock_claude_client = MagicMock()
        mock_claude_client.messages.create.side_effect = Exception("API connection error")
        mock_anthropic_class.return_value = mock_claude_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-5-sonnet-20240620',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="API connection error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_api_key(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test processor initialization without API key (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-5-sonnet-20240620',
            'api_key': None,  # No API key provided
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="Claude API key not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_claude_client = MagicMock()
        mock_anthropic_class.return_value = mock_claude_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-haiku-20240307',
            'api_key': 'custom-api-key',
            'temperature': 0.7,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'claude-3-haiku-20240307'
        assert processor.temperature == 0.7
        assert processor.max_output == 4096
        mock_anthropic_class.assert_called_once_with(api_key='custom-api-key')

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test processor initialization with default values"""
        # Arrange
        mock_claude_client = MagicMock()
        mock_anthropic_class.return_value = mock_claude_client
        
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
        assert processor.default_model == 'claude-3-5-sonnet-20240620'  # default_model
        assert processor.temperature == 0.0  # default_temperature
        assert processor.max_output == 8192  # default_max_output
        mock_anthropic_class.assert_called_once_with(api_key='test-api-key')

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test content generation with empty prompts"""
        # Arrange
        mock_claude_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Default response"
        mock_response.usage.input_tokens = 2
        mock_response.usage.output_tokens = 3
        
        mock_claude_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_claude_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-5-sonnet-20240620',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 8192,
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
        assert result.model == 'claude-3-5-sonnet-20240620'
        
        # Verify the system prompt and user content are handled correctly
        call_args = mock_claude_client.messages.create.call_args
        assert call_args[1]['system'] == ""
        assert call_args[1]['messages'][0]['content'][0]['text'] == ""

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_message_structure(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test that Claude messages are structured correctly"""
        # Arrange
        mock_claude_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Response with proper structure"
        mock_response.usage.input_tokens = 30
        mock_response.usage.output_tokens = 20
        
        mock_claude_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_claude_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-5-sonnet-20240620',
            'api_key': 'test-api-key',
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
        assert result.in_token == 30
        assert result.out_token == 20
        
        # Verify the message structure matches Claude API format
        call_args = mock_claude_client.messages.create.call_args
        
        # Check system prompt
        assert call_args[1]['system'] == "You are a helpful assistant"
        
        # Check user message structure
        messages = call_args[1]['messages']
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'][0]['type'] == 'text'
        assert messages[0]['content'][0]['text'] == "What is AI?"
        
        # Verify other parameters
        assert call_args[1]['model'] == 'claude-3-5-sonnet-20240620'
        assert call_args[1]['temperature'] == 0.5
        assert call_args[1]['max_tokens'] == 1024

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_multiple_content_blocks(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test handling of multiple content blocks in response"""
        # Arrange
        mock_claude_client = MagicMock()
        mock_response = MagicMock()
        
        # Mock multiple content blocks (Claude can return multiple)
        mock_content_1 = MagicMock()
        mock_content_1.text = "First part of response"
        mock_content_2 = MagicMock()
        mock_content_2.text = "Second part of response"
        mock_response.content = [mock_content_1, mock_content_2]
        
        mock_response.usage.input_tokens = 40
        mock_response.usage.output_tokens = 30
        
        mock_claude_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_claude_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-5-sonnet-20240620',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        # Should take the first content block
        assert result.text == "First part of response"
        assert result.in_token == 40
        assert result.out_token == 30
        assert result.model == 'claude-3-5-sonnet-20240620'

    @patch('trustgraph.model.text_completion.claude.llm.anthropic.Anthropic')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_claude_client_initialization(self, mock_llm_init, mock_async_init, mock_anthropic_class):
        """Test that Claude client is initialized correctly"""
        # Arrange
        mock_claude_client = MagicMock()
        mock_anthropic_class.return_value = mock_claude_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'claude-3-opus-20240229',
            'api_key': 'sk-ant-test-key',
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify Anthropic client was called with correct API key
        mock_anthropic_class.assert_called_once_with(api_key='sk-ant-test-key')
        
        # Verify processor has the client
        assert processor.claude == mock_claude_client
        assert processor.default_model == 'claude-3-opus-20240229'


if __name__ == '__main__':
    pytest.main([__file__])