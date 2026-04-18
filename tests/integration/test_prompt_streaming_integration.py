"""
Integration tests for Prompt Service Streaming Functionality

These tests verify the streaming behavior of the Prompt service,
testing how it coordinates between templates and text completion streaming.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from trustgraph.prompt.template.service import Processor
from trustgraph.schema import PromptRequest, PromptResponse, TextCompletionResponse
from trustgraph.base.text_completion_client import TextCompletionResult
from tests.utils.streaming_assertions import (
    assert_streaming_chunks_valid,
    assert_callback_invoked,
)


@pytest.mark.integration
class TestPromptStreaming:
    """Integration tests for Prompt service streaming"""

    @pytest.fixture
    def mock_flow_context_streaming(self):
        """Mock flow context with streaming text completion support"""
        context = MagicMock()

        # Mock text completion client with streaming
        text_completion_client = AsyncMock()

        # Streaming chunks to send
        chunks = [
            "Machine", " learning", " is", " a", " field",
            " of", " artificial", " intelligence", "."
        ]

        async def streaming_text_completion_stream(system, prompt, handler, timeout=600):
            """Simulate streaming text completion via text_completion_stream"""
            for i, chunk_text in enumerate(chunks):
                response = TextCompletionResponse(
                    response=chunk_text,
                    error=None,
                    end_of_stream=False
                )
                await handler(response)

            # Send final empty chunk with end_of_stream
            await handler(TextCompletionResponse(
                response="",
                error=None,
                end_of_stream=True
            ))

            return TextCompletionResult(
                text=None,
                in_token=10,
                out_token=9,
                model="test-model",
            )

        async def non_streaming_text_completion(system, prompt, timeout=600):
            """Simulate non-streaming text completion"""
            full_text = "Machine learning is a field of artificial intelligence."
            return TextCompletionResult(
                text=full_text,
                in_token=10,
                out_token=9,
                model="test-model",
            )

        text_completion_client.text_completion_stream = AsyncMock(
            side_effect=streaming_text_completion_stream
        )
        text_completion_client.text_completion = AsyncMock(
            side_effect=non_streaming_text_completion
        )

        # Mock response producer
        response_producer = AsyncMock()

        def context_router(service_name):
            if service_name == "text-completion-request":
                return text_completion_client
            elif service_name == "response":
                return response_producer
            else:
                return AsyncMock()

        context.side_effect = context_router
        context.workspace = "default"
        return context

    @pytest.fixture
    def mock_prompt_manager(self):
        """Mock PromptManager with simple template"""
        manager = MagicMock()

        async def invoke_template(kind, input_vars, llm_function):
            """Simulate template invocation"""
            # Call the LLM function with simple prompts
            system = "You are a helpful assistant."
            prompt = f"Question: {input_vars.get('question', 'test')}"
            result = await llm_function(system, prompt)
            return result

        manager.invoke = invoke_template
        return manager

    @pytest.fixture
    def prompt_processor_streaming(self, mock_prompt_manager):
        """Create Prompt processor with streaming support"""
        processor = MagicMock()
        processor.managers = {"default": mock_prompt_manager}
        processor.config_key = "prompt"

        # Bind the actual on_request method
        processor.on_request = Processor.on_request.__get__(processor, Processor)

        return processor

    @pytest.mark.asyncio
    async def test_prompt_streaming_basic(self, prompt_processor_streaming, mock_flow_context_streaming):
        """Test basic prompt streaming functionality"""
        # Arrange
        request = PromptRequest(
            id="kg_prompt",
            terms={"question": '"What is machine learning?"'},
            streaming=True
        )

        message = MagicMock()
        message.value.return_value = request
        message.properties.return_value = {"id": "test-123"}

        consumer = MagicMock()

        # Act
        await prompt_processor_streaming.on_request(
            message, consumer, mock_flow_context_streaming
        )

        # Assert
        # Verify response producer was called multiple times (for streaming chunks)
        response_producer = mock_flow_context_streaming("response")
        assert response_producer.send.call_count > 0

        # Verify streaming chunks were sent
        calls = response_producer.send.call_args_list
        assert len(calls) > 1  # Should have multiple chunks

        # Check that responses have end_of_stream flag
        for call in calls:
            response = call.args[0]
            assert isinstance(response, PromptResponse)
            assert hasattr(response, 'end_of_stream')

        # Last response should have end_of_stream=True
        last_call = calls[-1]
        last_response = last_call.args[0]
        assert last_response.end_of_stream is True

    @pytest.mark.asyncio
    async def test_prompt_streaming_non_streaming_mode(self, prompt_processor_streaming,
                                                         mock_flow_context_streaming):
        """Test prompt service in non-streaming mode"""
        # Arrange
        request = PromptRequest(
            id="kg_prompt",
            terms={"question": '"What is AI?"'},
            streaming=False  # Non-streaming
        )

        message = MagicMock()
        message.value.return_value = request
        message.properties.return_value = {"id": "test-456"}

        consumer = MagicMock()

        # Act
        await prompt_processor_streaming.on_request(
            message, consumer, mock_flow_context_streaming
        )

        # Assert
        # Verify response producer was called once (non-streaming)
        response_producer = mock_flow_context_streaming("response")
        # Note: In non-streaming mode, the service sends a single response
        assert response_producer.send.call_count >= 1

    @pytest.mark.asyncio
    async def test_prompt_streaming_chunk_forwarding(self, prompt_processor_streaming,
                                                       mock_flow_context_streaming):
        """Test that prompt service forwards chunks immediately"""
        # Arrange
        request = PromptRequest(
            id="test_prompt",
            terms={"question": '"Test query"'},
            streaming=True
        )

        message = MagicMock()
        message.value.return_value = request
        message.properties.return_value = {"id": "test-789"}

        consumer = MagicMock()

        # Act
        await prompt_processor_streaming.on_request(
            message, consumer, mock_flow_context_streaming
        )

        # Assert
        # Verify chunks were forwarded with proper structure
        response_producer = mock_flow_context_streaming("response")
        calls = response_producer.send.call_args_list

        for call in calls:
            response = call.args[0]
            # Each response should have text and end_of_stream fields
            assert hasattr(response, 'text')
            assert hasattr(response, 'end_of_stream')

    @pytest.mark.asyncio
    async def test_prompt_streaming_error_handling(self, prompt_processor_streaming):
        """Test error handling during streaming"""
        # Arrange
        from trustgraph.schema import Error
        context = MagicMock()

        # Mock text completion client that raises an error
        text_completion_client = AsyncMock()

        async def failing_stream(system, prompt, handler, timeout=600):
            raise RuntimeError("Text completion error")

        text_completion_client.text_completion_stream = AsyncMock(
            side_effect=failing_stream
        )

        # Mock response producer to capture error response
        response_producer = AsyncMock()

        def context_router(service_name):
            if service_name == "text-completion-request":
                return text_completion_client
            elif service_name == "response":
                return response_producer
            else:
                return AsyncMock()

        context.side_effect = context_router
        context.workspace = "default"

        request = PromptRequest(
            id="test_prompt",
            terms={"question": '"Test"'},
            streaming=True
        )

        message = MagicMock()
        message.value.return_value = request
        message.properties.return_value = {"id": "test-error"}

        consumer = MagicMock()

        # Act - The service catches errors and sends an error PromptResponse
        await prompt_processor_streaming.on_request(message, consumer, context)

        # Assert - error response was sent
        calls = response_producer.send.call_args_list
        assert len(calls) > 0
        error_response = calls[-1].args[0]
        assert error_response.error is not None
        assert "Text completion error" in error_response.error.message

    @pytest.mark.asyncio
    async def test_prompt_streaming_preserves_message_id(self, prompt_processor_streaming,
                                                           mock_flow_context_streaming):
        """Test that message IDs are preserved through streaming"""
        # Arrange
        message_id = "unique-test-id-12345"

        request = PromptRequest(
            id="test_prompt",
            terms={"question": '"Test"'},
            streaming=True
        )

        message = MagicMock()
        message.value.return_value = request
        message.properties.return_value = {"id": message_id}

        consumer = MagicMock()

        # Act
        await prompt_processor_streaming.on_request(
            message, consumer, mock_flow_context_streaming
        )

        # Assert
        # Verify all responses were sent with the correct message ID
        response_producer = mock_flow_context_streaming("response")
        calls = response_producer.send.call_args_list

        for call in calls:
            properties = call.kwargs.get('properties')
            assert properties is not None
            assert properties['id'] == message_id

    @pytest.mark.asyncio
    async def test_prompt_streaming_empty_response_handling(self, prompt_processor_streaming):
        """Test handling of empty responses during streaming"""
        # Arrange
        context = MagicMock()

        # Mock text completion that sends empty chunks
        text_completion_client = AsyncMock()

        async def empty_streaming(system, prompt, handler, timeout=600):
            # Send empty chunk followed by final marker
            await handler(TextCompletionResponse(
                response="",
                error=None,
                end_of_stream=False
            ))
            await handler(TextCompletionResponse(
                response="",
                error=None,
                end_of_stream=True
            ))

        text_completion_client.text_completion_stream = AsyncMock(
            side_effect=empty_streaming
        )
        response_producer = AsyncMock()

        def context_router(service_name):
            if service_name == "text-completion-request":
                return text_completion_client
            elif service_name == "response":
                return response_producer
            else:
                return AsyncMock()

        context.side_effect = context_router
        context.workspace = "default"

        request = PromptRequest(
            id="test_prompt",
            terms={"question": '"Test"'},
            streaming=True
        )

        message = MagicMock()
        message.value.return_value = request
        message.properties.return_value = {"id": "test-empty"}

        consumer = MagicMock()

        # Act
        await prompt_processor_streaming.on_request(message, consumer, context)

        # Assert
        # Should still send responses even if empty (including final marker)
        assert response_producer.send.call_count > 0

        # Last response should have end_of_stream=True
        last_call = response_producer.send.call_args_list[-1]
        last_response = last_call.args[0]
        assert last_response.end_of_stream is True

    @pytest.mark.asyncio
    async def test_prompt_streaming_concatenation_matches_complete(self, prompt_processor_streaming,
                                                                     mock_flow_context_streaming):
        """Test that streaming chunks concatenate to form complete response"""
        # Arrange
        request = PromptRequest(
            id="test_prompt",
            terms={"question": '"What is ML?"'},
            streaming=True
        )

        message = MagicMock()
        message.value.return_value = request
        message.properties.return_value = {"id": "test-concat"}

        consumer = MagicMock()

        # Act
        await prompt_processor_streaming.on_request(
            message, consumer, mock_flow_context_streaming
        )

        # Assert
        # Collect all response texts
        response_producer = mock_flow_context_streaming("response")
        calls = response_producer.send.call_args_list

        chunk_texts = []
        for call in calls:
            response = call.args[0]
            if response.text and not response.end_of_stream:
                chunk_texts.append(response.text)

        # Verify chunks concatenate to expected result
        full_text = "".join(chunk_texts)
        assert full_text == "Machine learning is a field of artificial intelligence."
