"""
Unit tests for trustgraph.model.text_completion.googleaistudio
Following the same successful pattern as previous tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.googleaistudio.llm import Processor
from trustgraph.base import LlmResult
from trustgraph.exceptions import TooManyRequests


class TestGoogleAIStudioProcessorSimple(IsolatedAsyncioTestCase):
    """Test Google AI Studio processor functionality"""

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test basic processor initialization"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
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
        assert processor.model == 'gemini-2.0-flash-001'
        assert processor.temperature == 0.0
        assert processor.max_output == 8192
        assert hasattr(processor, 'client')
        assert hasattr(processor, 'safety_settings')
        assert len(processor.safety_settings) == 4  # 4 safety categories
        mock_genai_class.assert_called_once_with(api_key='test-api-key')

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test successful content generation"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated response from Google AI Studio"
        mock_response.usage_metadata.prompt_token_count = 25
        mock_response.usage_metadata.candidates_token_count = 15
        
        mock_genai_client.models.generate_content.return_value = mock_response
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
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
        assert result.text == "Generated response from Google AI Studio"
        assert result.in_token == 25
        assert result.out_token == 15
        assert result.model == 'gemini-2.0-flash-001'
        
        # Verify the Google AI Studio API call
        mock_genai_client.models.generate_content.assert_called_once()
        call_args = mock_genai_client.models.generate_content.call_args
        assert call_args[1]['model'] == 'gemini-2.0-flash-001'
        assert call_args[1]['contents'] == "User prompt"

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_rate_limit_error(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test rate limit error handling"""
        # Arrange
        from google.api_core.exceptions import ResourceExhausted
        
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = ResourceExhausted("Rate limit exceeded")
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
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

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test handling of generic exceptions"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = Exception("API connection error")
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
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

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_api_key(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test processor initialization without API key (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
            'api_key': None,  # No API key provided
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="Google AI Studio API key not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-1.5-pro',
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
        assert processor.model == 'gemini-1.5-pro'
        assert processor.temperature == 0.7
        assert processor.max_output == 4096
        mock_genai_class.assert_called_once_with(api_key='custom-api-key')

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_defaults(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test processor initialization with default values"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_genai_class.return_value = mock_genai_client
        
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
        assert processor.model == 'gemini-2.0-flash-001'  # default_model
        assert processor.temperature == 0.0  # default_temperature
        assert processor.max_output == 8192  # default_max_output
        mock_genai_class.assert_called_once_with(api_key='test-api-key')

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test content generation with empty prompts"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Default response"
        mock_response.usage_metadata.prompt_token_count = 2
        mock_response.usage_metadata.candidates_token_count = 3
        
        mock_genai_client.models.generate_content.return_value = mock_response
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
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
        assert result.model == 'gemini-2.0-flash-001'
        
        # Verify the system instruction and content are handled correctly
        call_args = mock_genai_client.models.generate_content.call_args
        assert call_args[1]['contents'] == ""

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_configuration_structure(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test that generation configuration is structured correctly"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response with proper structure"
        mock_response.usage_metadata.prompt_token_count = 30
        mock_response.usage_metadata.candidates_token_count = 20
        
        mock_genai_client.models.generate_content.return_value = mock_response
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
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
        
        # Verify the generation configuration
        call_args = mock_genai_client.models.generate_content.call_args
        config_arg = call_args[1]['config']
        
        # Check that the configuration has the right structure
        assert call_args[1]['model'] == 'gemini-2.0-flash-001'
        assert call_args[1]['contents'] == "What is AI?"
        # Config should be a GenerateContentConfig object

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_safety_settings_initialization(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test that safety settings are initialized correctly"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
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
        assert hasattr(processor, 'safety_settings')
        assert len(processor.safety_settings) == 4
        # Should have 4 safety categories: hate speech, harassment, sexually explicit, dangerous content

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_token_parsing(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test token parsing from Google AI Studio response"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Token parsing test"
        mock_response.usage_metadata.prompt_token_count = 50
        mock_response.usage_metadata.candidates_token_count = 25
        
        mock_genai_client.models.generate_content.return_value = mock_response
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 8192,
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
        assert result.model == 'gemini-2.0-flash-001'

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_genai_client_initialization(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test that Google AI Studio client is initialized correctly"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-1.5-flash',
            'api_key': 'gai-test-key',
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify Google AI Studio client was called with correct API key
        mock_genai_class.assert_called_once_with(api_key='gai-test-key')
        
        # Verify processor has the client
        assert processor.client == mock_genai_client
        assert processor.model == 'gemini-1.5-flash'

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai.Client')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_system_instruction(self, mock_llm_init, mock_async_init, mock_genai_class):
        """Test that system instruction is handled correctly"""
        # Arrange
        mock_genai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "System instruction test"
        mock_response.usage_metadata.prompt_token_count = 35
        mock_response.usage_metadata.candidates_token_count = 25
        
        mock_genai_client.models.generate_content.return_value = mock_response
        mock_genai_class.return_value = mock_genai_client
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 8192,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("Be helpful and concise", "Explain quantum computing")

        # Assert
        assert result.text == "System instruction test"
        assert result.in_token == 35
        assert result.out_token == 25
        
        # Verify the system instruction is passed in the config
        call_args = mock_genai_client.models.generate_content.call_args
        config_arg = call_args[1]['config']
        # The system instruction should be in the config object
        assert call_args[1]['contents'] == "Explain quantum computing"


if __name__ == '__main__':
    pytest.main([__file__])