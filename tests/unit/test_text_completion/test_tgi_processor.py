"""
Unit tests for trustgraph.model.text_completion.tgi
Following the same successful pattern as previous tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.tgi.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestTGIProcessorSimple(IsolatedAsyncioTestCase):
    """Test TGI processor functionality"""

    @patch('trustgraph.model.text_completion.tgi.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test basic processor initialization"""
        # Arrange
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'tgi',
            'url': 'http://tgi-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'tgi'
        assert processor.base_url == 'http://tgi-service:8899/v1'
        assert processor.temperature == 0.0
        assert processor.max_output == 2048
        assert hasattr(processor, 'session')
        mock_session_class.assert_called_once()

    @patch('trustgraph.model.text_completion.tgi.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test successful content generation"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'message': {
                    'content': 'Generated response from TGI'
                }
            }],
            'usage': {
                'prompt_tokens': 20,
                'completion_tokens': 12
            }
        })

        # Mock the async context manager
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'tgi',
            'url': 'http://tgi-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Generated response from TGI"
        assert result.in_token == 20
        assert result.out_token == 12
        assert result.model == 'tgi'

        # Verify the API call was made correctly
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args

        # Check URL
        assert call_args[0][0] == 'http://tgi-service:8899/v1/chat/completions'

        # Check request structure
        request_body = call_args[1]['json']
        assert request_body['model'] == 'tgi'
        assert request_body['temperature'] == 0.0
        assert request_body['max_tokens'] == 2048

    @patch('trustgraph.model.text_completion.tgi.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_with_model_override(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test generate_content with model parameter override"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'message': {
                    'content': 'Response from overridden model'
                }
            }],
            'usage': {
                'prompt_tokens': 15,
                'completion_tokens': 10
            }
        })

        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'tgi',
            'url': 'http://tgi-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override model
        result = await processor.generate_content("System", "Prompt", model="custom-tgi-model")

        # Assert
        assert result.model == "custom-tgi-model"  # Should use overridden model
        assert result.text == "Response from overridden model"

        # Verify the API call was made with overridden model
        call_args = mock_session.post.call_args
        assert call_args[1]['json']['model'] == "custom-tgi-model"

    @patch('trustgraph.model.text_completion.tgi.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_with_temperature_override(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test generate_content with temperature parameter override"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'message': {
                    'content': 'Response with temperature override'
                }
            }],
            'usage': {
                'prompt_tokens': 18,
                'completion_tokens': 12
            }
        })

        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'tgi',
            'url': 'http://tgi-service:8899/v1',
            'temperature': 0.0,  # Default temperature
            'max_output': 2048,
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
        call_args = mock_session.post.call_args
        assert call_args[1]['json']['temperature'] == 0.7

    @patch('trustgraph.model.text_completion.tgi.llm.aiohttp.ClientSession')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_with_both_parameters_override(self, mock_llm_init, mock_async_init, mock_session_class):
        """Test generate_content with both model and temperature overrides"""
        # Arrange
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'message': {
                    'content': 'Response with both parameters override'
                }
            }],
            'usage': {
                'prompt_tokens': 20,
                'completion_tokens': 15
            }
        })

        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        mock_session_class.return_value = mock_session

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'tgi',
            'url': 'http://tgi-service:8899/v1',
            'temperature': 0.0,
            'max_output': 2048,
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
        call_args = mock_session.post.call_args
        assert call_args[1]['json']['model'] == "override-model"
        assert call_args[1]['json']['temperature'] == 0.8


if __name__ == '__main__':
    pytest.main([__file__])