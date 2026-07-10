"""
Unit tests for trustgraph.model.image_to_text.openai
Following the same successful pattern as the text completion OpenAI tests
"""

import base64

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.image_to_text.openai.service import Processor
from trustgraph.base import ImageDescriptionResult
from trustgraph.exceptions import TooManyRequests, LlmError

SAMPLE_IMAGE = base64.b64encode(b"image-data").decode("utf-8")


class TestOpenAIImageToTextProcessor(IsolatedAsyncioTestCase):
    """Test OpenAI image-to-text processor functionality"""

    def make_config(self, **overrides):
        config = {
            'model': 'test-vision-model',
            'api_key': 'test-api-key',
            'url': 'https://api.openai.com/v1',
            'max_output': 4096,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }
        config.update(overrides)
        return config

    def make_response(self, content="An image description",
                      prompt_tokens=20, completion_tokens=12):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = content
        mock_response.usage.prompt_tokens = prompt_tokens
        mock_response.usage.completion_tokens = completion_tokens
        return mock_response

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_processor_initialization_basic(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test basic processor initialization"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        # Act
        processor = Processor(**self.make_config())

        # Assert
        assert processor.default_model == 'test-vision-model'
        assert processor.max_output == 4096
        assert hasattr(processor, 'openai')
        mock_openai_class.assert_called_once_with(base_url='https://api.openai.com/v1', api_key='test-api-key')

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test processor initialization with default values"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

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
        assert processor.default_model == 'gpt-5-mini'  # default_model
        assert processor.max_output == 4096  # default_max_output
        mock_openai_class.assert_called_once_with(base_url='https://api.openai.com/v1', api_key='test-api-key')

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_processor_initialization_without_api_key(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test processor initialization without API key uses placeholder"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client
        mock_async_init.return_value = None
        mock_service_init.return_value = None

        # Act
        processor = Processor(**self.make_config(api_key=None))

        # Assert
        mock_openai_class.assert_called_once_with(
            base_url='https://api.openai.com/v1', api_key='not-set'
        )

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_openai_client_initialization_without_base_url(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test OpenAI client initialization without base_url"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        # Act
        processor = Processor(**self.make_config(url=None))

        # Assert - should be called without base_url when it's None
        mock_openai_class.assert_called_once_with(api_key='test-api-key')

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_describe_image_success(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test successful image description with data-URI message shape"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = self.make_response()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        processor = Processor(**self.make_config())

        # Act
        result = await processor.describe_image(
            SAMPLE_IMAGE, "image/png", "What is in this image?", "",
        )

        # Assert
        assert isinstance(result, ImageDescriptionResult)
        assert result.text == "An image description"
        assert result.in_token == 20
        assert result.out_token == 12
        assert result.model == 'test-vision-model'

        # Verify the OpenAI API call
        mock_openai_client.chat.completions.create.assert_called_once_with(
            model='test-vision-model',
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What is in this image?"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{SAMPLE_IMAGE}"
                        }
                    }
                ]
            }],
            max_completion_tokens=4096
        )

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_describe_image_default_prompt(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test that an empty prompt falls back to the default prompt"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = self.make_response()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        processor = Processor(**self.make_config())

        # Act
        await processor.describe_image(SAMPLE_IMAGE, "image/png", "", "")

        # Assert
        call_args = mock_openai_client.chat.completions.create.call_args
        text_block = call_args[1]['messages'][0]['content'][0]

        assert text_block['text'] == "Describe this image"

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_describe_image_system_prompt(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test that a system prompt is prepended to the user prompt"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = self.make_response()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        processor = Processor(**self.make_config())

        # Act
        await processor.describe_image(
            SAMPLE_IMAGE, "image/png", "What is this?", "You are terse",
        )

        # Assert
        call_args = mock_openai_client.chat.completions.create.call_args
        text_block = call_args[1]['messages'][0]['content'][0]

        assert text_block['text'] == "You are terse\n\nWhat is this?"

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_describe_image_model_override(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test model parameter override functionality"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = self.make_response()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        processor = Processor(**self.make_config())

        # Act - Override model at runtime
        await processor.describe_image(
            SAMPLE_IMAGE, "image/png", "Describe", "",
            model="other-vision-model",
        )

        # Assert
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'other-vision-model'

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_describe_image_no_override_uses_default(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test that no model override uses the processor default"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = self.make_response()
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        processor = Processor(**self.make_config())

        # Act
        await processor.describe_image(
            SAMPLE_IMAGE, "image/png", "Describe", "", model=None,
        )

        # Assert
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'test-vision-model'

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_describe_image_rate_limit_error(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test rate limit error handling"""
        # Arrange
        from openai import RateLimitError

        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        processor = Processor(**self.make_config())

        # Act & Assert
        with pytest.raises(TooManyRequests):
            await processor.describe_image(SAMPLE_IMAGE, "image/png", "Describe", "")

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_describe_image_rate_limit_unrecoverable(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test that unrecoverable rate limit codes raise RuntimeError"""
        # Arrange
        from openai import RateLimitError

        body = {
            "error": {
                "code": "insufficient_quota",
                "message": "You exceeded your current quota",
            }
        }

        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = RateLimitError("Rate limit exceeded", response=MagicMock(), body=body)
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        processor = Processor(**self.make_config())

        # Act & Assert
        with pytest.raises(RuntimeError, match="insufficient_quota"):
            await processor.describe_image(SAMPLE_IMAGE, "image/png", "Describe", "")

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_describe_image_internal_server_error(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test that InternalServerError is mapped to retryable LlmError"""
        # Arrange
        from openai import InternalServerError

        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = InternalServerError("Service unavailable", response=mock_response, body=None)
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        processor = Processor(**self.make_config())

        # Act & Assert
        with pytest.raises(LlmError):
            await processor.describe_image(SAMPLE_IMAGE, "image/png", "Describe", "")

    @patch('trustgraph.model.image_to_text.openai.service.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.image_to_text_service.ImageToTextService.__init__')
    async def test_describe_image_generic_exception(self, mock_service_init, mock_async_init, mock_openai_class):
        """Test handling of generic exceptions"""
        # Arrange
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = Exception("API connection error")
        mock_openai_class.return_value = mock_openai_client

        mock_async_init.return_value = None
        mock_service_init.return_value = None

        processor = Processor(**self.make_config())

        # Act & Assert
        with pytest.raises(Exception, match="API connection error"):
            await processor.describe_image(SAMPLE_IMAGE, "image/png", "Describe", "")


if __name__ == '__main__':
    pytest.main([__file__])
