"""
Unit tests for trustgraph.model.text_completion.vertexai
Updated for google-genai SDK
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.model.text_completion.vertexai.llm import Processor
from trustgraph.base import LlmResult


class TestVertexAIProcessorSimple(IsolatedAsyncioTestCase):
    """Simple test for processor initialization"""

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_basic(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test basic processor initialization with mocked dependencies"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

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
        assert processor.default_model == 'gemini-2.0-flash-001'
        assert hasattr(processor, 'generation_configs')  # Cache dictionary
        assert hasattr(processor, 'safety_settings')
        assert hasattr(processor, 'client')  # genai.Client
        mock_service_account.Credentials.from_service_account_file.assert_called_once()
        mock_genai.Client.assert_called_once_with(
            vertexai=True,
            project="test-project-123",
            location="us-central1",
            credentials=mock_credentials
        )

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_success(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test successful content generation"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_response = MagicMock()
        mock_response.text = "Generated response from Gemini"
        mock_response.usage_metadata.prompt_token_count = 15
        mock_response.usage_metadata.candidates_token_count = 8

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

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
        mock_client.models.generate_content.assert_called_once()

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_rate_limit_error(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test rate limit error handling"""
        # Arrange
        from google.api_core.exceptions import ResourceExhausted
        from trustgraph.exceptions import TooManyRequests

        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = ResourceExhausted("Rate limit exceeded")
        mock_genai.Client.return_value = mock_client

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

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_blocked_response(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test handling of blocked content (safety filters)"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_response = MagicMock()
        mock_response.text = None  # Blocked content returns None
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 0

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

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

    @patch('trustgraph.model.text_completion.vertexai.llm.google.auth.default')
    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_private_key(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai, mock_auth_default):
        """Test processor initialization without private key (uses default credentials)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        # Mock google.auth.default() to return credentials and project ID
        mock_credentials = MagicMock()
        mock_auth_default.return_value = (mock_credentials, "test-project-123")

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

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

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'gemini-2.0-flash-001'
        mock_auth_default.assert_called_once()
        mock_genai.Client.assert_called_once_with(
            vertexai=True,
            project="test-project-123",
            location="us-central1",
            credentials=mock_credentials
        )

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_generic_exception(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test handling of generic exceptions"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("Network error")
        mock_genai.Client.return_value = mock_client

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

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_with_custom_parameters(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test processor initialization with custom parameters"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

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
        assert processor.default_model == 'gemini-1.5-pro'

        # Verify that generation_config cache exists
        assert hasattr(processor, 'generation_configs')
        assert processor.generation_configs == {}  # Empty cache initially

        # Verify that safety settings are configured
        assert len(processor.safety_settings) == 4

        # Verify service account was called with custom key
        mock_service_account.Credentials.from_service_account_file.assert_called_once()

        # Verify that api_params dict has the correct values
        assert processor.api_params["temperature"] == 0.7
        assert processor.api_params["max_output_tokens"] == 4096
        assert processor.api_params["top_p"] == 1.0
        assert processor.api_params["top_k"] == 32

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_vertexai_initialization_with_credentials(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test that VertexAI is initialized correctly with credentials"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

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
        # Verify genai.Client was called with correct parameters
        mock_genai.Client.assert_called_once_with(
            vertexai=True,
            project='test-project-123',
            location='europe-west1',
            credentials=mock_credentials
        )

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_empty_prompts(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test content generation with empty prompts"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_response = MagicMock()
        mock_response.text = "Default response"
        mock_response.usage_metadata.prompt_token_count = 2
        mock_response.usage_metadata.candidates_token_count = 3

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

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

        # Verify the client was called
        mock_client.models.generate_content.assert_called_once()

    @patch('trustgraph.model.text_completion.vertexai.llm.AnthropicVertex')
    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_anthropic_processor_initialization_with_private_key(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai, mock_anthropic_vertex):
        """Test Anthropic processor initialization with private key credentials"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-456"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # Mock AnthropicVertex
        mock_anthropic_client = MagicMock()
        mock_anthropic_vertex.return_value = mock_anthropic_client

        config = {
            'region': 'us-west1',
            'model': 'claude-3-sonnet@20240229',  # Anthropic model
            'temperature': 0.5,
            'max_output': 2048,
            'private_key': 'anthropic-key.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-anthropic-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_model == 'claude-3-sonnet@20240229'

        # Verify service account was called with private key
        mock_service_account.Credentials.from_service_account_file.assert_called_once()

        # Verify AnthropicVertex was initialized with credentials (because model contains 'claude')
        mock_anthropic_vertex.assert_called_once_with(
            region='us-west1',
            project_id='test-project-456',
            credentials=mock_credentials
        )

        # Verify api_params are set correctly
        assert processor.api_params["temperature"] == 0.5
        assert processor.api_params["max_output_tokens"] == 2048
        assert processor.api_params["top_p"] == 1.0
        assert processor.api_params["top_k"] == 32

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_temperature_override(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test temperature parameter override functionality"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_response = MagicMock()
        mock_response.text = "Response with custom temperature"
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 12

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,  # Default temperature
            'max_output': 8192,
            'private_key': 'private.json',
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
        mock_client.models.generate_content.assert_called_once()

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_model_override(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test model parameter override functionality"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_response = MagicMock()
        mock_response.text = "Response with custom model"
        mock_response.usage_metadata.prompt_token_count = 18
        mock_response.usage_metadata.candidates_token_count = 14

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',  # Default model
            'temperature': 0.2,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override model at runtime
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model="gemini-1.5-pro",  # Override model
            temperature=None         # Use default temperature
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Response with custom model"

        # Verify the call was made with the override model
        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs['model'] == "gemini-1.5-pro"

    @patch('trustgraph.model.text_completion.vertexai.llm.genai')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_both_parameters_override(self, mock_llm_init, mock_async_init, mock_service_account, mock_genai):
        """Test overriding both model and temperature parameters simultaneously"""
        # Arrange
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-123"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_response = MagicMock()
        mock_response.text = "Response with both overrides"
        mock_response.usage_metadata.prompt_token_count = 22
        mock_response.usage_metadata.candidates_token_count = 16

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',  # Default model
            'temperature': 0.0,               # Default temperature
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Act - Override both parameters at runtime
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model="gemini-1.5-flash-001",  # Override model
            temperature=0.9                # Override temperature
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Response with both overrides"
        mock_client.models.generate_content.assert_called_once()

        # Verify the model override was used
        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs['model'] == "gemini-1.5-flash-001"


if __name__ == '__main__':
    pytest.main([__file__])
