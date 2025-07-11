"""
Unit tests for trustgraph.model.text_completion.cohere
Following the same successful pattern as previous tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.cohere.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestCohereProcessorSimple(IsolatedAsyncioTestCase):
    """Test Cohere processor functionality"""

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test basic processor initialization"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'c4ai-aya-23-8b',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'c4ai-aya-23-8b'
        assert processor.temperature == 0.0
        assert hasattr(processor, 'cohere')
        mock_cohere_class.assert_called_once_with(api_key='test-api-key')

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test successful content generation"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_output = MagicMock()
        mock_output.text = "Generated response from Cohere"
        mock_output.meta.billed_units.input_tokens = 25
        mock_output.meta.billed_units.output_tokens = 15
        
        mock_cohere_client.chat.return_value = mock_output
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'c4ai-aya-23-8b',
            'api_key': 'test-api-key',
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
        assert result.text == "Generated response from Cohere"
        assert result.in_token == 25
        assert result.out_token == 15
        assert result.model == 'c4ai-aya-23-8b'
        
        # Verify the Cohere API call
        mock_cohere_client.chat.assert_called_once_with(
            model='c4ai-aya-23-8b',
            message="User prompt",
            preamble="System prompt",
            temperature=0.0,
            chat_history=[],
            prompt_truncation='auto',
            connectors=[]
        )

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_rate_limit_error(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test rate limit error handling"""
        # Arrange
        import cohere
        
        mock_cohere_client = MagicMock()
        mock_cohere_client.chat.side_effect = cohere.TooManyRequestsError("Rate limit exceeded")
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'c4ai-aya-23-8b',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(TooManyRequests):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test handling of generic exceptions"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_cohere_client.chat.side_effect = Exception("API connection error")
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'c4ai-aya-23-8b',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="API connection error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_api_key(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test processor initialization without API key (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'c4ai-aya-23-8b',
            'api_key': None,  # No API key provided
            'temperature': 0.0,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="Cohere API key not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'command-light',
            'api_key': 'custom-api-key',
            'temperature': 0.7,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'command-light'
        assert processor.temperature == 0.7
        mock_cohere_class.assert_called_once_with(api_key='custom-api-key')

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test processor initialization with default values"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_cohere_class.return_value = mock_cohere_client
        
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
        assert processor.model == 'c4ai-aya-23-8b'  # default_model
        assert processor.temperature == 0.0  # default_temperature
        mock_cohere_class.assert_called_once_with(api_key='test-api-key')

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test content generation with empty prompts"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_output = MagicMock()
        mock_output.text = "Default response"
        mock_output.meta.billed_units.input_tokens = 2
        mock_output.meta.billed_units.output_tokens = 3
        
        mock_cohere_client.chat.return_value = mock_output
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'c4ai-aya-23-8b',
            'api_key': 'test-api-key',
            'temperature': 0.0,
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
        assert result.model == 'c4ai-aya-23-8b'
        
        # Verify the preamble and message are handled correctly
        call_args = mock_cohere_client.chat.call_args
        assert call_args[1]['preamble'] == ""
        assert call_args[1]['message'] == ""

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_chat_structure(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test that Cohere chat is structured correctly"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_output = MagicMock()
        mock_output.text = "Response with proper structure"
        mock_output.meta.billed_units.input_tokens = 30
        mock_output.meta.billed_units.output_tokens = 20
        
        mock_cohere_client.chat.return_value = mock_output
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'c4ai-aya-23-8b',
            'api_key': 'test-api-key',
            'temperature': 0.5,
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
        
        # Verify the chat structure matches Cohere API format
        call_args = mock_cohere_client.chat.call_args
        
        # Check parameters
        assert call_args[1]['model'] == 'c4ai-aya-23-8b'
        assert call_args[1]['message'] == "What is AI?"
        assert call_args[1]['preamble'] == "You are a helpful assistant"
        assert call_args[1]['temperature'] == 0.5
        assert call_args[1]['chat_history'] == []
        assert call_args[1]['prompt_truncation'] == 'auto'
        assert call_args[1]['connectors'] == []

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_token_parsing(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test token parsing from Cohere response"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_output = MagicMock()
        mock_output.text = "Token parsing test"
        mock_output.meta.billed_units.input_tokens = 50
        mock_output.meta.billed_units.output_tokens = 25
        
        mock_cohere_client.chat.return_value = mock_output
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'c4ai-aya-23-8b',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System", "User query")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Token parsing test"
        assert result.in_token == 50
        assert result.out_token == 25
        assert result.model == 'c4ai-aya-23-8b'

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_cohere_client_initialization(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test that Cohere client is initialized correctly"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'command-r',
            'api_key': 'co-test-key',
            'temperature': 0.0,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify Cohere client was called with correct API key
        mock_cohere_class.assert_called_once_with(api_key='co-test-key')
        
        # Verify processor has the client
        assert processor.cohere == mock_cohere_client
        assert processor.model == 'command-r'

    @patch('trustgraph.model.text_completion.cohere.llm.cohere.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_chat_parameters(self, mock_llm_init, mock_async_init, mock_cohere_class):
        """Test that all chat parameters are passed correctly"""
        # Arrange
        mock_cohere_client = MagicMock()
        mock_output = MagicMock()
        mock_output.text = "Chat parameter test"
        mock_output.meta.billed_units.input_tokens = 20
        mock_output.meta.billed_units.output_tokens = 10
        
        mock_cohere_client.chat.return_value = mock_output
        mock_cohere_class.return_value = mock_cohere_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'c4ai-aya-23-8b',
            'api_key': 'test-api-key',
            'temperature': 0.3,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System instructions", "User question")

        # Assert
        assert result.text == "Chat parameter test"
        
        # Verify all parameters are passed correctly
        call_args = mock_cohere_client.chat.call_args
        assert call_args[1]['model'] == 'c4ai-aya-23-8b'
        assert call_args[1]['message'] == "User question"
        assert call_args[1]['preamble'] == "System instructions"
        assert call_args[1]['temperature'] == 0.3
        assert call_args[1]['chat_history'] == []
        assert call_args[1]['prompt_truncation'] == 'auto'
        assert call_args[1]['connectors'] == []


if __name__ == '__main__':
    pytest.main([__file__])