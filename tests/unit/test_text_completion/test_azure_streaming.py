"""
Tests for Azure serverless endpoint streaming: model override during streaming,
HTTP 429 during streaming, SSE chunk parsing, and final token count emission.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.model.text_completion.azure.llm import Processor
from trustgraph.base import LlmChunk
from trustgraph.exceptions import TooManyRequests


def _make_processor(mock_requests, model="AzureAI", temperature=0.0):
    """Create a Processor with mocked base classes."""
    with patch('trustgraph.base.async_processor.AsyncProcessor.__init__',
               return_value=None), \
         patch('trustgraph.base.llm_service.LlmService.__init__',
               return_value=None):
        proc = Processor(
            endpoint="https://test.azure.com/v1/chat/completions",
            token="test-token",
            temperature=temperature,
            max_output=4192,
            model=model,
            concurrency=1,
            taskgroup=AsyncMock(),
            id="test-processor",
        )
    return proc


def _sse_lines(*data_items):
    """Build SSE byte lines from data items.  '[DONE]' is appended."""
    lines = []
    for item in data_items:
        if isinstance(item, dict):
            lines.append(f"data: {json.dumps(item)}".encode())
        else:
            lines.append(f"data: {item}".encode())
    lines.append(b"data: [DONE]")
    return lines


class TestAzureServerlessStreaming(IsolatedAsyncioTestCase):

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    async def test_streaming_yields_chunks(self, mock_requests):
        proc = _make_processor(mock_requests)

        chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " world"}}]},
            {"usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = _sse_lines(*chunks)
        mock_requests.post.return_value = mock_response

        results = []
        async for chunk in proc.generate_content_stream("sys", "user"):
            results.append(chunk)

        # Content chunks + final chunk
        assert len(results) == 3
        assert results[0].text == "Hello"
        assert results[0].is_final is False
        assert results[1].text == " world"
        assert results[1].is_final is False
        assert results[2].is_final is True
        assert results[2].in_token == 10
        assert results[2].out_token == 5

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    async def test_streaming_model_override(self, mock_requests):
        proc = _make_processor(mock_requests, model="default-model")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = _sse_lines(
            {"choices": [{"delta": {"content": "ok"}}]},
            {"usage": {"prompt_tokens": 5, "completion_tokens": 2}},
        )
        mock_requests.post.return_value = mock_response

        results = []
        async for chunk in proc.generate_content_stream(
            "sys", "user", model="override-model"
        ):
            results.append(chunk)

        # All chunks should carry the overridden model name
        for r in results:
            assert r.model == "override-model"

        # Verify the request body used the overridden model
        call_args = mock_requests.post.call_args
        body = json.loads(call_args[1]["data"])
        assert body["model"] == "override-model"

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    async def test_streaming_temperature_override(self, mock_requests):
        proc = _make_processor(mock_requests, temperature=0.0)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = _sse_lines(
            {"choices": [{"delta": {"content": "ok"}}]},
            {"usage": {"prompt_tokens": 5, "completion_tokens": 2}},
        )
        mock_requests.post.return_value = mock_response

        results = []
        async for chunk in proc.generate_content_stream(
            "sys", "user", temperature=0.9
        ):
            results.append(chunk)

        call_args = mock_requests.post.call_args
        body = json.loads(call_args[1]["data"])
        assert body["temperature"] == 0.9

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    async def test_streaming_429_raises_too_many_requests(self, mock_requests):
        proc = _make_processor(mock_requests)

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_requests.post.return_value = mock_response

        with pytest.raises(TooManyRequests):
            async for _ in proc.generate_content_stream("sys", "user"):
                pass

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    async def test_streaming_http_error_raises_runtime(self, mock_requests):
        proc = _make_processor(mock_requests)

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_requests.post.return_value = mock_response

        with pytest.raises(RuntimeError, match="HTTP 503"):
            async for _ in proc.generate_content_stream("sys", "user"):
                pass

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    async def test_streaming_includes_stream_options(self, mock_requests):
        """Verify stream=True and stream_options in request body."""
        proc = _make_processor(mock_requests)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = _sse_lines(
            {"usage": {"prompt_tokens": 0, "completion_tokens": 0}},
        )
        mock_requests.post.return_value = mock_response

        async for _ in proc.generate_content_stream("sys", "user"):
            pass

        call_args = mock_requests.post.call_args
        body = json.loads(call_args[1]["data"])
        assert body["stream"] is True
        assert body["stream_options"]["include_usage"] is True

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    async def test_streaming_malformed_json_skipped(self, mock_requests):
        """Malformed JSON chunks should be skipped, not crash the stream."""
        proc = _make_processor(mock_requests)

        mock_response = MagicMock()
        mock_response.status_code = 200
        lines = [
            b"data: {not valid json}",
            f'data: {json.dumps({"choices": [{"delta": {"content": "ok"}}]})}'.encode(),
            f'data: {json.dumps({"usage": {"prompt_tokens": 1, "completion_tokens": 1}})}'.encode(),
            b"data: [DONE]",
        ]
        mock_response.iter_lines.return_value = lines
        mock_requests.post.return_value = mock_response

        results = []
        async for chunk in proc.generate_content_stream("sys", "user"):
            results.append(chunk)

        # Should get the valid content chunk + final chunk
        assert any(r.text == "ok" for r in results)
        assert results[-1].is_final is True

    @patch('trustgraph.model.text_completion.azure.llm.requests')
    async def test_streaming_supports_streaming_flag(self, mock_requests):
        proc = _make_processor(mock_requests)
        assert proc.supports_streaming() is True
