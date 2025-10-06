"""
Unit tests for trustgraph.model.text_completion.mistral
Following the same successful pattern as other processor tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.mistral.llm import Processor
from trustgraph.base import LlmResult


class TestMistralProcessorSimple(IsolatedAsyncioTestCase):
    """Test Mistral processor functionality"""

    @patch('trustgraph.model.text_completion.mistral.llm.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_mistral_class):
        """Test basic processor initialization"""
        # Arrange
        mock_mistral_client = MagicMock()
        mock_mistral_class.return_value = mock_mistral_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'ministral-8b-latest',
            'api_key': 'test-api-key',
            'temperature': 0.1,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'ministral-8b-latest'
        assert processor.temperature == 0.1
        assert processor.max_output == 2048
        assert hasattr(processor, 'mistral')
        mock_mistral_class.assert_called_once_with(api_key='test-api-key')

    @patch('trustgraph.model.text_completion.mistral.llm.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_mistral_class):
        """Test successful content generation"""
        # Arrange
        mock_mistral_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = 'Generated response from Mistral'
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 8
        mock_mistral_client.chat.complete.return_value = mock_response
        mock_mistral_class.return_value = mock_mistral_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'ministral-8b-latest',
            'api_key': 'test-api-key',
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
        assert result.text == "Generated response from Mistral"
        assert result.in_token == 15
        assert result.out_token == 8
        assert result.model == 'ministral-8b-latest'
        mock_mistral_client.chat.complete.assert_called_once()

    @patch('trustgraph.model.text_completion.mistral.llm.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_temperature_override(self, mock_llm_init, mock_async_init, mock_mistral_class):
        """Test temperature parameter override functionality"""
        # Arrange
        mock_mistral_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = 'Response with custom temperature'
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 12
        mock_mistral_client.chat.complete.return_value = mock_response
        mock_mistral_class.return_value = mock_mistral_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'ministral-8b-latest',
            'api_key': 'test-api-key',
            'temperature': 0.0,  # Default temperature
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
            model=None,      # Use default model
            temperature=0.8  # Override temperature
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Response with custom temperature"

        # Verify Mistral API was called with overridden temperature
        call_args = mock_mistral_client.chat.complete.call_args
        assert call_args[1]['temperature'] == 0.8  # Should use runtime override
        assert call_args[1]['model'] == 'ministral-8b-latest'

    @patch('trustgraph.model.text_completion.mistral.llm.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_model_override(self, mock_llm_init, mock_async_init, mock_mistral_class):
        """Test model parameter override functionality"""
        # Arrange
        mock_mistral_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = 'Response with custom model'
        mock_response.usage.prompt_tokens = 18
        mock_response.usage.completion_tokens = 14
        mock_mistral_client.chat.complete.return_value = mock_response
        mock_mistral_class.return_value = mock_mistral_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'ministral-8b-latest',    # Default model
            'api_key': 'test-api-key',
            'temperature': 0.1,   # Default temperature
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
            model="mistral-large-latest",    # Override model
            temperature=None    # Use default temperature
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Response with custom model"

        # Verify Mistral API was called with overridden model
        call_args = mock_mistral_client.chat.complete.call_args
        assert call_args[1]['model'] == 'mistral-large-latest'  # Should use runtime override
        assert call_args[1]['temperature'] == 0.1  # Should use processor default

    @patch('trustgraph.model.text_completion.mistral.llm.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_both_parameters_override(self, mock_llm_init, mock_async_init, mock_mistral_class):
        """Test overriding both model and temperature parameters simultaneously"""
        # Arrange
        mock_mistral_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = 'Response with both overrides'
        mock_response.usage.prompt_tokens = 22
        mock_response.usage.completion_tokens = 16
        mock_mistral_client.chat.complete.return_value = mock_response
        mock_mistral_class.return_value = mock_mistral_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'ministral-8b-latest',    # Default model
            'api_key': 'test-api-key',
            'temperature': 0.0,   # Default temperature
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override both parameters at runtime
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model="mistral-large-latest",  # Override model
            temperature=0.9     # Override temperature
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Response with both overrides"

        # Verify Mistral API was called with both overrides
        call_args = mock_mistral_client.chat.complete.call_args
        assert call_args[1]['model'] == 'mistral-large-latest'  # Should use runtime override
        assert call_args[1]['temperature'] == 0.9  # Should use runtime override

    @patch('trustgraph.model.text_completion.mistral.llm.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_prompt_construction(self, mock_llm_init, mock_async_init, mock_mistral_class):
        """Test prompt construction with system and user prompts"""
        # Arrange
        mock_mistral_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = 'Response with system instructions'
        mock_response.usage.prompt_tokens = 25
        mock_response.usage.completion_tokens = 15
        mock_mistral_client.chat.complete.return_value = mock_response
        mock_mistral_class.return_value = mock_mistral_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'ministral-8b-latest',
            'api_key': 'test-api-key',
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
        assert result.text == "Response with system instructions"
        assert result.in_token == 25
        assert result.out_token == 15

        # Verify the combined prompt structure
        call_args = mock_mistral_client.chat.complete.call_args
        messages = call_args[1]['messages']
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'][0]['type'] == 'text'
        assert messages[0]['content'][0]['text'] == "You are a helpful assistant\n\nWhat is AI?"


if __name__ == '__main__':
    pytest.main([__file__])