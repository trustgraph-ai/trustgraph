"""
Unit tests for trustgraph.model.text_completion.lmstudio
Following the same successful pattern as previous tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.lmstudio.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestLMStudioProcessorSimple(IsolatedAsyncioTestCase):
    """Test LMStudio processor functionality"""

    @patch('trustgraph.model.text_completion.lmstudio.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test basic processor initialization"""
        # Arrange
        mock_openai = MagicMock()
        mock_openai_class.return_value = mock_openai

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemma3:9b',
            'url': 'http://localhost:1234/',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'gemma3:9b'
        assert processor.url == 'http://localhost:1234/v1/'
        assert processor.temperature == 0.0
        assert processor.max_output == 4096
        assert hasattr(processor, 'openai')
        mock_openai_class.assert_called_once_with(
            base_url='http://localhost:1234/v1/',
            api_key='sk-no-key-required'
        )

    @patch('trustgraph.model.text_completion.lmstudio.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test successful content generation"""
        # Arrange
        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = 'Generated response from LMStudio'
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 12

        mock_openai.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemma3:9b',
            'url': 'http://localhost:1234/',
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
        assert result.text == "Generated response from LMStudio"
        assert result.in_token == 20
        assert result.out_token == 12
        assert result.model == 'gemma3:9b'

        # Verify the API call was made correctly
        mock_openai.chat.completions.create.assert_called_once()
        call_args = mock_openai.chat.completions.create.call_args

        # Check model and temperature
        assert call_args[1]['model'] == 'gemma3:9b'
        assert call_args[1]['temperature'] == 0.0
        assert call_args[1]['max_tokens'] == 4096

    @patch('trustgraph.model.text_completion.lmstudio.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_with_model_override(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test generate_content with model parameter override"""
        # Arrange
        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = 'Response from overridden model'
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 10

        mock_openai.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemma3:9b',
            'url': 'http://localhost:1234/',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override model
        result = await processor.generate_content("System", "Prompt", model="custom-lmstudio-model")

        # Assert
        assert result.model == "custom-lmstudio-model"  # Should use overridden model
        assert result.text == "Response from overridden model"

        # Verify the API call was made with overridden model
        call_args = mock_openai.chat.completions.create.call_args
        assert call_args[1]['model'] == "custom-lmstudio-model"

    @patch('trustgraph.model.text_completion.lmstudio.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_with_temperature_override(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test generate_content with temperature parameter override"""
        # Arrange
        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = 'Response with temperature override'
        mock_response.usage.prompt_tokens = 18
        mock_response.usage.completion_tokens = 12

        mock_openai.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemma3:9b',
            'url': 'http://localhost:1234/',
            'temperature': 0.0,  # Default temperature
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override temperature
        result = await processor.generate_content("System", "Prompt", temperature=0.7)

        # Assert
        assert result.text == "Response with temperature override"

        # Verify the API call was made with overridden temperature
        call_args = mock_openai.chat.completions.create.call_args
        assert call_args[1]['temperature'] == 0.7

    @patch('trustgraph.model.text_completion.lmstudio.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_with_both_parameters_override(self, mock_llm_init, mock_async_init, mock_openai_class):
        """Test generate_content with both model and temperature overrides"""
        # Arrange
        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = 'Response with both parameters override'
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 15

        mock_openai.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemma3:9b',
            'url': 'http://localhost:1234/',
            'temperature': 0.0,
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override both parameters
        result = await processor.generate_content("System", "Prompt", model="override-model", temperature=0.8)

        # Assert
        assert result.model == "override-model"
        assert result.text == "Response with both parameters override"

        # Verify the API call was made with overridden parameters
        call_args = mock_openai.chat.completions.create.call_args
        assert call_args[1]['model'] == "override-model"
        assert call_args[1]['temperature'] == 0.8


if __name__ == '__main__':
    pytest.main([__file__])