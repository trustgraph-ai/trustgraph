"""
Unit tests for PromptClient streaming callback behavior.

These tests verify that the prompt client correctly passes the end_of_stream
flag to chunk callbacks, ensuring proper streaming protocol compliance.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch
from trustgraph.base.prompt_client import PromptClient
from trustgraph.schema import PromptResponse


class TestPromptClientStreamingCallback:
    """Test PromptClient streaming callback behavior"""

    @pytest.fixture
    def prompt_client(self):
        """Create a PromptClient with mocked dependencies"""
        # Mock all the required initialization parameters
        with patch.object(PromptClient, '__init__', lambda self: None):
            client = PromptClient()
            return client

    @pytest.fixture
    def mock_request_response(self):
        """Create a mock request/response handler"""
        async def mock_request(request, recipient=None, timeout=600):
            if recipient:
                # Simulate streaming responses
                responses = [
                    PromptResponse(text="Hello", object=None, error=None, end_of_stream=False),
                    PromptResponse(text=" world", object=None, error=None, end_of_stream=False),
                    PromptResponse(text="!", object=None, error=None, end_of_stream=False),
                    PromptResponse(text="", object=None, error=None, end_of_stream=True),
                ]
                for resp in responses:
                    should_stop = await recipient(resp)
                    if should_stop:
                        break
            else:
                # Non-streaming response
                return PromptResponse(text="Hello world!", object=None, error=None)

        return mock_request

    @pytest.mark.asyncio
    async def test_callback_receives_chunk_and_end_of_stream(self, prompt_client, mock_request_response):
        """Test that callback receives both chunk text and end_of_stream flag"""
        # Arrange
        prompt_client.request = mock_request_response

        callback = AsyncMock()

        # Act
        await prompt_client.prompt(
            id="test-prompt",
            variables={"query": "test"},
            streaming=True,
            chunk_callback=callback
        )

        # Assert - callback should be called with (chunk, end_of_stream) signature
        assert callback.call_count == 4

        # Verify first chunk: text + end_of_stream=False
        assert callback.call_args_list[0] == call("Hello", False)

        # Verify second chunk
        assert callback.call_args_list[1] == call(" world", False)

        # Verify third chunk
        assert callback.call_args_list[2] == call("!", False)

        # Verify final chunk: empty text + end_of_stream=True
        assert callback.call_args_list[3] == call("", True)

    @pytest.mark.asyncio
    async def test_callback_receives_empty_final_chunk(self, prompt_client, mock_request_response):
        """Test that empty final chunks are passed to callback"""
        # Arrange
        prompt_client.request = mock_request_response

        chunks_received = []

        async def collect_chunks(chunk, end_of_stream):
            chunks_received.append((chunk, end_of_stream))

        # Act
        await prompt_client.prompt(
            id="test-prompt",
            variables={"query": "test"},
            streaming=True,
            chunk_callback=collect_chunks
        )

        # Assert - should receive the empty final chunk
        final_chunk = chunks_received[-1]
        assert final_chunk == ("", True), "Final chunk should be empty string with end_of_stream=True"

    @pytest.mark.asyncio
    async def test_callback_signature_with_non_empty_final_chunk(self, prompt_client):
        """Test callback signature when LLM sends non-empty final chunk"""
        # Arrange
        async def mock_request_non_empty_final(request, recipient=None, timeout=600):
            if recipient:
                # Some LLMs send content in the final chunk
                responses = [
                    PromptResponse(text="Hello", object=None, error=None, end_of_stream=False),
                    PromptResponse(text=" world!", object=None, error=None, end_of_stream=True),
                ]
                for resp in responses:
                    should_stop = await recipient(resp)
                    if should_stop:
                        break

        prompt_client.request = mock_request_non_empty_final

        callback = AsyncMock()

        # Act
        await prompt_client.prompt(
            id="test-prompt",
            variables={"query": "test"},
            streaming=True,
            chunk_callback=callback
        )

        # Assert
        assert callback.call_count == 2
        assert callback.call_args_list[0] == call("Hello", False)
        assert callback.call_args_list[1] == call(" world!", True)

    @pytest.mark.asyncio
    async def test_callback_not_called_without_text(self, prompt_client):
        """Test that callback is not called for responses without text"""
        # Arrange
        async def mock_request_no_text(request, recipient=None, timeout=600):
            if recipient:
                # Response with only end_of_stream, no text
                responses = [
                    PromptResponse(text="Content", object=None, error=None, end_of_stream=False),
                    PromptResponse(text=None, object=None, error=None, end_of_stream=True),
                ]
                for resp in responses:
                    should_stop = await recipient(resp)
                    if should_stop:
                        break

        prompt_client.request = mock_request_no_text

        callback = AsyncMock()

        # Act
        await prompt_client.prompt(
            id="test-prompt",
            variables={"query": "test"},
            streaming=True,
            chunk_callback=callback
        )

        # Assert - callback should only be called once (for "Content")
        assert callback.call_count == 1
        assert callback.call_args_list[0] == call("Content", False)

    @pytest.mark.asyncio
    async def test_synchronous_callback_also_receives_end_of_stream(self, prompt_client):
        """Test that synchronous callbacks also receive end_of_stream parameter"""
        # Arrange
        async def mock_request(request, recipient=None, timeout=600):
            if recipient:
                responses = [
                    PromptResponse(text="test", object=None, error=None, end_of_stream=False),
                    PromptResponse(text="", object=None, error=None, end_of_stream=True),
                ]
                for resp in responses:
                    should_stop = await recipient(resp)
                    if should_stop:
                        break

        prompt_client.request = mock_request

        callback = MagicMock()  # Synchronous mock

        # Act
        await prompt_client.prompt(
            id="test-prompt",
            variables={"query": "test"},
            streaming=True,
            chunk_callback=callback
        )

        # Assert - synchronous callback should also get both parameters
        assert callback.call_count == 2
        assert callback.call_args_list[0] == call("test", False)
        assert callback.call_args_list[1] == call("", True)

    @pytest.mark.asyncio
    async def test_kg_prompt_passes_parameters_to_callback(self, prompt_client):
        """Test that kg_prompt correctly passes streaming parameters"""
        # Arrange
        async def mock_request(request, recipient=None, timeout=600):
            if recipient:
                responses = [
                    PromptResponse(text="Answer", object=None, error=None, end_of_stream=False),
                    PromptResponse(text="", object=None, error=None, end_of_stream=True),
                ]
                for resp in responses:
                    should_stop = await recipient(resp)
                    if should_stop:
                        break

        prompt_client.request = mock_request

        callback = AsyncMock()

        # Act
        await prompt_client.kg_prompt(
            query="What is machine learning?",
            kg=[("subject", "predicate", "object")],
            streaming=True,
            chunk_callback=callback
        )

        # Assert
        assert callback.call_count == 2
        assert callback.call_args_list[0] == call("Answer", False)
        assert callback.call_args_list[1] == call("", True)

    @pytest.mark.asyncio
    async def test_document_prompt_passes_parameters_to_callback(self, prompt_client):
        """Test that document_prompt correctly passes streaming parameters"""
        # Arrange
        async def mock_request(request, recipient=None, timeout=600):
            if recipient:
                responses = [
                    PromptResponse(text="Summary", object=None, error=None, end_of_stream=False),
                    PromptResponse(text="", object=None, error=None, end_of_stream=True),
                ]
                for resp in responses:
                    should_stop = await recipient(resp)
                    if should_stop:
                        break

        prompt_client.request = mock_request

        callback = AsyncMock()

        # Act
        await prompt_client.document_prompt(
            query="Summarize this",
            documents=["doc1", "doc2"],
            streaming=True,
            chunk_callback=callback
        )

        # Assert
        assert callback.call_count == 2
        assert callback.call_args_list[0] == call("Summary", False)
        assert callback.call_args_list[1] == call("", True)
