"""
Integration tests for Dynamic LLM Parameters
Testing end-to-end flow of runtime parameter changes in LLM processors
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from trustgraph.model.text_completion.openai.llm import Processor as OpenAIProcessor
from trustgraph.base import LlmResult


@pytest.mark.integration
class TestDynamicLlmParameters:
    """Integration tests for dynamic parameter configuration"""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client that returns realistic responses"""
        client = MagicMock()

        # Default mock response
        usage = CompletionUsage(prompt_tokens=25, completion_tokens=15, total_tokens=40)
        message = ChatCompletionMessage(role="assistant", content="Dynamic parameter test response")
        choice = Choice(index=0, message=message, finish_reason="stop")

        completion = ChatCompletion(
            id="chatcmpl-test-dynamic",
            choices=[choice],
            created=1234567890,
            model="gpt-4",  # Will be overridden based on test
            object="chat.completion",
            usage=usage
        )

        client.chat.completions.create.return_value = completion
        return client

    @pytest.fixture
    def base_processor_config(self):
        """Base configuration for test processors"""
        return {
            "api_key": "test-api-key",
            "url": "https://api.openai.com/v1",
            "temperature": 0.0,  # Default temperature
            "max_output": 1024,
        }

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_runtime_temperature_override(self, mock_llm_init, mock_async_init,
                                               mock_openai_class, mock_openai_client, base_processor_config):
        """Test that temperature can be overridden at runtime"""
        # Arrange
        mock_openai_class.return_value = mock_openai_client
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = base_processor_config | {
            "model": "gpt-3.5-turbo",
            "concurrency": 1,
            "taskgroup": AsyncMock(),
            "id": "test-processor"
        }

        processor = OpenAIProcessor(**config)

        # Act - Call with different temperature than configured default (0.0)
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model=None,  # Use default model
            temperature=0.9  # Override temperature
        )

        # Assert
        assert isinstance(result, LlmResult)
        assert result.text == "Dynamic parameter test response"

        # Verify the OpenAI API was called with the overridden temperature
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args

        assert call_args.kwargs['temperature'] == 0.9  # Should use runtime parameter
        assert call_args.kwargs['model'] == "gpt-3.5-turbo"  # Should use processor default

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_runtime_model_override(self, mock_llm_init, mock_async_init,
                                         mock_openai_class, mock_openai_client, base_processor_config):
        """Test that model can be overridden at runtime"""
        # Arrange
        mock_openai_class.return_value = mock_openai_client
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = base_processor_config | {
            "model": "gpt-3.5-turbo",  # Default model
            "concurrency": 1,
            "taskgroup": AsyncMock(),
            "id": "test-processor"
        }

        processor = OpenAIProcessor(**config)

        # Act - Call with different model than configured default
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model="gpt-4",        # Override model
            temperature=None      # Use default temperature
        )

        # Assert
        assert isinstance(result, LlmResult)

        # Verify the OpenAI API was called with the overridden model
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args

        assert call_args.kwargs['model'] == "gpt-4"        # Should use runtime parameter
        assert call_args.kwargs['temperature'] == 0.0      # Should use processor default

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_both_parameters_override(self, mock_llm_init, mock_async_init,
                                           mock_openai_class, mock_openai_client, base_processor_config):
        """Test that both model and temperature can be overridden simultaneously"""
        # Arrange
        mock_openai_class.return_value = mock_openai_client
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = base_processor_config | {
            "model": "gpt-3.5-turbo",  # Default model
            "concurrency": 1,
            "taskgroup": AsyncMock(),
            "id": "test-processor"
        }

        processor = OpenAIProcessor(**config)

        # Act - Override both parameters
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model="gpt-4",        # Override model
            temperature=0.5       # Override temperature
        )

        # Assert
        assert isinstance(result, LlmResult)

        # Verify both parameters were overridden
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args

        assert call_args.kwargs['model'] == "gpt-4"        # Should use runtime parameter
        assert call_args.kwargs['temperature'] == 0.5      # Should use runtime parameter

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_fallback_to_defaults_when_no_override(self, mock_llm_init, mock_async_init,
                                                        mock_openai_class, mock_openai_client, base_processor_config):
        """Test that processor falls back to configured defaults when no parameters are provided"""
        # Arrange
        mock_openai_class.return_value = mock_openai_client
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = base_processor_config | {
            "model": "gpt-3.5-turbo",  # Default model
            "temperature": 0.2,        # Default temperature
            "concurrency": 1,
            "taskgroup": AsyncMock(),
            "id": "test-processor"
        }

        processor = OpenAIProcessor(**config)

        # Act - Call with no parameter overrides
        result = await processor.generate_content(
            "System prompt",
            "User prompt",
            model=None,       # Use default
            temperature=None  # Use default
        )

        # Assert
        assert isinstance(result, LlmResult)

        # Verify defaults were used
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args

        assert call_args.kwargs['model'] == "gpt-3.5-turbo"  # Should use processor default
        assert call_args.kwargs['temperature'] == 0.2        # Should use processor default

    @patch('trustgraph.model.text_completion.openai.llm.OpenAI')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_multiple_concurrent_calls_different_parameters(self, mock_llm_init, mock_async_init,
                                                                 mock_openai_class, mock_openai_client, base_processor_config):
        """Test multiple concurrent calls with different parameters don't interfere"""
        # Arrange
        mock_openai_class.return_value = mock_openai_client
        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = base_processor_config | {
            "model": "gpt-3.5-turbo",
            "concurrency": 1,
            "taskgroup": AsyncMock(),
            "id": "test-processor"
        }

        processor = OpenAIProcessor(**config)

        # Reset the mock to track multiple calls
        mock_openai_client.reset_mock()

        # Act - Make multiple calls with different parameters concurrently
        import asyncio
        tasks = [
            processor.generate_content("System 1", "Prompt 1", model="gpt-3.5-turbo", temperature=0.1),
            processor.generate_content("System 2", "Prompt 2", model="gpt-4", temperature=0.8),
            processor.generate_content("System 3", "Prompt 3", model="gpt-3.5-turbo", temperature=0.5)
        ]

        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        for result in results:
            assert isinstance(result, LlmResult)

        # Verify all calls were made with correct parameters
        assert mock_openai_client.chat.completions.create.call_count == 3

        # Get all call arguments
        call_args_list = mock_openai_client.chat.completions.create.call_args_list

        # Verify each call had the expected parameters
        expected_params = [
            ("gpt-3.5-turbo", 0.1),
            ("gpt-4", 0.8),
            ("gpt-3.5-turbo", 0.5)
        ]

        for i, (expected_model, expected_temp) in enumerate(expected_params):
            call_kwargs = call_args_list[i].kwargs
            assert call_kwargs['model'] == expected_model
            assert call_kwargs['temperature'] == expected_temp

    async def test_parameter_boundary_values(self, mock_openai_client, base_processor_config):
        """Test parameter boundary values (edge cases)"""
        # This would test extreme values like temperature=0.0, temperature=2.0, etc.
        # Implementation depends on specific validation requirements
        pass

    async def test_invalid_parameter_types_handling(self, mock_openai_client, base_processor_config):
        """Test handling of invalid parameter types"""
        # This would test what happens with invalid temperature values, non-existent models, etc.
        # Implementation depends on error handling requirements
        pass


if __name__ == '__main__':
    pytest.main([__file__])