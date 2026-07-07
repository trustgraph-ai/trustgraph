"""
Tests for RequestResponseSpec's optional flag: an optional client spec
binds only when the flow definition declares its topics, so a definition
predating the topics skips the binding (flow(name) then returns None)
instead of raising KeyError during Flow construction — which would wedge
the processor's start-flow retry loop.
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.base.request_response_spec import RequestResponseSpec


class StubImpl:
    """Captures constructor kwargs; stands in for RequestResponse."""

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


FULL_TOPICS = {
    "topics": {
        "keyword-index-request": "request:tg:keyword-index:ws:f",
        "keyword-index-response": "response:tg:keyword-index:ws:f",
    }
}


class TestOptionalRequestResponseSpec:

    def test_optional_spec_skips_binding_when_topics_absent(self):
        flow = make_flow()
        make_spec(optional=True).add(flow, MagicMock(), {"topics": {}})
        assert flow.consumer == {}

    def test_optional_spec_skips_when_only_one_topic_present(self):
        flow = make_flow()
        definition = {
            "topics": {
                "keyword-index-request": "request:tg:keyword-index:ws:f",
            }
        }
        make_spec(optional=True).add(flow, MagicMock(), definition)
        assert flow.consumer == {}

    def test_optional_spec_binds_when_topics_present(self):
        flow = make_flow()
        make_spec(optional=True).add(flow, MagicMock(), FULL_TOPICS)
        client = flow.consumer["keyword-index-request"]
        assert isinstance(client, StubImpl)
        assert client.kwargs["request_topic"] == \
            "request:tg:keyword-index:ws:f"

    def test_default_spec_still_requires_topics(self):
        # Non-optional specs keep the existing contract: a missing topic
        # is a definition error, surfaced immediately.
        with pytest.raises(KeyError):
            make_spec(optional=False).add(
                make_flow(), MagicMock(), {"topics": {}},
            )
