"""
Unit tests for trustgraph.model.text_completion.azure_openai
Following the same successful pattern as previous tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.azure_openai.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestAzureOpenAIProcessorSimple(IsolatedAsyncioTestCase):
    """Test Azure OpenAI processor functionality"""

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test basic processor initialization"""
        # Arrange
        mock_azure_client = MagicMock()
        mock_azure_openai_class.return_value = mock_azure_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-4',
            'endpoint': 'https://test.openai.azure.com/',
            'token': 'test-token',
            'api_version': '2024-12-01-preview',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'gpt-4'
        assert processor.temperature == 0.0
        assert processor.max_output == 4192
        assert hasattr(processor, 'openai')
        mock_azure_openai_class.assert_called_once_with(
            api_key='test-token',
            api_version='2024-12-01-preview',
            azure_endpoint='https://test.openai.azure.com/'
        )

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test successful content generation"""
        # Arrange
        mock_azure_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response from Azure OpenAI"
        mock_response.usage.prompt_tokens = 25
        mock_response.usage.completion_tokens = 15
        
        mock_azure_client.chat.completions.create.return_value = mock_response
        mock_azure_openai_class.return_value = mock_azure_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-4',
            'endpoint': 'https://test.openai.azure.com/',
            'token': 'test-token',
            'api_version': '2024-12-01-preview',
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
        assert result.text == "Generated response from Azure OpenAI"
        assert result.in_token == 25
        assert result.out_token == 15
        assert result.model == 'gpt-4'
        
        # Verify the Azure OpenAI API call
        mock_azure_client.chat.completions.create.assert_called_once_with(
            model='gpt-4',
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": "System prompt\n\nUser prompt"
                }]
            }],
            temperature=0.0,
            max_tokens=4192,
            top_p=1
        )

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_rate_limit_error(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test rate limit error handling"""
        # Arrange
        from openai import RateLimitError
        
        mock_azure_client = MagicMock()
        mock_azure_client.chat.completions.create.side_effect = RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)
        mock_azure_openai_class.return_value = mock_azure_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-4',
            'endpoint': 'https://test.openai.azure.com/',
            'token': 'test-token',
            'api_version': '2024-12-01-preview',
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

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test handling of generic exceptions"""
        # Arrange
        mock_azure_client = MagicMock()
        mock_azure_client.chat.completions.create.side_effect = Exception("Azure API connection error")
        mock_azure_openai_class.return_value = mock_azure_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-4',
            'endpoint': 'https://test.openai.azure.com/',
            'token': 'test-token',
            'api_version': '2024-12-01-preview',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="Azure API connection error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_endpoint(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test processor initialization without endpoint (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-4',
            'endpoint': None,  # No endpoint provided
            'token': 'test-token',
            'api_version': '2024-12-01-preview',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="Azure endpoint not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_token(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test processor initialization without token (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-4',
            'endpoint': 'https://test.openai.azure.com/',
            'token': None,  # No token provided
            'api_version': '2024-12-01-preview',
            'temperature': 0.0,
            'max_output': 4192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="Azure token not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_azure_client = MagicMock()
        mock_azure_openai_class.return_value = mock_azure_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-35-turbo',
            'endpoint': 'https://custom.openai.azure.com/',
            'token': 'custom-token',
            'api_version': '2023-05-15',
            'temperature': 0.7,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'gpt-35-turbo'
        assert processor.temperature == 0.7
        assert processor.max_output == 2048
        mock_azure_openai_class.assert_called_once_with(
            api_key='custom-token',
            api_version='2023-05-15',
            azure_endpoint='https://custom.openai.azure.com/'
        )

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test processor initialization with default values"""
        # Arrange
        mock_azure_client = MagicMock()
        mock_azure_openai_class.return_value = mock_azure_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        # Only provide required fields, should use defaults
        config = {
            'endpoint': 'https://test.openai.azure.com/',
            'token': 'test-token',
            'model': 'gpt-4',  # Required for Azure
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'gpt-4'
        assert processor.temperature == 0.0  # default_temperature
        assert processor.max_output == 4192  # default_max_output
        mock_azure_openai_class.assert_called_once_with(
            api_key='test-token',
            api_version='2024-12-01-preview',  # default_api
            azure_endpoint='https://test.openai.azure.com/'
        )

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test content generation with empty prompts"""
        # Arrange
        mock_azure_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Default response"
        mock_response.usage.prompt_tokens = 2
        mock_response.usage.completion_tokens = 3
        
        mock_azure_client.chat.completions.create.return_value = mock_response
        mock_azure_openai_class.return_value = mock_azure_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-4',
            'endpoint': 'https://test.openai.azure.com/',
            'token': 'test-token',
            'api_version': '2024-12-01-preview',
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
        assert result.model == 'gpt-4'
        
        # Verify the combined prompt is sent correctly
        call_args = mock_azure_client.chat.completions.create.call_args
        expected_prompt = "\n\n"  # Empty system + "\n\n" + empty user
        assert call_args[1]['messages'][0]['content'][0]['text'] == expected_prompt

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_message_structure(self, mock_llm_init, mock_async_init, mock_azure_openai_class):
        """Test that Azure OpenAI messages are structured correctly"""
        # Arrange
        mock_azure_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response with proper structure"
        mock_response.usage.prompt_tokens = 30
        mock_response.usage.completion_tokens = 20
        
        mock_azure_client.chat.completions.create.return_value = mock_response
        mock_azure_openai_class.return_value = mock_azure_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gpt-4',
            'endpoint': 'https://test.openai.azure.com/',
            'token': 'test-token',
            'api_version': '2024-12-01-preview',
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
        
        # Verify the message structure matches Azure OpenAI Chat API format
        call_args = mock_azure_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'][0]['type'] == 'text'
        assert messages[0]['content'][0]['text'] == "You are a helpful assistant\n\nWhat is AI?"
        
        # Verify other parameters
        assert call_args[1]['model'] == 'gpt-4'
        assert call_args[1]['temperature'] == 0.5
        assert call_args[1]['max_tokens'] == 1024
        assert call_args[1]['top_p'] == 1


if __name__ == '__main__':
    pytest.main([__file__])