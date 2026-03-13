"""
Tests for Azure OpenAI streaming: model/temperature override during streaming,
RateLimitError → TooManyRequests conversion, chunk iteration, and final token
count emission.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.model.text_completion.azure_openai.llm import Processor
from trustgraph.base import LlmChunk
from trustgraph.exceptions import TooManyRequests


def _make_processor(mock_azure_openai_class, model="gpt-4"):
    """Create a Processor with mocked base classes."""
    with patch('trustgraph.base.async_processor.AsyncProcessor.__init__',
               return_value=None), \
         patch('trustgraph.base.llm_service.LlmService.__init__',
               return_value=None):
        proc = Processor(
            endpoint="https://test.openai.azure.com/",
            token="test-token",
            api_version="2024-12-01-preview",
            model=model,
            temperature=0.0,
            max_output=4192,
            concurrency=1,
            taskgroup=AsyncMock(),
            id="test-processor",
        )
    return proc


def _make_stream_chunk(content=None, usage=None):
    """Create a mock streaming chunk."""
    chunk = MagicMock()
    if content:
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = content
    else:
        chunk.choices = []
    chunk.usage = usage
    return chunk


class TestAzureOpenAIStreaming(IsolatedAsyncioTestCase):

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    async def test_streaming_yields_chunks(self, mock_azure_class):
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client
        proc = _make_processor(mock_azure_class)

        usage = MagicMock()
        usage.prompt_tokens = 10
        usage.completion_tokens = 5

        stream_data = [
            _make_stream_chunk(content="Hello"),
            _make_stream_chunk(content=" world"),
            _make_stream_chunk(usage=usage),
        ]
        mock_client.chat.completions.create.return_value = iter(stream_data)

        results = []
        async for chunk in proc.generate_content_stream("sys", "user"):
            results.append(chunk)

        assert len(results) == 3  # 2 content + 1 final
        assert results[0].text == "Hello"
        assert results[0].is_final is False
        assert results[1].text == " world"
        assert results[2].is_final is True
        assert results[2].in_token == 10
        assert results[2].out_token == 5

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    async def test_streaming_model_override(self, mock_azure_class):
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client
        proc = _make_processor(mock_azure_class, model="gpt-4")

        usage = MagicMock()
        usage.prompt_tokens = 5
        usage.completion_tokens = 2

        stream_data = [
            _make_stream_chunk(content="ok"),
            _make_stream_chunk(usage=usage),
        ]
        mock_client.chat.completions.create.return_value = iter(stream_data)

        results = []
        async for chunk in proc.generate_content_stream(
            "sys", "user", model="gpt-4o"
        ):
            results.append(chunk)

        # All chunks carry overridden model
        for r in results:
            assert r.model == "gpt-4o"

        # Verify API call used overridden model
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    async def test_streaming_temperature_override(self, mock_azure_class):
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client
        proc = _make_processor(mock_azure_class)

        usage = MagicMock()
        usage.prompt_tokens = 5
        usage.completion_tokens = 2

        stream_data = [_make_stream_chunk(usage=usage)]
        mock_client.chat.completions.create.return_value = iter(stream_data)

        async for _ in proc.generate_content_stream(
            "sys", "user", temperature=0.7
        ):
            pass

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    async def test_streaming_rate_limit_raises_too_many_requests(self, mock_azure_class):
        from openai import RateLimitError

        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client
        proc = _make_processor(mock_azure_class)

        mock_client.chat.completions.create.side_effect = RateLimitError(
            "Rate limit exceeded", response=MagicMock(), body=None
        )

        with pytest.raises(TooManyRequests):
            async for _ in proc.generate_content_stream("sys", "user"):
                pass

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    async def test_streaming_generic_exception_propagates(self, mock_azure_class):
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client
        proc = _make_processor(mock_azure_class)

        mock_client.chat.completions.create.side_effect = Exception("API down")

        with pytest.raises(Exception, match="API down"):
            async for _ in proc.generate_content_stream("sys", "user"):
                pass

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    async def test_streaming_passes_stream_options(self, mock_azure_class):
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client
        proc = _make_processor(mock_azure_class)

        usage = MagicMock()
        usage.prompt_tokens = 0
        usage.completion_tokens = 0
        stream_data = [_make_stream_chunk(usage=usage)]
        mock_client.chat.completions.create.return_value = iter(stream_data)

        async for _ in proc.generate_content_stream("sys", "user"):
            pass

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["stream"] is True
        assert call_kwargs["stream_options"] == {"include_usage": True}

    @patch('trustgraph.model.text_completion.azure_openai.llm.AzureOpenAI')
    async def test_supports_streaming(self, mock_azure_class):
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client
        proc = _make_processor(mock_azure_class)
        assert proc.supports_streaming() is True
