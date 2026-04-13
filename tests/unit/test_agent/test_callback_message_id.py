"""
Tests that streaming callbacks set message_id on AgentResponse.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.agent.orchestrator.pattern_base import PatternBase
from trustgraph.schema import AgentResponse


@pytest.fixture
def pattern():
    processor = MagicMock()
    return PatternBase(processor)


class TestThinkCallbackMessageId:

    @pytest.mark.asyncio
    async def test_streaming_think_has_message_id(self, pattern):
        responses = []
        async def capture(r):
            responses.append(r)

        msg_id = "urn:trustgraph:agent:sess/i1/thought"
        think = pattern.make_think_callback(capture, streaming=True, message_id=msg_id)
        await think("hello", is_final=False)

        assert len(responses) == 1
        assert responses[0].message_id == msg_id
        assert responses[0].message_type == "thought"

    @pytest.mark.asyncio
    async def test_non_streaming_think_has_message_id(self, pattern):
        responses = []
        async def capture(r):
            responses.append(r)

        msg_id = "urn:trustgraph:agent:sess/i1/thought"
        think = pattern.make_think_callback(capture, streaming=False, message_id=msg_id)
        await think("hello")

        assert responses[0].message_id == msg_id
        assert responses[0].end_of_message is True


class TestObserveCallbackMessageId:

    @pytest.mark.asyncio
    async def test_streaming_observe_has_message_id(self, pattern):
        responses = []
        async def capture(r):
            responses.append(r)

        msg_id = "urn:trustgraph:agent:sess/i1/observation"
        observe = pattern.make_observe_callback(capture, streaming=True, message_id=msg_id)
        await observe("result", is_final=True)

        assert responses[0].message_id == msg_id
        assert responses[0].message_type == "observation"


class TestAnswerCallbackMessageId:

    @pytest.mark.asyncio
    async def test_streaming_answer_has_message_id(self, pattern):
        responses = []
        async def capture(r):
            responses.append(r)

        msg_id = "urn:trustgraph:agent:sess/final"
        answer = pattern.make_answer_callback(capture, streaming=True, message_id=msg_id)
        await answer("the answer")

        assert responses[0].message_id == msg_id
        assert responses[0].message_type == "answer"

    @pytest.mark.asyncio
    async def test_no_message_id_default(self, pattern):
        responses = []
        async def capture(r):
            responses.append(r)

        answer = pattern.make_answer_callback(capture, streaming=True)
        await answer("the answer")

        assert responses[0].message_id == ""


class TestSendFinalResponseMessageId:

    @pytest.mark.asyncio
    async def test_streaming_final_has_message_id(self, pattern):
        responses = []
        async def capture(r):
            responses.append(r)

        msg_id = "urn:trustgraph:agent:sess/final"
        await pattern.send_final_response(
            capture, streaming=True, answer_text="answer",
            message_id=msg_id,
        )

        # Should get content chunk + end-of-dialog marker
        assert all(r.message_id == msg_id for r in responses)

    @pytest.mark.asyncio
    async def test_non_streaming_final_has_message_id(self, pattern):
        responses = []
        async def capture(r):
            responses.append(r)

        msg_id = "urn:trustgraph:agent:sess/final"
        await pattern.send_final_response(
            capture, streaming=False, answer_text="answer",
            message_id=msg_id,
        )

        assert len(responses) == 1
        assert responses[0].message_id == msg_id
        assert responses[0].end_of_dialog is True
