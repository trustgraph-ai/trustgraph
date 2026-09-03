"""
Prompt and librarian client timeouts (#874 slice 2): a spec resolves its
timeout from an explicit constructor value, then the processor's CLI
attribute, then the class default, and threads it into the client it creates.
"""

import argparse
import asyncio
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.base.request_response_spec import (
    RequestResponseSpec, _make_impl_wrapper,
)
from trustgraph.base.prompt_client import PromptClientSpec, PromptClient
from trustgraph.base.config_client import ConfigClientSpec
from trustgraph.base.librarian_spec import LibrarianSpec
from trustgraph.base.async_librarian_client import AsyncLibrarianClient
from trustgraph.base.request_response_client import RequestResponseClient
from trustgraph.schema import LibrarianRequest, PromptResponse


REAL_WAIT_FOR = asyncio.wait_for

RR_CREATE = "trustgraph.base.request_response_client.RequestResponseClient.create"
LIB_CREATE = "trustgraph.base.async_librarian_client.AsyncLibrarianClient.create"

TOPICS = {
    "topics": {
        "prompt-request": "q:prompt:req",
        "prompt-response": "q:prompt:resp",
        "config-request": "q:config:req",
        "config-response": "q:config:resp",
        "librarian-request": "q:lib:req",
        "librarian-response": "q:lib:resp",
    }
}


def make_processor(**attrs):
    # SimpleNamespace, not MagicMock: a missing attribute must be missing.
    return SimpleNamespace(async_backend=AsyncMock(), id="proc1", **attrs)


def make_flow():
    flow = MagicMock()
    flow.workspace = "ws"
    flow.name = "f"
    flow.consumer = {}
    return flow


def generic_spec(**kwargs):
    return RequestResponseSpec(
        request_name="prompt-request",
        request_schema=object,
        response_name="prompt-response",
        response_schema=object,
        impl=None,
        **kwargs,
    )


def prompt_spec(**kwargs):
    return PromptClientSpec(
        request_name="prompt-request", response_name="prompt-response", **kwargs,
    )


def config_spec(**kwargs):
    return ConfigClientSpec(
        request_name="config-request", response_name="config-response", **kwargs,
    )


class TestResolveTimeout:

    def test_generic_default_matches_previous_wrapper_literal(self):
        assert generic_spec().resolve_timeout(make_processor()) == 300

    def test_base_spec_ignores_processor_attributes(self):
        proc = make_processor(prompt_timeout=45, librarian_timeout=30)
        assert generic_spec().resolve_timeout(proc) == 300

    @pytest.mark.parametrize("make, attr, default", [
        (prompt_spec, "prompt_timeout", 600),
        (config_spec, "config_timeout", 60),
        (LibrarianSpec, "librarian_timeout", 120),
    ])
    def test_class_default_then_processor_then_explicit(self, make, attr, default):
        assert make().resolve_timeout(make_processor()) == default
        assert make().resolve_timeout(make_processor(**{attr: 45})) == 45
        assert make(timeout=9).resolve_timeout(make_processor(**{attr: 45})) == 9

    @pytest.mark.asyncio
    @pytest.mark.parametrize("make, attrs, target, expected", [
        (lambda: generic_spec(timeout=42), {}, RR_CREATE, 42),
        (prompt_spec, {"prompt_timeout": 45}, RR_CREATE, 45),
        (LibrarianSpec, {"librarian_timeout": 30}, LIB_CREATE, 30),
    ])
    async def test_register_threads_timeout_into_client(
            self, make, attrs, target, expected):
        create = AsyncMock(return_value=MagicMock())
        with patch(target, new=create):
            await make().register(make_flow(), make_processor(**attrs), TOPICS)
        assert create.call_args.kwargs["default_timeout"] == expected


class TestImplWrapperTimeout:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kwargs, forwarded", [({}, None), ({"timeout": 7}, 7)])
    async def test_request_forwards_timeout(self, kwargs, forwarded):
        rr = MagicMock()
        rr.request = AsyncMock(return_value="ok")
        wrapper = _make_impl_wrapper(rr, None)

        assert await wrapper.request("req", **kwargs) == "ok"
        assert rr.request.call_args.kwargs["timeout"] == forwarded


class TestRegisteredPromptWrapper:

    @pytest.mark.asyncio
    async def test_bare_request_reaches_client_with_prompt_default(self):
        # A real RequestResponseClient (no pub/sub), so the number that
        # reaches wait_for is the effective default, not a forwarded None.
        async def create(**kwargs):
            client = RequestResponseClient(
                default_timeout=kwargs["default_timeout"],
            )
            client.producer = AsyncMock()
            return client

        wait_for = AsyncMock(return_value="resp")
        with patch(RR_CREATE, new=create), patch(
            "trustgraph.base.request_response_client.asyncio.wait_for",
            new=wait_for,
        ):
            wrapper = await prompt_spec().register(
                make_flow(), make_processor(), TOPICS,
            )
            assert await wrapper.request("req") == "resp"

        assert wait_for.call_args.kwargs["timeout"] == 600


