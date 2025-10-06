"""
Unit tests for trustgraph.model.text_completion.bedrock
Following the same successful pattern as other processor tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase
import json

# Import the service under test
from trustgraph.model.text_completion.bedrock.llm import Processor, Mistral, Anthropic
from trustgraph.base import LlmResult


class TestBedrockProcessorSimple(IsolatedAsyncioTestCase):
    """Test Bedrock processor functionality"""

    @patch('trustgraph.model.text_completion.bedrock.llm.boto3.Session')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test basic processor initialization"""
        # Arrange
        mock_session = MagicMock()
        mock_bedrock = MagicMock()
        mock_session.client.return_value = mock_bedrock
        mock_session_class.return_value = mock_session

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'mistral.mistral-large-2407-v1:0',
            'temperature': 0.1,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'mistral.mistral-large-2407-v1:0'
        assert processor.temperature == 0.1
        assert hasattr(processor, 'bedrock')
        mock_session_class.assert_called_once()

    @patch('trustgraph.model.text_completion.bedrock.llm.boto3.Session')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success_mistral(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test successful content generation with Mistral model"""
        # Arrange
        mock_session = MagicMock()
        mock_bedrock = MagicMock()
        mock_session.client.return_value = mock_bedrock
        mock_session_class.return_value = mock_session

        mock_response = {
            'body': MagicMock(),
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'x-amzn-bedrock-input-token-count': '15',
                    'x-amzn-bedrock-output-token-count': '8'
                }
            }
        }
        mock_response['body'].read.return_value = json.dumps({
            'outputs': [{'text': 'Generated response from Bedrock'}]
        })
        mock_bedrock.invoke_model.return_value = mock_response

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'mistral.mistral-large-2407-v1:0',
            'temperature': 0.0,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Generated response from Bedrock"
        assert result.in_token == 15
        assert result.out_token == 8
        assert result.model == 'mistral.mistral-large-2407-v1:0'
        mock_bedrock.invoke_model.assert_called_once()

    @patch('trustgraph.model.text_completion.bedrock.llm.boto3.Session')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_temperature_override(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test temperature parameter override functionality"""
        # Arrange
        mock_session = MagicMock()
        mock_bedrock = MagicMock()
        mock_session.client.return_value = mock_bedrock
        mock_session_class.return_value = mock_session

        mock_response = {
            'body': MagicMock(),
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'x-amzn-bedrock-input-token-count': '20',
                    'x-amzn-bedrock-output-token-count': '12'
                }
            }
        }
        mock_response['body'].read.return_value = json.dumps({
            'outputs': [{'text': 'Response with custom temperature'}]
        })
        mock_bedrock.invoke_model.return_value = mock_response

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'mistral.mistral-large-2407-v1:0',
            'temperature': 0.0,  # Default temperature
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

        # Verify the model variant was created with overridden temperature
        # The cache key should include the temperature
        cache_key = f"mistral.mistral-large-2407-v1:0:0.8"
        assert cache_key in processor.model_variants
        variant = processor.model_variants[cache_key]
        assert variant.temperature == 0.8

    @patch('trustgraph.model.text_completion.bedrock.llm.boto3.Session')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_model_override(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test model parameter override functionality"""
        # Arrange
        mock_session = MagicMock()
        mock_bedrock = MagicMock()
        mock_session.client.return_value = mock_bedrock
        mock_session_class.return_value = mock_session

        mock_response = {
            'body': MagicMock(),
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'x-amzn-bedrock-input-token-count': '18',
                    'x-amzn-bedrock-output-token-count': '14'
                }
            }
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Response with custom model'}]
        })
        mock_bedrock.invoke_model.return_value = mock_response

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'mistral.mistral-large-2407-v1:0',  # Default model
            'temperature': 0.1,   # Default temperature
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override model at runtime
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model="anthropic.claude-3-sonnet-20240229-v1:0",  # Override model
            temperature=None    # Use default temperature
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Response with custom model"

        # Verify Bedrock API was called with overridden model
        mock_bedrock.invoke_model.assert_called_once()
        call_args = mock_bedrock.invoke_model.call_args
        assert call_args[1]['modelId'] == "anthropic.claude-3-sonnet-20240229-v1:0"

        # Verify the correct model variant (Anthropic) was used
        cache_key = f"anthropic.claude-3-sonnet-20240229-v1:0:0.1"
        assert cache_key in processor.model_variants
        variant = processor.model_variants[cache_key]
        assert isinstance(variant, Anthropic)

    @patch('trustgraph.model.text_completion.bedrock.llm.boto3.Session')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_both_parameters_override(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test overriding both model and temperature parameters simultaneously"""
        # Arrange
        mock_session = MagicMock()
        mock_bedrock = MagicMock()
        mock_session.client.return_value = mock_bedrock
        mock_session_class.return_value = mock_session

        mock_response = {
            'body': MagicMock(),
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'x-amzn-bedrock-input-token-count': '22',
                    'x-amzn-bedrock-output-token-count': '16'
                }
            }
        }
        mock_response['body'].read.return_value = json.dumps({
            'generation': 'Response with both overrides'
        })
        mock_bedrock.invoke_model.return_value = mock_response

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'mistral.mistral-large-2407-v1:0',  # Default model
            'temperature': 0.0,   # Default temperature
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override both parameters at runtime
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model="meta.llama3-70b-instruct-v1:0",  # Override model (Meta/Llama)
            temperature=0.9     # Override temperature
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Response with both overrides"

        # Verify Bedrock API was called with both overrides
        mock_bedrock.invoke_model.assert_called_once()
        call_args = mock_bedrock.invoke_model.call_args
        assert call_args[1]['modelId'] == "meta.llama3-70b-instruct-v1:0"

        # Verify the correct model variant (Meta) was used with correct temperature
        cache_key = f"meta.llama3-70b-instruct-v1:0:0.9"
        assert cache_key in processor.model_variants
        variant = processor.model_variants[cache_key]
        assert variant.temperature == 0.9


if __name__ == '__main__':
    pytest.main([__file__])