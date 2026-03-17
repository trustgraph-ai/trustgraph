"""
Tests for tool service lifecycle, invoke contract, streaming responses,
multi-tenancy, and error propagation.

Tests the actual DynamicToolService, ToolService, and ToolServiceClient
classes rather than plain dicts.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.schema import (
    ToolServiceRequest, ToolServiceResponse, Error,
    ToolRequest, ToolResponse,
)
from trustgraph.exceptions import TooManyRequests


# ---------------------------------------------------------------------------
# DynamicToolService tests
# ---------------------------------------------------------------------------

class TestDynamicToolServiceInvokeContract:

    @pytest.mark.asyncio
    async def test_base_invoke_raises_not_implemented(self):
        """Base class invoke() should raise NotImplementedError."""
        from trustgraph.base.dynamic_tool_service import DynamicToolService

        svc = DynamicToolService.__new__(DynamicToolService)

        with pytest.raises(NotImplementedError):
            await svc.invoke("user", {}, {})

    @pytest.mark.asyncio
    async def test_on_request_calls_invoke_with_parsed_args(self):
        """on_request should JSON-parse config/arguments and pass to invoke."""
        from trustgraph.base.dynamic_tool_service import DynamicToolService

        svc = DynamicToolService.__new__(DynamicToolService)
        svc.id = "test-svc"
        svc.producer = AsyncMock()

        calls = []

        async def tracking_invoke(user, config, arguments):
            calls.append({"user": user, "config": config, "arguments": arguments})
            return "ok"

        svc.invoke = tracking_invoke

        # Ensure the class-level metric exists
        if not hasattr(DynamicToolService, "tool_service_metric"):
            DynamicToolService.tool_service_metric = MagicMock()

        msg = MagicMock()
        msg.value.return_value = ToolServiceRequest(
            user="alice",
            config='{"style": "pun"}',
            arguments='{"topic": "cats"}',
        )
        msg.properties.return_value = {"id": "req-1"}

        await svc.on_request(msg, MagicMock(), None)

        assert len(calls) == 1
        assert calls[0]["user"] == "alice"
        assert calls[0]["config"] == {"style": "pun"}
        assert calls[0]["arguments"] == {"topic": "cats"}

    @pytest.mark.asyncio
    async def test_on_request_empty_user_defaults_to_trustgraph(self):
        """Empty user field should default to 'trustgraph'."""
        from trustgraph.base.dynamic_tool_service import DynamicToolService

        svc = DynamicToolService.__new__(DynamicToolService)
        svc.id = "test-svc"
        svc.producer = AsyncMock()

        received_user = None

        async def capture_invoke(user, config, arguments):
            nonlocal received_user
            received_user = user
            return "ok"

        svc.invoke = capture_invoke

        if not hasattr(DynamicToolService, "tool_service_metric"):
            DynamicToolService.tool_service_metric = MagicMock()

        msg = MagicMock()
        msg.value.return_value = ToolServiceRequest(user="", config="", arguments="")
        msg.properties.return_value = {"id": "req-2"}

        await svc.on_request(msg, MagicMock(), None)

        assert received_user == "trustgraph"

    @pytest.mark.asyncio
    async def test_on_request_string_response_sent_directly(self):
        """String return from invoke → response field is the string."""
        from trustgraph.base.dynamic_tool_service import DynamicToolService

        svc = DynamicToolService.__new__(DynamicToolService)
        svc.id = "test-svc"
        svc.producer = AsyncMock()

        async def string_invoke(user, config, arguments):
            return "hello world"

        svc.invoke = string_invoke

        if not hasattr(DynamicToolService, "tool_service_metric"):
            DynamicToolService.tool_service_metric = MagicMock()

        msg = MagicMock()
        msg.value.return_value = ToolServiceRequest(user="u", config="{}", arguments="{}")
        msg.properties.return_value = {"id": "r1"}

        await svc.on_request(msg, MagicMock(), None)

        sent = svc.producer.send.call_args[0][0]
        assert isinstance(sent, ToolServiceResponse)
        assert sent.response == "hello world"
        assert sent.end_of_stream is True
        assert sent.error is None

    @pytest.mark.asyncio
    async def test_on_request_dict_response_json_encoded(self):
        """Dict return from invoke → response field is JSON-encoded."""
        from trustgraph.base.dynamic_tool_service import DynamicToolService

        svc = DynamicToolService.__new__(DynamicToolService)
        svc.id = "test-svc"
        svc.producer = AsyncMock()

        async def dict_invoke(user, config, arguments):
            return {"result": 42}

        svc.invoke = dict_invoke

        if not hasattr(DynamicToolService, "tool_service_metric"):
            DynamicToolService.tool_service_metric = MagicMock()

        msg = MagicMock()
        msg.value.return_value = ToolServiceRequest(user="u", config="{}", arguments="{}")
        msg.properties.return_value = {"id": "r2"}

        await svc.on_request(msg, MagicMock(), None)

        sent = svc.producer.send.call_args[0][0]
        assert json.loads(sent.response) == {"result": 42}

    @pytest.mark.asyncio
    async def test_on_request_error_sends_error_response(self):
        """Exception in invoke → error response sent."""
        from trustgraph.base.dynamic_tool_service import DynamicToolService

        svc = DynamicToolService.__new__(DynamicToolService)
        svc.id = "test-svc"
        svc.producer = AsyncMock()

        async def failing_invoke(user, config, arguments):
            raise ValueError("bad input")

        svc.invoke = failing_invoke

        msg = MagicMock()
        msg.value.return_value = ToolServiceRequest(user="u", config="{}", arguments="{}")
        msg.properties.return_value = {"id": "r3"}

        await svc.on_request(msg, MagicMock(), None)

        sent = svc.producer.send.call_args[0][0]
        assert sent.error is not None
        assert sent.error.type == "tool-service-error"
        assert "bad input" in sent.error.message
        assert sent.response == ""

    @pytest.mark.asyncio
    async def test_on_request_too_many_requests_propagates(self):
        """TooManyRequests should propagate (not caught as error response)."""
        from trustgraph.base.dynamic_tool_service import DynamicToolService

        svc = DynamicToolService.__new__(DynamicToolService)
        svc.id = "test-svc"
        svc.producer = AsyncMock()

        async def rate_limited_invoke(user, config, arguments):
            raise TooManyRequests("rate limited")

        svc.invoke = rate_limited_invoke

        msg = MagicMock()
        msg.value.return_value = ToolServiceRequest(user="u", config="{}", arguments="{}")
        msg.properties.return_value = {"id": "r4"}

        with pytest.raises(TooManyRequests):
            await svc.on_request(msg, MagicMock(), None)

    @pytest.mark.asyncio
    async def test_on_request_preserves_message_id(self):
        """Response should include the original message id in properties."""
        from trustgraph.base.dynamic_tool_service import DynamicToolService

        svc = DynamicToolService.__new__(DynamicToolService)
        svc.id = "test-svc"
        svc.producer = AsyncMock()

        async def ok_invoke(user, config, arguments):
            return "ok"

        svc.invoke = ok_invoke

        if not hasattr(DynamicToolService, "tool_service_metric"):
            DynamicToolService.tool_service_metric = MagicMock()

        msg = MagicMock()
        msg.value.return_value = ToolServiceRequest(user="u", config="{}", arguments="{}")
        msg.properties.return_value = {"id": "unique-42"}

        await svc.on_request(msg, MagicMock(), None)

        props = svc.producer.send.call_args[1]["properties"]
        assert props["id"] == "unique-42"


# ---------------------------------------------------------------------------
# ToolService (flow-based) tests
# ---------------------------------------------------------------------------

class TestToolServiceOnRequest:

    @pytest.mark.asyncio
    async def test_string_response_sent_as_text(self):
        """String return from invoke_tool → ToolResponse.text is set."""
        from trustgraph.base.tool_service import ToolService

        svc = ToolService.__new__(ToolService)
        svc.id = "test-tool"

        async def mock_invoke(name, params):
            return "tool result"

        svc.invoke_tool = mock_invoke

        if not hasattr(ToolService, "tool_invocation_metric"):
            ToolService.tool_invocation_metric = MagicMock()

        mock_response_pub = AsyncMock()
        flow = MagicMock()
        flow.name = "test-flow"

        def flow_callable(name):
            if name == "response":
                return mock_response_pub
            return MagicMock()

        flow_callable.producer = {"response": mock_response_pub}
        flow_callable.name = "test-flow"

        msg = MagicMock()
        msg.value.return_value = ToolRequest(name="my-tool", parameters='{"key": "val"}')
        msg.properties.return_value = {"id": "t1"}

        await svc.on_request(msg, MagicMock(), flow_callable)

        sent = mock_response_pub.send.call_args[0][0]
        assert isinstance(sent, ToolResponse)
        assert sent.text == "tool result"
        assert sent.object is None

    @pytest.mark.asyncio
    async def test_dict_response_sent_as_json_object(self):
        """Dict return from invoke_tool → ToolResponse.object is JSON."""
        from trustgraph.base.tool_service import ToolService

        svc = ToolService.__new__(ToolService)
        svc.id = "test-tool"

        async def mock_invoke(name, params):
            return {"data": [1, 2, 3]}

        svc.invoke_tool = mock_invoke

        if not hasattr(ToolService, "tool_invocation_metric"):
            ToolService.tool_invocation_metric = MagicMock()

        mock_response_pub = AsyncMock()
        flow = MagicMock()

        def flow_callable(name):
            if name == "response":
                return mock_response_pub
            return MagicMock()

        flow_callable.producer = {"response": mock_response_pub}
        flow_callable.name = "test-flow"

        msg = MagicMock()
        msg.value.return_value = ToolRequest(name="my-tool", parameters="{}")
        msg.properties.return_value = {"id": "t2"}

        await svc.on_request(msg, MagicMock(), flow_callable)

        sent = mock_response_pub.send.call_args[0][0]
        assert sent.text is None
        assert json.loads(sent.object) == {"data": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_error_sends_error_response(self):
        """Exception in invoke_tool → error response via flow producer."""
        from trustgraph.base.tool_service import ToolService

        svc = ToolService.__new__(ToolService)
        svc.id = "test-tool"

        async def failing_invoke(name, params):
            raise RuntimeError("tool broke")

        svc.invoke_tool = failing_invoke

        mock_response_pub = AsyncMock()
        flow = MagicMock()

        def flow_callable(name):
            return MagicMock()

        flow_callable.producer = {"response": mock_response_pub}
        flow_callable.name = "test-flow"

        msg = MagicMock()
        msg.value.return_value = ToolRequest(name="my-tool", parameters="{}")
        msg.properties.return_value = {"id": "t3"}

        await svc.on_request(msg, MagicMock(), flow_callable)

        sent = mock_response_pub.send.call_args[0][0]
        assert sent.error is not None
        assert sent.error.type == "tool-error"
        assert "tool broke" in sent.error.message

    @pytest.mark.asyncio
    async def test_too_many_requests_propagates(self):
        """TooManyRequests should propagate from ToolService.on_request."""
        from trustgraph.base.tool_service import ToolService

        svc = ToolService.__new__(ToolService)
        svc.id = "test-tool"

        async def rate_limited(name, params):
            raise TooManyRequests("slow down")

        svc.invoke_tool = rate_limited

        msg = MagicMock()
        msg.value.return_value = ToolRequest(name="my-tool", parameters="{}")
        msg.properties.return_value = {"id": "t4"}

        flow = MagicMock()
        flow.producer = {"response": AsyncMock()}
        flow.name = "test-flow"

        with pytest.raises(TooManyRequests):
            await svc.on_request(msg, MagicMock(), flow)

    @pytest.mark.asyncio
    async def test_parameters_json_parsed(self):
        """Parameters should be JSON-parsed before passing to invoke_tool."""
        from trustgraph.base.tool_service import ToolService

        svc = ToolService.__new__(ToolService)
        svc.id = "test-tool"

        received = {}

        async def capture_invoke(name, params):
            received["name"] = name
            received["params"] = params
            return "ok"

        svc.invoke_tool = capture_invoke

        if not hasattr(ToolService, "tool_invocation_metric"):
            ToolService.tool_invocation_metric = MagicMock()

        mock_pub = AsyncMock()
        flow = lambda name: mock_pub
        flow.producer = {"response": mock_pub}
        flow.name = "f"

        msg = MagicMock()
        msg.value.return_value = ToolRequest(
            name="search",
            parameters='{"query": "test", "limit": 10}',
        )
        msg.properties.return_value = {"id": "t5"}

        await svc.on_request(msg, MagicMock(), flow)

        assert received["name"] == "search"
        assert received["params"] == {"query": "test", "limit": 10}


# ---------------------------------------------------------------------------
# ToolServiceClient tests
# ---------------------------------------------------------------------------

class TestToolServiceClientCall:

    @pytest.mark.asyncio
    async def test_call_sends_request_and_returns_response(self):
        """call() should send ToolServiceRequest and return response string."""
        from trustgraph.base.tool_service_client import ToolServiceClient

        client = ToolServiceClient.__new__(ToolServiceClient)
        client.request = AsyncMock(return_value=ToolServiceResponse(
            error=None, response="joke result", end_of_stream=True,
        ))

        result = await client.call(
            user="alice",
            config={"style": "pun"},
            arguments={"topic": "cats"},
        )

        assert result == "joke result"

        req = client.request.call_args[0][0]
        assert isinstance(req, ToolServiceRequest)
        assert req.user == "alice"
        assert json.loads(req.config) == {"style": "pun"}
        assert json.loads(req.arguments) == {"topic": "cats"}

    @pytest.mark.asyncio
    async def test_call_raises_on_error(self):
        """call() should raise RuntimeError when response has error."""
        from trustgraph.base.tool_service_client import ToolServiceClient

        client = ToolServiceClient.__new__(ToolServiceClient)
        client.request = AsyncMock(return_value=ToolServiceResponse(
            error=Error(type="tool-service-error", message="service down"),
            response="",
        ))

        with pytest.raises(RuntimeError, match="service down"):
            await client.call(user="u", config={}, arguments={})

    @pytest.mark.asyncio
    async def test_call_empty_config_sends_empty_json(self):
        """Empty config/arguments should be sent as '{}'."""
        from trustgraph.base.tool_service_client import ToolServiceClient

        client = ToolServiceClient.__new__(ToolServiceClient)
        client.request = AsyncMock(return_value=ToolServiceResponse(
            error=None, response="ok",
        ))

        await client.call(user="u", config=None, arguments=None)

        req = client.request.call_args[0][0]
        assert req.config == "{}"
        assert req.arguments == "{}"

    @pytest.mark.asyncio
    async def test_call_passes_timeout(self):
        """call() should forward timeout to underlying request."""
        from trustgraph.base.tool_service_client import ToolServiceClient

        client = ToolServiceClient.__new__(ToolServiceClient)
        client.request = AsyncMock(return_value=ToolServiceResponse(
            error=None, response="ok",
        ))

        await client.call(user="u", config={}, arguments={}, timeout=30)

        _, kwargs = client.request.call_args
        assert kwargs["timeout"] == 30


class TestToolServiceClientStreaming:

    @pytest.mark.asyncio
    async def test_call_streaming_collects_chunks(self):
        """call_streaming should accumulate chunks and return full result."""
        from trustgraph.base.tool_service_client import ToolServiceClient

        client = ToolServiceClient.__new__(ToolServiceClient)

        # Simulate streaming: request() calls recipient with each chunk
        chunks = [
            ToolServiceResponse(error=None, response="chunk1", end_of_stream=False),
            ToolServiceResponse(error=None, response="chunk2", end_of_stream=True),
        ]

        async def mock_request(req, timeout=600, recipient=None):
            for chunk in chunks:
                done = await recipient(chunk)
                if done:
                    break

        client.request = mock_request

        received = []

        async def callback(text):
            received.append(text)

        result = await client.call_streaming(
            user="u", config={}, arguments={}, callback=callback,
        )

        assert result == "chunk1chunk2"
        assert received == ["chunk1", "chunk2"]

    @pytest.mark.asyncio
    async def test_call_streaming_raises_on_error(self):
        """call_streaming should raise RuntimeError on error chunk."""
        from trustgraph.base.tool_service_client import ToolServiceClient

        client = ToolServiceClient.__new__(ToolServiceClient)

        async def mock_request(req, timeout=600, recipient=None):
            error_resp = ToolServiceResponse(
                error=Error(type="tool-service-error", message="stream failed"),
                response="",
                end_of_stream=True,
            )
            await recipient(error_resp)

        client.request = mock_request

        with pytest.raises(RuntimeError, match="stream failed"):
            await client.call_streaming(
                user="u", config={}, arguments={},
                callback=AsyncMock(),
            )

    @pytest.mark.asyncio
    async def test_call_streaming_skips_empty_response(self):
        """Empty response chunks should not be added to result."""
        from trustgraph.base.tool_service_client import ToolServiceClient

        client = ToolServiceClient.__new__(ToolServiceClient)

        chunks = [
            ToolServiceResponse(error=None, response="", end_of_stream=False),
            ToolServiceResponse(error=None, response="data", end_of_stream=True),
        ]

        async def mock_request(req, timeout=600, recipient=None):
            for chunk in chunks:
                done = await recipient(chunk)
                if done:
                    break

        client.request = mock_request

        received = []

        async def callback(text):
            received.append(text)

        result = await client.call_streaming(
            user="u", config={}, arguments={}, callback=callback,
        )

        # Empty response is falsy, so callback shouldn't be called for it
        assert result == "data"
        assert received == ["data"]


# ---------------------------------------------------------------------------
# Multi-tenancy
# ---------------------------------------------------------------------------

class TestMultiTenancy:

    @pytest.mark.asyncio
    async def test_user_propagated_to_invoke(self):
        """User from request should reach the invoke method."""
        from trustgraph.base.dynamic_tool_service import DynamicToolService

        svc = DynamicToolService.__new__(DynamicToolService)
        svc.id = "test"
        svc.producer = AsyncMock()

        users_seen = []

        async def tracking(user, config, arguments):
            users_seen.append(user)
            return "ok"

        svc.invoke = tracking

        if not hasattr(DynamicToolService, "tool_service_metric"):
            DynamicToolService.tool_service_metric = MagicMock()

        for u in ["tenant-a", "tenant-b", "tenant-c"]:
            msg = MagicMock()
            msg.value.return_value = ToolServiceRequest(
                user=u, config="{}", arguments="{}",
            )
            msg.properties.return_value = {"id": f"req-{u}"}
            await svc.on_request(msg, MagicMock(), None)

        assert users_seen == ["tenant-a", "tenant-b", "tenant-c"]

    @pytest.mark.asyncio
    async def test_client_sends_user_in_request(self):
        """ToolServiceClient.call should include user in request."""
        from trustgraph.base.tool_service_client import ToolServiceClient

        client = ToolServiceClient.__new__(ToolServiceClient)
        client.request = AsyncMock(return_value=ToolServiceResponse(
            error=None, response="ok",
        ))

        await client.call(user="isolated-tenant", config={}, arguments={})

        req = client.request.call_args[0][0]
        assert req.user == "isolated-tenant"
