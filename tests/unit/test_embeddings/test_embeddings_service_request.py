"""
Tests for EmbeddingsService.on_request — the request handler that dispatches
to on_embeddings and sends responses.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.base import EmbeddingsService
from trustgraph.schema import EmbeddingsRequest, EmbeddingsResponse, Error
from trustgraph.exceptions import TooManyRequests


class StubEmbeddingsService(EmbeddingsService):
    """Minimal concrete implementation for testing on_request."""

    def __init__(self, embed_result=None, embed_error=None):
        # Skip super().__init__ to avoid taskgroup/registration
        self.embed_result = embed_result or [[0.1, 0.2]]
        self.embed_error = embed_error

    async def on_embeddings(self, texts, model=None):
        if self.embed_error:
            raise self.embed_error
        return self.embed_result


def _make_msg(texts, msg_id="req-1"):
    request = EmbeddingsRequest(texts=texts)
    msg = MagicMock()
    msg.value.return_value = request
    msg.properties.return_value = {"id": msg_id}
    return msg


def _make_flow(model="test-model"):
    mock_response_producer = AsyncMock()
    mock_flow = MagicMock()

    def flow_callable(name):
        if name == "model":
            return model
        if name == "response":
            return mock_response_producer
        return MagicMock()

    flow_callable.producer = {"response": mock_response_producer}
    return flow_callable, mock_response_producer


class TestEmbeddingsServiceOnRequest:

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """on_request should call on_embeddings and send response."""
        service = StubEmbeddingsService(embed_result=[[0.1, 0.2], [0.3, 0.4]])
        msg = _make_msg(["hello", "world"], msg_id="r1")
        flow, mock_response = _make_flow(model="my-model")

        await service.on_request(msg, MagicMock(), flow)

        mock_response.send.assert_called_once()
        resp = mock_response.send.call_args[0][0]
        assert isinstance(resp, EmbeddingsResponse)
        assert resp.error is None
        assert resp.vectors == [[0.1, 0.2], [0.3, 0.4]]

        # Check id is passed through
        props = mock_response.send.call_args[1]["properties"]
        assert props["id"] == "r1"

    @pytest.mark.asyncio
    async def test_passes_model_from_flow(self):
        """on_request should pass model parameter from flow to on_embeddings."""
        calls = []

        class TrackingService(EmbeddingsService):
            def __init__(self):
                pass

            async def on_embeddings(self, texts, model=None):
                calls.append({"texts": texts, "model": model})
                return [[0.0]]

        service = TrackingService()
        msg = _make_msg(["test"])
        flow, _ = _make_flow(model="custom-model-v2")

        await service.on_request(msg, MagicMock(), flow)

        assert len(calls) == 1
        assert calls[0]["model"] == "custom-model-v2"
        assert calls[0]["texts"] == ["test"]

    @pytest.mark.asyncio
    async def test_error_sends_error_response(self):
        """Non-rate-limit errors should send an error response."""
        service = StubEmbeddingsService(
            embed_error=ValueError("dimension mismatch")
        )
        msg = _make_msg(["test"], msg_id="r2")
        flow, mock_response = _make_flow()

        await service.on_request(msg, MagicMock(), flow)

        mock_response.send.assert_called_once()
        resp = mock_response.send.call_args[0][0]
        assert resp.error is not None
        assert resp.error.type == "embeddings-error"
        assert "dimension mismatch" in resp.error.message
        assert resp.vectors == []

    @pytest.mark.asyncio
    async def test_rate_limit_propagates(self):
        """TooManyRequests should propagate (not caught as error response)."""
        service = StubEmbeddingsService(
            embed_error=TooManyRequests("rate limited")
        )
        msg = _make_msg(["test"])
        flow, _ = _make_flow()

        with pytest.raises(TooManyRequests):
            await service.on_request(msg, MagicMock(), flow)

    @pytest.mark.asyncio
    async def test_message_id_preserved(self):
        """The request message id should be forwarded in the response properties."""
        service = StubEmbeddingsService()
        msg = _make_msg(["test"], msg_id="unique-id-42")
        flow, mock_response = _make_flow()

        await service.on_request(msg, MagicMock(), flow)

        props = mock_response.send.call_args[1]["properties"]
        assert props["id"] == "unique-id-42"
