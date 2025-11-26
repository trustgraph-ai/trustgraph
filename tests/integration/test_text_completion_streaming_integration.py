"""
Integration tests for Text Completion Streaming Functionality

These tests verify the streaming behavior of the Text Completion service,
testing token-by-token response delivery through the complete pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice as StreamChoice, ChoiceDelta

from trustgraph.model.text_completion.openai.llm import Processor
from trustgraph.base import LlmChunk
from tests.utils.streaming_assertions import (
    assert_streaming_chunks_valid,
    assert_callback_invoked,
)


@pytest.mark.integration
class TestTextCompletionStreaming:
    """Integration tests for Text Completion streaming"""

    @pytest.fixture
    def mock_streaming_openai_client(self, mock_streaming_llm_response):
        """Mock OpenAI client with streaming support"""
        client = MagicMock()

        def create_streaming_completion(**kwargs):
            """Generator that yields streaming chunks"""
            if kwargs.get('stream', False):
                # Simulate OpenAI streaming response
                chunks_text = [
                    "Machine", " learning", " is", " a", " subset",
                    " of", " AI", " that", " enables", " computers",
                    " to", " learn", " from", " data", "."
                ]

                for text in chunks_text:
                    delta = ChoiceDelta(content=text, role=None)
                    choice = StreamChoice(index=0, delta=delta, finish_reason=None)
                    chunk = ChatCompletionChunk(
                        id="chatcmpl-streaming",
                        choices=[choice],
                        created=1234567890,
                        model="gpt-3.5-turbo",
                        object="chat.completion.chunk"
                    )
                    yield chunk
            else:
                # Non-streaming response (shouldn't happen in these tests)
                raise ValueError("Expected streaming mode")

        client.chat.completions.create.return_value = create_streaming_completion()
        return client

    @pytest.fixture
    def text_completion_processor_streaming(self, mock_streaming_openai_client):
        """Create text completion processor with streaming support"""
        processor = MagicMock()
        processor.default_model = "gpt-3.5-turbo"
        processor.temperature = 0.7
        processor.max_output = 1024
        processor.openai = mock_streaming_openai_client

        # Bind the actual streaming method
        processor.generate_content_stream = Processor.generate_content_stream.__get__(
            processor, Processor
        )

        return processor

    @pytest.mark.asyncio
    async def test_text_completion_streaming_basic(self, text_completion_processor_streaming,
                                                     streaming_chunk_collector):
        """Test basic text completion streaming functionality"""
        # Arrange
        system_prompt = "You are a helpful assistant."
        user_prompt = "What is machine learning?"
        collector = streaming_chunk_collector()

        # Act - Collect all chunks
        chunks = []
        async for chunk in text_completion_processor_streaming.generate_content_stream(
            system_prompt, user_prompt
        ):
            chunks.append(chunk)
            if chunk.text:
                await collector.collect(chunk.text)

        # Assert
        assert len(chunks) > 1  # Should have multiple chunks

        # Verify all chunks are LlmChunk objects
        for chunk in chunks:
            assert isinstance(chunk, LlmChunk)
            assert chunk.model == "gpt-3.5-turbo"

        # Verify last chunk has is_final=True
        assert chunks[-1].is_final is True

        # Verify we got meaningful content
        full_text = collector.get_full_text()
        assert "machine" in full_text.lower() or "learning" in full_text.lower()

    @pytest.mark.asyncio
    async def test_text_completion_streaming_chunk_structure(self, text_completion_processor_streaming):
        """Test that streaming chunks have correct structure"""
        # Arrange
        system_prompt = "You are a helpful assistant."
        user_prompt = "Explain AI."

        # Act
        chunks = []
        async for chunk in text_completion_processor_streaming.generate_content_stream(
            system_prompt, user_prompt
        ):
            chunks.append(chunk)

        # Assert - Verify chunk structure
        for i, chunk in enumerate(chunks[:-1]):  # All except last
            assert isinstance(chunk, LlmChunk)
            assert chunk.text is not None
            assert chunk.model == "gpt-3.5-turbo"
            assert chunk.is_final is False

        # Last chunk should be final marker
        final_chunk = chunks[-1]
        assert final_chunk.is_final is True
        assert final_chunk.model == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_text_completion_streaming_concatenation(self, text_completion_processor_streaming):
        """Test that chunks concatenate to form complete response"""
        # Arrange
        system_prompt = "You are a helpful assistant."
        user_prompt = "What is AI?"

        # Act - Collect all chunk texts
        chunk_texts = []
        async for chunk in text_completion_processor_streaming.generate_content_stream(
            system_prompt, user_prompt
        ):
            if chunk.text and not chunk.is_final:
                chunk_texts.append(chunk.text)

        # Assert
        full_text = "".join(chunk_texts)
        assert len(full_text) > 0
        assert len(chunk_texts) > 1  # Should have multiple chunks

        # Verify completeness - should be a coherent sentence
        assert full_text == "Machine learning is a subset of AI that enables computers to learn from data."

    @pytest.mark.asyncio
    async def test_text_completion_streaming_final_marker(self, text_completion_processor_streaming):
        """Test that final chunk properly marks end of stream"""
        # Arrange
        system_prompt = "You are a helpful assistant."
        user_prompt = "Test query"

        # Act
        chunks = []
        async for chunk in text_completion_processor_streaming.generate_content_stream(
            system_prompt, user_prompt
        ):
            chunks.append(chunk)

        # Assert
        # Should have at least content chunks + final marker
        assert len(chunks) >= 2

        # Only the last chunk should have is_final=True
        for chunk in chunks[:-1]:
            assert chunk.is_final is False

        assert chunks[-1].is_final is True

    @pytest.mark.asyncio
    async def test_text_completion_streaming_model_parameter(self, mock_streaming_openai_client):
        """Test that model parameter is preserved in streaming"""
        # Arrange
        processor = MagicMock()
        processor.default_model = "gpt-4"
        processor.temperature = 0.5
        processor.max_output = 2048
        processor.openai = mock_streaming_openai_client
        processor.generate_content_stream = Processor.generate_content_stream.__get__(
            processor, Processor
        )

        # Act
        chunks = []
        async for chunk in processor.generate_content_stream("System", "Prompt"):
            chunks.append(chunk)

        # Assert
        # Verify OpenAI was called with correct model
        call_args = mock_streaming_openai_client.chat.completions.create.call_args
        assert call_args.kwargs['model'] == "gpt-4"
        assert call_args.kwargs['temperature'] == 0.5
        assert call_args.kwargs['max_tokens'] == 2048
        assert call_args.kwargs['stream'] is True

        # Verify chunks have correct model
        for chunk in chunks:
            assert chunk.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_text_completion_streaming_temperature_parameter(self, mock_streaming_openai_client):
        """Test that temperature parameter is applied in streaming"""
        # Arrange
        temperatures = [0.0, 0.5, 1.0, 1.5]

        for temp in temperatures:
            processor = MagicMock()
            processor.default_model = "gpt-3.5-turbo"
            processor.temperature = temp
            processor.max_output = 1024
            processor.openai = mock_streaming_openai_client
            processor.generate_content_stream = Processor.generate_content_stream.__get__(
                processor, Processor
            )

            # Act
            chunks = []
            async for chunk in processor.generate_content_stream("System", "Prompt"):
                chunks.append(chunk)
                if chunk.is_final:
                    break

            # Assert
            call_args = mock_streaming_openai_client.chat.completions.create.call_args
            assert call_args.kwargs['temperature'] == temp

            # Reset mock for next iteration
            mock_streaming_openai_client.reset_mock()

    @pytest.mark.asyncio
    async def test_text_completion_streaming_error_propagation(self):
        """Test that errors during streaming are properly propagated"""
        # Arrange
        mock_client = MagicMock()

        def failing_stream(**kwargs):
            yield from []
            raise Exception("Streaming error")

        mock_client.chat.completions.create.return_value = failing_stream()

        processor = MagicMock()
        processor.default_model = "gpt-3.5-turbo"
        processor.temperature = 0.7
        processor.max_output = 1024
        processor.openai = mock_client
        processor.generate_content_stream = Processor.generate_content_stream.__get__(
            processor, Processor
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            async for chunk in processor.generate_content_stream("System", "Prompt"):
                pass

        assert "Streaming error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_text_completion_streaming_empty_chunks_filtered(self, mock_streaming_openai_client):
        """Test that empty chunks are handled correctly"""
        # Arrange - Mock that returns some empty chunks
        def create_streaming_with_empties(**kwargs):
            chunks_text = ["Hello", "", " world", "", "!"]

            for text in chunks_text:
                delta = ChoiceDelta(content=text if text else None, role=None)
                choice = StreamChoice(index=0, delta=delta, finish_reason=None)
                chunk = ChatCompletionChunk(
                    id="chatcmpl-streaming",
                    choices=[choice],
                    created=1234567890,
                    model="gpt-3.5-turbo",
                    object="chat.completion.chunk"
                )
                yield chunk

        mock_streaming_openai_client.chat.completions.create.return_value = create_streaming_with_empties()

        processor = MagicMock()
        processor.default_model = "gpt-3.5-turbo"
        processor.temperature = 0.7
        processor.max_output = 1024
        processor.openai = mock_streaming_openai_client
        processor.generate_content_stream = Processor.generate_content_stream.__get__(
            processor, Processor
        )

        # Act
        chunks = []
        async for chunk in processor.generate_content_stream("System", "Prompt"):
            chunks.append(chunk)

        # Assert - Only non-empty chunks should be yielded (plus final marker)
        text_chunks = [c for c in chunks if not c.is_final]
        assert len(text_chunks) == 3  # "Hello", " world", "!"
        assert "".join(c.text for c in text_chunks) == "Hello world!"

    @pytest.mark.asyncio
    async def test_text_completion_streaming_prompt_construction(self, mock_streaming_openai_client):
        """Test that system and user prompts are correctly combined for streaming"""
        # Arrange
        processor = MagicMock()
        processor.default_model = "gpt-3.5-turbo"
        processor.temperature = 0.7
        processor.max_output = 1024
        processor.openai = mock_streaming_openai_client
        processor.generate_content_stream = Processor.generate_content_stream.__get__(
            processor, Processor
        )

        system_prompt = "You are an expert."
        user_prompt = "Explain quantum physics."

        # Act
        chunks = []
        async for chunk in processor.generate_content_stream(system_prompt, user_prompt):
            chunks.append(chunk)
            if chunk.is_final:
                break

        # Assert - Verify prompts were combined correctly
        call_args = mock_streaming_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        assert len(messages) == 1

        message_content = messages[0]['content'][0]['text']
        assert system_prompt in message_content
        assert user_prompt in message_content
        assert message_content.startswith(system_prompt)

    @pytest.mark.asyncio
    async def test_text_completion_streaming_chunk_count(self, text_completion_processor_streaming):
        """Test that streaming produces expected number of chunks"""
        # Arrange
        system_prompt = "You are a helpful assistant."
        user_prompt = "Test"

        # Act
        chunks = []
        async for chunk in text_completion_processor_streaming.generate_content_stream(
            system_prompt, user_prompt
        ):
            chunks.append(chunk)

        # Assert
        # Should have 15 content chunks + 1 final marker = 16 total
        assert len(chunks) == 16

        # 15 content chunks
        content_chunks = [c for c in chunks if not c.is_final]
        assert len(content_chunks) == 15

        # 1 final marker
        final_chunks = [c for c in chunks if c.is_final]
        assert len(final_chunks) == 1
