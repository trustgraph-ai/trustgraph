"""
Tests for RequestResponseSpec's optional flag: an optional client spec
binds only when the flow definition declares its topics, so a definition
predating the topics skips the binding (flow(name) then returns None)
instead of raising KeyError during Flow construction — which would wedge
the processor's start-flow retry loop.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.base.request_response_spec import RequestResponseSpec


class StubImpl:
    """Captures constructor kwargs; stands in for a client mixin."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def make_spec(optional):
    return RequestResponseSpec(
        request_name="keyword-index-request",
        request_schema=object,
        response_name="keyword-index-response",
        response_schema=object,
        impl=StubImpl,
        optional=optional,
    )


def make_flow():
    flow = MagicMock()
    flow.id = "f-id"
    flow.name = "f-name"
    flow.workspace = "ws"
    flow.consumer = {}
    return flow


def make_processor():
    p = MagicMock()
    p.async_backend = AsyncMock()
    p.id = "proc1"
    return p


FULL_TOPICS = {
    "topics": {
        "keyword-index-request": "request:tg:keyword-index:ws:f",
        "keyword-index-response": "response:tg:keyword-index:ws:f",
    }
}


class TestOptionalRequestResponseSpec:

    @pytest.mark.asyncio
    async def test_optional_spec_skips_binding_when_topics_absent(self):
        flow = make_flow()
        result = await make_spec(optional=True).register(
            flow, make_processor(), {"topics": {}},
        )
        assert flow.consumer == {}
        assert result is None

    @pytest.mark.asyncio
    async def test_optional_spec_skips_when_only_one_topic_present(self):
        flow = make_flow()
        definition = {
            "topics": {
                "keyword-index-request": "request:tg:keyword-index:ws:f",
            }
        }
        result = await make_spec(optional=True).register(
            flow, make_processor(), definition,
        )
        assert flow.consumer == {}
        assert result is None

    @pytest.mark.asyncio
    async def test_optional_spec_binds_when_topics_present(self):
        flow = make_flow()
        with patch(
            "trustgraph.base.request_response_client.RequestResponseClient"
        ) as mock_rrc:
            mock_rrc.create = AsyncMock(return_value=AsyncMock())
            await make_spec(optional=True).register(
                flow, make_processor(), FULL_TOPICS,
            )
        assert "keyword-index-request" in flow.consumer

    @pytest.mark.asyncio
    async def test_default_spec_still_requires_topics(self):
        with pytest.raises(KeyError):
            await make_spec(optional=False).register(
                make_flow(), make_processor(), {"topics": {}},
            )
