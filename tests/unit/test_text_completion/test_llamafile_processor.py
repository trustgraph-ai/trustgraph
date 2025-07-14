"""
Unit tests for trustgraph.model.text_completion.llamafile
Following the same successful pattern as previous tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.llamafile.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestLlamaFileProcessorSimple(IsolatedAsyncioTestCase):
    """Test LlamaFile processor functionality"""

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
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
            'model': 'LLaMA_CPP',
            'llamafile': 'http://localhost:8080/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'LLaMA_CPP'
        assert processor.llamafile == 'http://localhost:8080/v1'
        assert processor.temperature == 0.0
        assert processor.max_output == 4096
        assert hasattr(processor, 'openai')
        mock_openai_class.assert_called_once_with(
            base_url='http://localhost:8080/v1',
            api_key='sk-no-key-required'
        )

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test successful content generation"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response from LlamaFile"
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 12
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'LLaMA_CPP',
            'llamafile': 'http://localhost:8080/v1',
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
        assert result.text == "Generated response from LlamaFile"
        assert result.in_token == 20
        assert result.out_token == 12
        assert result.model == 'llama.cpp'  # Note: model in result is hardcoded to 'llama.cpp'
        
        # Verify the OpenAI API call structure
        mock_openai_client.chat.completions.create.assert_called_once_with(
            model='LLaMA_CPP',
            messages=[{
                "role": "user",
                "content": "System prompt\n\nUser prompt"
            }]
        )

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test handling of generic exceptions"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = Exception("Connection error")
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'LLaMA_CPP',
            'llamafile': 'http://localhost:8080/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="Connection error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
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
            'model': 'custom-llama',
            'llamafile': 'http://custom-host:8080/v1',
            'temperature': 0.7,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'custom-llama'
        assert processor.llamafile == 'http://custom-host:8080/v1'
        assert processor.temperature == 0.7
        assert processor.max_output == 2048
        mock_openai_class.assert_called_once_with(
            base_url='http://custom-host:8080/v1',
            api_key='sk-no-key-required'
        )

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
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
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'LLaMA_CPP'  # default_model
        assert processor.llamafile == 'http://localhost:8080/v1'  # default_llamafile
        assert processor.temperature == 0.0  # default_temperature
        assert processor.max_output == 4096  # default_max_output
        mock_openai_class.assert_called_once_with(
            base_url='http://localhost:8080/v1',
            api_key='sk-no-key-required'
        )

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
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
            'model': 'LLaMA_CPP',
            'llamafile': 'http://localhost:8080/v1',
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
        assert result.model == 'llama.cpp'
        
        # Verify the combined prompt is sent correctly
        call_args = mock_openai_client.chat.completions.create.call_args
        expected_prompt = "\n\n"  # Empty system + "\n\n" + empty user
        assert call_args[1]['messages'][0]['content'] == expected_prompt

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_message_structure(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that LlamaFile messages are structured correctly"""
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
            'model': 'LLaMA_CPP',
            'llamafile': 'http://localhost:8080/v1',
            'temperature': 0.0,
            'max_output': 4096,
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
        
        # Verify the message structure
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'] == "You are a helpful assistant\n\nWhat is AI?"
        
        # Verify model parameter
        assert call_args[1]['model'] == 'LLaMA_CPP'

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_openai_client_initialization(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that OpenAI client is initialized correctly for LlamaFile"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'llama-custom',
            'llamafile': 'http://llamafile-server:8080/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify OpenAI client was called with correct parameters
        mock_openai_class.assert_called_once_with(
            base_url='http://llamafile-server:8080/v1',
            api_key='sk-no-key-required'
        )
        
        # Verify processor has the client
        assert processor.openai == mock_openai_client

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_prompt_construction(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test prompt construction with system and user prompts"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response with system instructions"
        mock_response.usage.prompt_tokens = 30
        mock_response.usage.completion_tokens = 20
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'LLaMA_CPP',
            'llamafile': 'http://localhost:8080/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("You are a helpful assistant", "What is machine learning?")

        # Assert
        assert result.text == "Response with system instructions"
        assert result.in_token == 30
        assert result.out_token == 20
        
        # Verify the combined prompt
        call_args = mock_openai_client.chat.completions.create.call_args
        expected_prompt = "You are a helpful assistant\n\nWhat is machine learning?"
        assert call_args[1]['messages'][0]['content'] == expected_prompt

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_hardcoded_model_response(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that response model is hardcoded to 'llama.cpp'"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 10
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'custom-model-name',  # This should be ignored in response
            'llamafile': 'http://localhost:8080/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System", "User")

        # Assert
        assert result.model == 'llama.cpp'  # Should always be 'llama.cpp', not 'custom-model-name'
        assert processor.model == 'custom-model-name'  # But processor.model should still be custom

    @patch('trustgraph.model.text_completion.llamafile.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_no_rate_limiting(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test that no rate limiting is implemented (SLM assumption)"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "No rate limiting test"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'LLaMA_CPP',
            'llamafile': 'http://localhost:8080/v1',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System", "User")

        # Assert
        assert result.text == "No rate limiting test"
        # No specific rate limit error handling tested since SLM presumably has no rate limits


if __name__ == '__main__':
    pytest.main([__file__])