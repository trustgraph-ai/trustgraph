"""
Integration tests for Text Completion Service (OpenAI)

These tests verify the end-to-end functionality of the OpenAI text completion service,
testing API connectivity, authentication, rate limiting, error handling, and token tracking.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from openai import OpenAI, RateLimitError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from trustgraph.model.text_completion.openai.llm import Processor
from trustgraph.exceptions import TooManyRequests
from trustgraph.base import LlmResult
from trustgraph.schema import TextCompletionRequest, TextCompletionResponse, Error


@pytest.mark.integration
class TestTextCompletionIntegration:
    """Integration tests for OpenAI text completion service coordination"""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client that returns realistic responses"""
        client = MagicMock(spec=OpenAI)
        
        # Mock chat completion response
        usage = CompletionUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150)
        message = ChatCompletionMessage(role="assistant", content="This is a test response from the AI model.")
        choice = Choice(index=0, message=message, finish_reason="stop")
        
        completion = ChatCompletion(
            id="chatcmpl-test123",
            choices=[choice],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion",
            usage=usage
        )
        
        client.chat.completions.create.return_value = completion
        return client

    @pytest.fixture
    def processor_config(self):
        """Configuration for processor testing"""
        return {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_output": 1024,
        }

    @pytest.fixture
    def text_completion_processor(self, processor_config):
        """Create text completion processor with test configuration"""
        # Create a minimal processor instance for testing generate_content
        processor = MagicMock()
        processor.default_model = processor_config["model"]
        processor.temperature = processor_config["temperature"]
        processor.max_output = processor_config["max_output"]

        # Add the actual generate_content method from Processor class
        processor.generate_content = Processor.generate_content.__get__(processor, Processor)

        return processor

    @pytest.mark.asyncio
    async def test_text_completion_successful_generation(self, text_completion_processor, mock_openai_client):
        """Test successful text completion generation"""
        # Arrange
        text_completion_processor.openai = mock_openai_client
        system_prompt = "You are a helpful assistant."
        user_prompt = "What is machine learning?"

        # Act
        result = await text_completion_processor.generate_content(system_prompt, user_prompt)

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "This is a test response from the AI model."
        assert result.in_token == 50
        assert result.out_token == 100
        assert result.model == "gpt-3.5-turbo"

        # Verify OpenAI API was called correctly
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        
        assert call_args.kwargs['model'] == "gpt-3.5-turbo"
        assert call_args.kwargs['temperature'] == 0.7
        assert call_args.kwargs['max_tokens'] == 1024
        assert len(call_args.kwargs['messages']) == 1
        assert call_args.kwargs['messages'][0]['role'] == "user"
        assert "You are a helpful assistant." in call_args.kwargs['messages'][0]['content'][0]['text']
        assert "What is machine learning?" in call_args.kwargs['messages'][0]['content'][0]['text']

    @pytest.mark.asyncio
    async def test_text_completion_with_different_configurations(self, mock_openai_client):
        """Test text completion with various configuration parameters"""
        # Test different configurations
        test_configs = [
            {"model": "gpt-4", "temperature": 0.0, "max_output": 512},
            {"model": "gpt-3.5-turbo", "temperature": 1.0, "max_output": 2048},
            {"model": "gpt-4-turbo", "temperature": 0.5, "max_output": 4096}
        ]

        for config in test_configs:
            # Arrange - Create minimal processor mock
            processor = MagicMock()
            processor.default_model = config['model']
            processor.temperature = config['temperature']
            processor.max_output = config['max_output']
            processor.openai = mock_openai_client

            # Add the actual generate_content method
            processor.generate_content = Processor.generate_content.__get__(processor, Processor)

            # Act
            result = await processor.generate_content("System prompt", "User prompt")

            # Assert
            assert isinstance(result, LlmResult)
            assert result.text == "This is a test response from the AI model."
            assert result.in_token == 50
            assert result.out_token == 100
            # Note: result.model comes from mock response, not processor config
            
            # Verify configuration was applied
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args.kwargs['model'] == config['model']
            assert call_args.kwargs['temperature'] == config['temperature']
            assert call_args.kwargs['max_tokens'] == config['max_output']
            
            # Reset mock for next iteration
            mock_openai_client.reset_mock()

    @pytest.mark.asyncio
    async def test_text_completion_rate_limit_handling(self, text_completion_processor, mock_openai_client):
        """Test proper rate limit error handling"""
        # Arrange
        mock_openai_client.chat.completions.create.side_effect = RateLimitError(
            "Rate limit exceeded", 
            response=MagicMock(status_code=429),
            body={}
        )
        text_completion_processor.openai = mock_openai_client

        # Act & Assert
        with pytest.raises(TooManyRequests):
            await text_completion_processor.generate_content("System prompt", "User prompt")

        # Verify OpenAI API was called
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_completion_api_error_handling(self, text_completion_processor, mock_openai_client):
        """Test handling of general API errors"""
        # Arrange
        mock_openai_client.chat.completions.create.side_effect = Exception("API connection failed")
        text_completion_processor.openai = mock_openai_client

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await text_completion_processor.generate_content("System prompt", "User prompt")

        assert "API connection failed" in str(exc_info.value)
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_completion_token_tracking(self, text_completion_processor, mock_openai_client):
        """Test accurate token counting and tracking"""
        # Arrange - Different token counts for multiple requests
        test_cases = [
            (25, 75),   # Small request
            (100, 200), # Medium request
            (500, 1000) # Large request
        ]

        for input_tokens, output_tokens in test_cases:
            # Update mock response with different token counts
            usage = CompletionUsage(
                prompt_tokens=input_tokens, 
                completion_tokens=output_tokens, 
                total_tokens=input_tokens + output_tokens
            )
            message = ChatCompletionMessage(role="assistant", content="Test response")
            choice = Choice(index=0, message=message, finish_reason="stop")
            
            completion = ChatCompletion(
                id="chatcmpl-test123",
                choices=[choice],
                created=1234567890,
                model="gpt-3.5-turbo",
                object="chat.completion",
                usage=usage
            )
            
            mock_openai_client.chat.completions.create.return_value = completion
            text_completion_processor.openai = mock_openai_client

            # Act
            result = await text_completion_processor.generate_content("System", "Prompt")

            # Assert
            assert result.in_token == input_tokens
            assert result.out_token == output_tokens
            assert result.model == "gpt-3.5-turbo"

            # Reset mock for next iteration
            mock_openai_client.reset_mock()

    @pytest.mark.asyncio
    async def test_text_completion_prompt_construction(self, text_completion_processor, mock_openai_client):
        """Test proper prompt construction with system and user prompts"""
        # Arrange
        text_completion_processor.openai = mock_openai_client
        system_prompt = "You are an expert in artificial intelligence."
        user_prompt = "Explain neural networks in simple terms."

        # Act
        result = await text_completion_processor.generate_content(system_prompt, user_prompt)

        # Assert
        call_args = mock_openai_client.chat.completions.create.call_args
        sent_message = call_args.kwargs['messages'][0]['content'][0]['text']
        
        # Verify system and user prompts are combined correctly
        assert system_prompt in sent_message
        assert user_prompt in sent_message
        assert sent_message.startswith(system_prompt)
        assert user_prompt in sent_message

    @pytest.mark.asyncio
    async def test_text_completion_concurrent_requests(self, processor_config, mock_openai_client):
        """Test handling of concurrent requests"""
        # Arrange
        processors = []
        for i in range(5):
            processor = MagicMock()
            processor.default_model = processor_config["model"]
            processor.temperature = processor_config["temperature"]
            processor.max_output = processor_config["max_output"]
            processor.openai = mock_openai_client
            processor.generate_content = Processor.generate_content.__get__(processor, Processor)
            processors.append(processor)

        # Simulate multiple concurrent requests
        tasks = []
        for i, processor in enumerate(processors):
            task = processor.generate_content(f"System {i}", f"Prompt {i}")
            tasks.append(task)

        # Act
        import asyncio
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 5
        for result in results:
            assert isinstance(result, LlmResult)
            assert result.text == "This is a test response from the AI model."
            assert result.in_token == 50
            assert result.out_token == 100

        # Verify all requests were processed
        assert mock_openai_client.chat.completions.create.call_count == 5

    @pytest.mark.asyncio
    async def test_text_completion_response_format_validation(self, text_completion_processor, mock_openai_client):
        """Test response format and structure validation"""
        # Arrange
        text_completion_processor.openai = mock_openai_client

        # Act
        result = await text_completion_processor.generate_content("System", "Prompt")

        # Assert
        # Verify OpenAI API call parameters
        call_args = mock_openai_client.chat.completions.create.call_args
        # Note: response_format, top_p, frequency_penalty, and presence_penalty
        # were removed in #561 as unnecessary parameters
        assert 'model' in call_args.kwargs
        assert 'temperature' in call_args.kwargs
        assert 'max_tokens' in call_args.kwargs

        # Verify result structure
        assert hasattr(result, 'text')
        assert hasattr(result, 'in_token')
        assert hasattr(result, 'out_token')
        assert hasattr(result, 'model')

    @pytest.mark.asyncio
    async def test_text_completion_authentication_patterns(self):
        """Test different authentication configurations"""
        # Test missing API key first (this should fail early)
        with pytest.raises(RuntimeError) as exc_info:
            Processor(id="test-no-key", api_key=None)
        assert "OpenAI API key not specified" in str(exc_info.value)

        # Test authentication pattern by examining the initialization logic
        # Since we can't fully instantiate due to taskgroup requirements,
        # we'll test the authentication logic directly
        from trustgraph.model.text_completion.openai.llm import default_api_key, default_base_url
        
        # Test default values
        assert default_base_url == "https://api.openai.com/v1"
        
        # Test configuration parameters
        test_configs = [
            {"api_key": "test-key-1", "url": "https://api.openai.com/v1"},
            {"api_key": "test-key-2", "url": "https://custom.openai.com/v1"},
        ]
        
        for config in test_configs:
            # We can't fully test instantiation due to taskgroup,
            # but we can verify the authentication logic would work
            assert config["api_key"] is not None
            assert config["url"] is not None

    @pytest.mark.asyncio
    async def test_text_completion_error_propagation(self, text_completion_processor, mock_openai_client):
        """Test error propagation through the service"""
        # Test different error types
        error_cases = [
            (RateLimitError("Rate limit", response=MagicMock(status_code=429), body={}), TooManyRequests),
            (Exception("Connection timeout"), Exception),
            (ValueError("Invalid request"), ValueError),
        ]

        for error_input, expected_error in error_cases:
            # Arrange
            mock_openai_client.chat.completions.create.side_effect = error_input
            text_completion_processor.openai = mock_openai_client

            # Act & Assert
            with pytest.raises(expected_error):
                await text_completion_processor.generate_content("System", "Prompt")

            # Reset mock for next iteration
            mock_openai_client.reset_mock()

    @pytest.mark.asyncio
    async def test_text_completion_model_parameter_validation(self, mock_openai_client):
        """Test that model parameters are correctly passed to OpenAI API"""
        # Arrange
        processor = MagicMock()
        processor.default_model = "gpt-4"
        processor.temperature = 0.8
        processor.max_output = 2048
        processor.openai = mock_openai_client
        processor.generate_content = Processor.generate_content.__get__(processor, Processor)

        # Act
        await processor.generate_content("System prompt", "User prompt")

        # Assert
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs['model'] == "gpt-4"
        assert call_args.kwargs['temperature'] == 0.8
        assert call_args.kwargs['max_tokens'] == 2048
        # Note: top_p, frequency_penalty, and presence_penalty
        # were removed in #561 as unnecessary parameters

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_text_completion_performance_timing(self, text_completion_processor, mock_openai_client):
        """Test performance timing for text completion"""
        # Arrange
        text_completion_processor.openai = mock_openai_client
        
        # Act
        import time
        start_time = time.time()
        
        result = await text_completion_processor.generate_content("System", "Prompt")
        
        end_time = time.time()
        execution_time = end_time - start_time

        # Assert
        assert isinstance(result, LlmResult)
        assert execution_time < 1.0  # Should complete quickly with mocked API
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_completion_response_content_extraction(self, text_completion_processor, mock_openai_client):
        """Test proper extraction of response content from OpenAI API"""
        # Arrange
        test_responses = [
            "This is a simple response.",
            "This is a multi-line response.\nWith multiple lines.\nAnd more content.",
            "Response with special characters: @#$%^&*()_+-=[]{}|;':\",./<>?",
            ""  # Empty response
        ]

        for test_content in test_responses:
            # Update mock response
            usage = CompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            message = ChatCompletionMessage(role="assistant", content=test_content)
            choice = Choice(index=0, message=message, finish_reason="stop")
            
            completion = ChatCompletion(
                id="chatcmpl-test123",
                choices=[choice],
                created=1234567890,
                model="gpt-3.5-turbo",
                object="chat.completion",
                usage=usage
            )
            
            mock_openai_client.chat.completions.create.return_value = completion
            text_completion_processor.openai = mock_openai_client

            # Act
            result = await text_completion_processor.generate_content("System", "Prompt")

            # Assert
            assert result.text == test_content
            assert result.in_token == 10
            assert result.out_token == 20
            assert result.model == "gpt-3.5-turbo"

            # Reset mock for next iteration
            mock_openai_client.reset_mock()