class TestPromptClientMethods:

    def client(self):
        client = PromptClient.__new__(PromptClient)
        client.request = AsyncMock(
            return_value=PromptResponse(text="x", object=None, error=None),
        )
        return client

    @pytest.mark.asyncio
    async def test_methods_forward_none_by_default(self):
        client = self.client()
        await client.question("q")
        assert client.request.call_args.kwargs["timeout"] is None

        await client.extract_definitions("t")
        assert client.request.call_args.kwargs["timeout"] is None

    @pytest.mark.asyncio
    async def test_methods_forward_explicit_timeout(self):
        client = self.client()
        await client.question("q", timeout=5)
        assert client.request.call_args.kwargs["timeout"] == 5

        await client.extract_relationships("t", timeout=6)
        assert client.request.call_args.kwargs["timeout"] == 6


class TestAsyncLibrarianClientTimeout:

    def client(self, response, **kwargs):
        # The producer answers its own request so the real wait_for completes.
        client = AsyncLibrarianClient(**kwargs)

        async def send(request, properties):
            request_id = properties["id"]
            if request_id in client._streams:
                await client._streams[request_id].put(response)
            else:
                client._pending[request_id].set_result(response)

        client._producer = MagicMock(send=AsyncMock(side_effect=send))
        return client

    def wait_for(self):
        return patch(
            "trustgraph.base.async_librarian_client.asyncio.wait_for",
            new=AsyncMock(side_effect=REAL_WAIT_FOR),
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("ctor, call, expected", [
        ({}, {}, 120),
        ({"default_timeout": 33}, {}, 33),
        ({"default_timeout": 33}, {"timeout": 5}, 5),
    ])
    async def test_request_resolves_timeout(self, ctor, call, expected):
        client = self.client(MagicMock(error=None), **ctor)
        with self.wait_for() as wait_for:
            await client.request(
                LibrarianRequest(operation="list-documents"), **call,
            )
        assert wait_for.call_args.kwargs["timeout"] == expected

    @pytest.mark.asyncio
    async def test_stream_uses_constructor_default(self):
        final = MagicMock(error=None, is_final=True)
        client = self.client(final, default_timeout=33)
        with self.wait_for() as wait_for:
            chunks = await client.stream(
                LibrarianRequest(operation="stream-document"),
            )
        assert chunks == [final]
        assert wait_for.call_args.kwargs["timeout"] == 33

    @pytest.mark.asyncio
    async def test_fetch_helpers_defer_to_default(self):
        response = MagicMock(error=None, document_metadata="meta")
        client = self.client(response, default_timeout=33)
        with self.wait_for() as wait_for:
            assert await client.fetch_document_metadata("d1") == "meta"
        assert wait_for.call_args.kwargs["timeout"] == 33

    @pytest.mark.asyncio
    async def test_create_threads_default_timeout(self):
        with patch(
            "trustgraph.base.async_librarian_client.asyncio.create_task",
            new=lambda coro, **kw: coro.close(),
        ):
            client = await AsyncLibrarianClient.create(
                backend=AsyncMock(), request_topic="r", response_topic="s",
                default_timeout=33,
            )
        assert client.default_timeout == 33


class TestTimeoutArgs:

    def test_flow_processor_add_args(self):
        from trustgraph.base.flow_processor import FlowProcessor

        parser = argparse.ArgumentParser()
        FlowProcessor.add_args(parser)

        args = parser.parse_args([])
        assert args.prompt_timeout == 600
        assert args.librarian_timeout == 120

        args = parser.parse_args(
            ["--prompt-timeout", "30", "--librarian-timeout", "15"],
        )
        assert args.prompt_timeout == 30
        assert args.librarian_timeout == 15

    def test_workspace_processor_has_neither_flag(self):
        from trustgraph.base.workspace_processor import WorkspaceProcessor

        parser = argparse.ArgumentParser()
        WorkspaceProcessor.add_args(parser)

        args = parser.parse_args([])
        assert not hasattr(args, "librarian_timeout")
        assert not hasattr(args, "prompt_timeout")

    def test_librarian_arg_is_opt_in_for_workspace_processors(self):
        from trustgraph.base.workspace_processor import WorkspaceProcessor

        parser = argparse.ArgumentParser()
        WorkspaceProcessor.add_args(parser)
        WorkspaceProcessor.add_librarian_args(parser)

        assert parser.parse_args([]).librarian_timeout == 120
        assert parser.parse_args(["--librarian-timeout", "15"]).librarian_timeout == 15

    def _flow_processor(self, **extra):
        with patch(
            "trustgraph.base.async_processor.get_async_pubsub"
        ) as pubsub:
            pubsub.return_value = MagicMock()
            from trustgraph.base.flow_processor import FlowProcessor
            return FlowProcessor(
                id="test-flow-processor", taskgroup=AsyncMock(), **extra,
            )

    def test_processor_attribute_defaults(self):
        p = self._flow_processor()
        assert p.prompt_timeout == 600
        assert p.librarian_timeout == 120

    def test_processor_attributes_from_params(self):
        p = self._flow_processor(prompt_timeout=30, librarian_timeout=15)
        assert p.prompt_timeout == 30
        assert p.librarian_timeout == 15
