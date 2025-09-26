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
        assert processor.default_model == 'gemini-2.0-flash-001'  # It's stored as 'model', not 'model_name'
        assert hasattr(processor, 'generation_configs')  # Now a cache dictionary
        assert hasattr(processor, 'safety_settings')
        assert hasattr(processor, 'model_clients')  # LLM clients are now cached
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
        # Generation config is now created dynamically per model
        assert 'generation_config' in call_args[1]
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

    @patch('trustgraph.model.text_completion.vertexai.llm.google.auth.default')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_processor_initialization_without_private_key(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account, mock_auth_default):
        """Test processor initialization without private key (uses default credentials)"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None
        
        # Mock google.auth.default() to return credentials and project ID
        mock_credentials = MagicMock()
        mock_auth_default.return_value = (mock_credentials, "test-project-123")
        
        # Mock GenerativeModel
        mock_model = MagicMock()
        mock_generative_model.return_value = mock_model

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
        mock_vertexai.init.assert_called_once_with(
            location='us-central1', 
            project='test-project-123'
        )

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
        assert processor.default_model == 'gemini-1.5-pro'
        
        # Verify that generation_config object exists (can't easily check internal values)
        assert hasattr(processor, 'generation_configs')  # Now a cache dictionary
        assert processor.generation_configs == {}  # Empty cache initially
        
        # Verify that safety settings are configured
        assert len(processor.safety_settings) == 4
        
        # Verify service account was called with custom key
        mock_service_account.Credentials.from_service_account_file.assert_called_once_with('custom-key.json')
        
        # Verify that api_params dict has the correct values (this is accessible)
        assert processor.api_params["temperature"] == 0.7
        assert processor.api_params["max_output_tokens"] == 4096
        assert processor.api_params["top_p"] == 1.0
        assert processor.api_params["top_k"] == 32

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
        
        # GenerativeModel is now created lazily on first use, not at initialization
        mock_generative_model.assert_not_called()

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

    @patch('trustgraph.model.text_completion.vertexai.llm.AnthropicVertex')
    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_anthropic_processor_initialization_with_private_key(self, mock_llm_init, mock_async_init, mock_service_account, mock_anthropic_vertex):
        """Test Anthropic processor initialization with private key credentials"""
        # Arrange
        mock_async_init.return_value = None
        mock_llm_init.return_value = None
        
        mock_credentials = MagicMock()
        mock_credentials.project_id = "test-project-456"
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
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
        # is_anthropic logic is now determined dynamically per request
        
        # Verify service account was called with private key
        mock_service_account.Credentials.from_service_account_file.assert_called_once_with('anthropic-key.json')
        
        # Verify AnthropicVertex was initialized with credentials
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

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_temperature_override(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test temperature parameter override functionality"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response with custom temperature"
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 12
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model

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

        # Verify Gemini API was called with overridden temperature
        mock_model.generate_content.assert_called_once()
        call_args = mock_model.generate_content.call_args

        # Check that generation_config was created (we can't directly access temperature from mock)
        generation_config = call_args.kwargs['generation_config']
        assert generation_config is not None  # Should use overridden temperature configuration

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_model_override(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test model parameter override functionality"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        # Mock different models
        mock_model_default = MagicMock()
        mock_model_override = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response with custom model"
        mock_response.usage_metadata.prompt_token_count = 18
        mock_response.usage_metadata.candidates_token_count = 14
        mock_model_override.generate_content.return_value = mock_response

        # GenerativeModel should return different models based on input
        def model_factory(model_name):
            if model_name == 'gemini-1.5-pro':
                return mock_model_override
            return mock_model_default

        mock_generative_model.side_effect = model_factory

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',  # Default model
            'temperature': 0.2,               # Default temperature
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

        # Verify the overridden model was used
        mock_model_override.generate_content.assert_called_once()
        # Verify GenerativeModel was called with the override model
        mock_generative_model.assert_called_with('gemini-1.5-pro')

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_generate_content_both_parameters_override(self, mock_llm_init, mock_async_init, mock_generative_model, mock_vertexai, mock_service_account):
        """Test overriding both model and temperature parameters simultaneously"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response with both overrides"
        mock_response.usage_metadata.prompt_token_count = 22
        mock_response.usage_metadata.candidates_token_count = 16
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model

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

        # Verify both overrides were used
        mock_model.generate_content.assert_called_once()
        call_args = mock_model.generate_content.call_args

        # Verify model override
        mock_generative_model.assert_called_with('gemini-1.5-flash-001')  # Should use runtime override

        # Verify temperature override (we can't directly access temperature from mock)
        generation_config = call_args.kwargs['generation_config']
        assert generation_config is not None  # Should use overridden temperature configuration


if __name__ == '__main__':
    pytest.main([__file__])