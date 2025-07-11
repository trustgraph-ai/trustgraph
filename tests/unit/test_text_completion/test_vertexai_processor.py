"""
Unit tests for trustgraph.model.text_completion.vertexai
Following TEST_STRATEGY.md patterns for mocking external dependencies
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from unittest import IsolatedAsyncioTestCase
import asyncio
import os
from google.api_core.exceptions import ResourceExhausted
from google.oauth2 import service_account

# Import the service under test
from trustgraph.model.text_completion.vertexai.llm import Processor
from trustgraph.base.types import TextCompletionRequest, TextCompletionResponse, LlmResult, Error


class TestVertexAIProcessorInitialization(IsolatedAsyncioTestCase):
    """Test processor initialization with various configurations"""

    def setUp(self):
        """Set up test fixtures"""
        self.default_config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1
        }

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_processor_initialization_with_valid_credentials(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test processor initialization with valid service account credentials"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        mock_model = MagicMock()
        mock_generative_model.return_value = mock_model

        # Act
        processor = Processor(**self.default_config)

        # Assert
        mock_service_account.Credentials.from_service_account_file.assert_called_once_with('private.json')
        mock_vertexai.init.assert_called_once()
        mock_generative_model.assert_called_once_with(
            'gemini-2.0-flash-001',
            generation_config=processor.generation_config,
            safety_settings=processor.safety_settings
        )
        assert processor.model_name == 'gemini-2.0-flash-001'
        assert processor.region == 'us-central1'
        assert processor.temperature == 0.0
        assert processor.max_output == 8192

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_processor_initialization_with_custom_model(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test processor initialization with custom model selection"""
        # Arrange
        config = self.default_config.copy()
        config['model'] = 'gemini-1.5-pro'
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        # Act
        processor = Processor(**config)

        # Assert
        mock_generative_model.assert_called_once_with(
            'gemini-1.5-pro',
            generation_config=processor.generation_config,
            safety_settings=processor.safety_settings
        )
        assert processor.model_name == 'gemini-1.5-pro'

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_processor_initialization_with_custom_parameters(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test processor initialization with custom generation parameters"""
        # Arrange
        config = self.default_config.copy()
        config.update({
            'temperature': 0.7,
            'max_output': 4096,
            'region': 'us-east1'
        })
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.temperature == 0.7
        assert processor.max_output == 4096
        assert processor.region == 'us-east1'
        assert processor.generation_config.temperature == 0.7
        assert processor.generation_config.max_output_tokens == 4096

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_processor_initialization_without_private_key(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test processor initialization without private key (default credentials)"""
        # Arrange
        config = self.default_config.copy()
        config['private_key'] = None

        # Act
        processor = Processor(**config)

        # Assert
        mock_service_account.Credentials.from_service_account_file.assert_not_called()
        mock_vertexai.init.assert_called_once()
        assert processor.model_name == 'gemini-2.0-flash-001'

    async def test_processor_initialization_generation_config(self):
        """Test that generation config is properly set"""
        # Arrange & Act
        with patch('trustgraph.model.text_completion.vertexai.llm.service_account'), \
             patch('trustgraph.model.text_completion.vertexai.llm.vertexai'), \
             patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel'):
            
            processor = Processor(**self.default_config)

            # Assert
            assert processor.generation_config.temperature == 0.0
            assert processor.generation_config.max_output_tokens == 8192
            assert processor.generation_config.top_p == 1.0
            assert processor.generation_config.top_k == 10
            assert processor.generation_config.candidate_count == 1

    async def test_processor_initialization_safety_settings(self):
        """Test that safety settings are properly configured"""
        # Arrange & Act
        with patch('trustgraph.model.text_completion.vertexai.llm.service_account'), \
             patch('trustgraph.model.text_completion.vertexai.llm.vertexai'), \
             patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel'):
            
            processor = Processor(**self.default_config)

            # Assert
            assert len(processor.safety_settings) == 4
            # Check that all harm categories are configured
            harm_categories = [setting.category for setting in processor.safety_settings]
            assert 'HARM_CATEGORY_HARASSMENT' in str(harm_categories)
            assert 'HARM_CATEGORY_HATE_SPEECH' in str(harm_categories)
            assert 'HARM_CATEGORY_SEXUALLY_EXPLICIT' in str(harm_categories)
            assert 'HARM_CATEGORY_DANGEROUS_CONTENT' in str(harm_categories)


class TestVertexAIMessageProcessing(IsolatedAsyncioTestCase):
    """Test message processing functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.default_config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1
        }

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_successful_text_completion_simple_prompt(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test successful text completion with simple prompt"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test response from Gemini"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System prompt", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Test response from Gemini"
        assert result.in_token == 10
        assert result.out_token == 5
        mock_model.generate_content.assert_called_once_with("System prompt\nUser prompt")

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_text_completion_with_system_instructions(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test text completion with system instructions"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response with system instructions"
        mock_response.usage_metadata.prompt_token_count = 25
        mock_response.usage_metadata.candidates_token_count = 15
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("You are a helpful assistant", "What is AI?")

        # Assert
        assert result.text == "Response with system instructions"
        assert result.in_token == 25
        assert result.out_token == 15
        mock_model.generate_content.assert_called_once_with("You are a helpful assistant\nWhat is AI?")

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_text_completion_with_long_context(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test text completion with long context"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response to long context"
        mock_response.usage_metadata.prompt_token_count = 1000
        mock_response.usage_metadata.candidates_token_count = 100
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)
        long_prompt = "This is a very long prompt. " * 100

        # Act
        result = await processor.generate_content("System", long_prompt)

        # Assert
        assert result.text == "Response to long context"
        assert result.in_token == 1000
        assert result.out_token == 100

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_text_completion_with_empty_prompts(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test text completion with empty prompts"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Default response"
        mock_response.usage_metadata.prompt_token_count = 1
        mock_response.usage_metadata.candidates_token_count = 2
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("", "")

        # Assert
        assert result.text == "Default response"
        mock_model.generate_content.assert_called_once_with("\n")


class TestVertexAISafetyFiltering(IsolatedAsyncioTestCase):
    """Test safety filtering functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.default_config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1
        }

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_safety_filter_configuration(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test safety filter configuration"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        # Act
        processor = Processor(**self.default_config)

        # Assert
        assert len(processor.safety_settings) == 4
        # Verify safety settings are passed to model
        mock_generative_model.assert_called_once_with(
            'gemini-2.0-flash-001',
            generation_config=processor.generation_config,
            safety_settings=processor.safety_settings
        )

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_blocked_content_handling(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test blocked content handling"""
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

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "Blocked content prompt")

        # Assert
        assert result.text == ""  # Should return empty string for blocked content
        assert result.in_token == 10
        assert result.out_token == 0


class TestVertexAIErrorHandling(IsolatedAsyncioTestCase):
    """Test error handling functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.default_config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1
        }

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_rate_limit_error_handling(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test rate limit error handling"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = ResourceExhausted("Rate limit exceeded")
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == ""
        assert result.in_token is None
        assert result.out_token is None
        assert result.error == "TooManyRequests"

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_authentication_error_handling(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test authentication error handling"""
        # Arrange
        mock_service_account.Credentials.from_service_account_file.side_effect = FileNotFoundError("Private key not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            processor = Processor(**self.default_config)

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_generic_exception_handling(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test generic exception handling"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Unknown error")
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == ""
        assert result.in_token is None
        assert result.out_token is None
        assert result.error == "Unknown error"

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_model_not_found_error_handling(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test model not found error handling"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = ValueError("Model not found")
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == ""
        assert result.error == "Model not found"

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_quota_exceeded_error_handling(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test quota exceeded error handling"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = ResourceExhausted("Quota exceeded")
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == ""
        assert result.error == "TooManyRequests"

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_token_limit_exceeded_error_handling(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test token limit exceeded error handling"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = ValueError("Token limit exceeded")
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == ""
        assert result.error == "Token limit exceeded"


class TestVertexAIMetricsCollection(IsolatedAsyncioTestCase):
    """Test metrics collection functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.default_config = {
            'region': 'us-central1',
            'model': 'gemini-2.0-flash-001',
            'temperature': 0.0,
            'max_output': 8192,
            'private_key': 'private.json',
            'concurrency': 1
        }

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_token_usage_metrics_collection(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test token usage metrics collection"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_response.usage_metadata.prompt_token_count = 50
        mock_response.usage_metadata.candidates_token_count = 25
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert result.in_token == 50
        assert result.out_token == 25

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_request_duration_metrics(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test request duration metrics collection"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5
        
        # Simulate slow response
        async def slow_generate_content(prompt):
            await asyncio.sleep(0.1)
            return mock_response
        
        mock_model.generate_content.side_effect = slow_generate_content
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert result.text == "Test response"
        # Note: In real implementation, this would be captured by Prometheus metrics

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_error_rate_metrics(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test error rate metrics collection"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Test error")
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert result.error == "Test error"
        # Note: In real implementation, this would be captured by Prometheus metrics

    @patch('trustgraph.model.text_completion.vertexai.llm.service_account')
    @patch('trustgraph.model.text_completion.vertexai.llm.vertexai')
    @patch('trustgraph.model.text_completion.vertexai.llm.GenerativeModel')
    async def test_cost_calculation_metrics(self, mock_generative_model, mock_vertexai, mock_service_account):
        """Test cost calculation metrics per model type"""
        # Arrange
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model

        processor = Processor(**self.default_config)

        # Act
        result = await processor.generate_content("System", "User prompt")

        # Assert
        assert result.in_token == 100
        assert result.out_token == 50
        # Note: Cost calculation would be done by the metrics system based on model type and token usage


if __name__ == '__main__':
    pytest.main([__file__])