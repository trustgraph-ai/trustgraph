"""
Unit tests for trustgraph.model.text_completion.vertexai
Starting simple with one test to get the basics working
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.vertexai.llm import Processor
from trustgraph.base import LlmResult


class TestVertexAIProcessorSimple(IsolatedAsyncioTestCase):
    """Simple test for processor initialization"""

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test basic processor initialization with mocked dependencies"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        mock_model = MagicMock()
        mock_generative_model.return_value = mock_model
        
        # Mock the parent class initialization to avoid taskgroup requirement
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),  # Required by AsyncProcessor
            'id': 'test-processor'     # Required by AsyncProcessor
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'gemini-2.0-flash-001'  # It's stored as 'model', not 'model_name'
        assert hasattr(processor, 'generation_config')
        assert hasattr(processor, 'safety_settings')
        assert hasattr(processor, 'llm')
        mock_service_account.Credentials.from_service_account_file.assert_called_once_with('private.json')
        mock_vertexai.init.assert_called_once()

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test successful content generation"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated response from Gemini"
        mock_response.usage_metadata.prompt_token_count = 15
        mock_response.usage_metadata.candidates_token_count = 8
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Generated response from Gemini"
        assert result.in_token == 15
        assert result.out_token == 8
        assert result.model == 'gemini-2.0-flash-001'
        # Check that the method was called (actual prompt format may vary)
        mock_model.generate_content.assert_called_once()
        # Verify the call was made with the expected parameters
        call_args = mock_model.generate_content.call_args
        assert call_args[1]['generation_config'] == processor.generation_config
        assert call_args[1]['safety_settings'] == processor.safety_settings

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_rate_limit_error(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test rate limit error handling"""
        # Arrange
        from google.api_core.exceptions import ResourceExhausted
        from trustgraph.exceptions import TooManyRequests
        
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = ResourceExhausted("Rate limit exceeded")
        mock_generative_model.return_value = mock_model
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(TooManyRequests):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_blocked_response(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test handling of blocked content (safety filters)"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None  # Blocked content returns None
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 0
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act
        result = await processor.generate_content("System prompt", "Blocked content")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text is None  # Should preserve None for blocked content
        assert result.in_token == 10
        assert result.out_token == 0
        assert result.model == 'gemini-2.0-flash-001'

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_private_key(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test processor initialization without private key (should fail)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': None,  # No private key provided
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act & Assert
        with pytest.raises(RuntimeError, match="Private key file not specified"):
            processor = Processor(**config)

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test handling of generic exceptions"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Network error")
        mock_generative_model.return_value = mock_model
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act & Assert
        with pytest.raises(Exception, match="Network error"):
            await processor.generate_content("System prompt", "User prompt")

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        mock_model = MagicMock()
        mock_generative_model.return_value = mock_model
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-west1',
            'model': 'gemini-1.5-pro',
            'temperature': 0.7,
            'max_output': 4096,
            'private_key': 'custom-key.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.model == 'gemini-1.5-pro'
        
        # Verify that generation_config object exists (can't easily check internal values)
        assert hasattr(processor, 'generation_config')
        assert processor.generation_config is not None
        
        # Verify that safety settings are configured
        assert len(processor.safety_settings) == 4
        
        # Verify service account was called with custom key
        mock_service_account.Credentials.from_service_account_file.assert_called_once_with('custom-key.json')
        
        # Verify that parameters dict has the correct values (this is accessible)
        assert processor.parameters["temperature"] == 0.7
        assert processor.parameters["max_output_tokens"] == 4096
        assert processor.parameters["top_p"] == 1.0
        assert processor.parameters["top_k"] == 32
        assert processor.parameters["candidate_count"] == 1

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_vertexai_initialization_with_credentials(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test that VertexAI is initialized correctly with credentials"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        mock_model = MagicMock()
        mock_generative_model.return_value = mock_model
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'europe-west1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'service-account.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify VertexAI init was called with correct parameters
        mock_vertexai.init.assert_called_once_with(
            location='europe-west1',
            credentials=mock_credentials,
            project='test-project-123'
        )
        
        # Verify GenerativeModel was created with the right model name
        mock_generative_model.assert_called_once_with('gemini-2.0-flash-001')

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test content generation with empty prompts"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Default response"
        mock_response.usage_metadata.prompt_token_count = 2
        mock_response.usage_metadata.candidates_token_count = 3
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model
        
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
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
        
        # Verify the model was called with the combined empty prompts
        mock_model.generate_content.assert_called_once()
        call_args = mock_model.generate_content.call_args
        # The prompt should be "" + "\n\n" + "" = "\n\n"
        assert call_args[0][0] == "\n\n"


if __name__ == '__main__':
    pytest.main([__file__])