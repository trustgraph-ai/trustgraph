"""
Unit tests for PatternBase subagent helpers — is_subagent() and
emit_subagent_completion().
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass

from trustgraph.schema import AgentRequest

from trustgraph.agent.orchestrator.pattern_base import PatternBase


@dataclass
class MockProcessor:
    """Minimal processor mock for PatternBase."""
    pass


def _make_request(**kwargs):
    defaults = dict(
        question="Test question",
        user="testuser",
        collection="default",
    )
    defaults.update(kwargs)
    return AgentRequest(**defaults)


def _make_pattern():
    return PatternBase(MockProcessor())


class TestIsSubagent:

    def test_returns_true_when_correlation_id_set(self):
        pattern = _make_pattern()
        request = _make_request(correlation_id="corr-123")
        assert pattern.is_subagent(request) is True

    def test_returns_false_when_correlation_id_empty(self):
        pattern = _make_pattern()
        request = _make_request(correlation_id="")
        assert pattern.is_subagent(request) is False

    def test_returns_false_when_correlation_id_missing(self):
        pattern = _make_pattern()
        request = _make_request()
        assert pattern.is_subagent(request) is False


class TestEmitSubagentCompletion:

    @pytest.mark.asyncio
    async def test_calls_next_with_completion_request(self):
        pattern = _make_pattern()
        request = _make_request(
            correlation_id="corr-123",
            parent_session_id="parent-sess",
            subagent_goal="What is X?",
            expected_siblings=4,
        )
        next_fn = AsyncMock()

        await pattern.emit_subagent_completion(
            request, next_fn, "The answer is Y",
        )

        next_fn.assert_called_once()
        completion_req = next_fn.call_args[0][0]
        assert isinstance(completion_req, AgentRequest)

    @pytest.mark.asyncio
    async def test_completion_has_correct_step_type(self):
        pattern = _make_pattern()
        request = _make_request(
            correlation_id="corr-123",
            subagent_goal="What is X?",
        )
        next_fn = AsyncMock()

        await pattern.emit_subagent_completion(
            request, next_fn, "answer text",
        )

        completion_req = next_fn.call_args[0][0]
        assert len(completion_req.history) == 1
        step = completion_req.history[0]
        assert step.step_type == "subagent-completion"

    @pytest.mark.asyncio
    async def test_completion_carries_answer_in_observation(self):
        pattern = _make_pattern()
        request = _make_request(
            correlation_id="corr-123",
            subagent_goal="What is X?",
        )
        next_fn = AsyncMock()

        await pattern.emit_subagent_completion(
            request, next_fn, "The answer is Y",
        )

        completion_req = next_fn.call_args[0][0]
        step = completion_req.history[0]
        assert step.observation == "The answer is Y"

    @pytest.mark.asyncio
    async def test_completion_preserves_correlation_fields(self):
        pattern = _make_pattern()
        request = _make_request(
            correlation_id="corr-123",
            parent_session_id="parent-sess",
            subagent_goal="What is X?",
            expected_siblings=4,
        )
        next_fn = AsyncMock()

        await pattern.emit_subagent_completion(
            request, next_fn, "answer",
        )

        completion_req = next_fn.call_args[0][0]
        assert completion_req.correlation_id == "corr-123"
        assert completion_req.parent_session_id == "parent-sess"
        assert completion_req.subagent_goal == "What is X?"
        assert completion_req.expected_siblings == 4

    @pytest.mark.asyncio
    async def test_completion_has_empty_pattern(self):
        pattern = _make_pattern()
        request = _make_request(
            correlation_id="corr-123",
            subagent_goal="goal",
        )
        next_fn = AsyncMock()

        await pattern.emit_subagent_completion(
            request, next_fn, "answer",
        )

        completion_req = next_fn.call_args[0][0]
        assert completion_req.pattern == ""
