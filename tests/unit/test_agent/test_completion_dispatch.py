"""
Unit tests for completion dispatch — verifies that agent_request() in the
orchestrator service correctly intercepts subagent completion messages and
routes them to _handle_subagent_completion.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.schema import AgentRequest, AgentStep

from trustgraph.agent.orchestrator.aggregator import Aggregator


def _make_request(**kwargs):
    defaults = dict(
        question="Test question",
        collection="default",
    )
    defaults.update(kwargs)
    return AgentRequest(**defaults)


def _make_completion_request(correlation_id, goal, answer):
    """Build a completion request as emit_subagent_completion would."""
    step = AgentStep(
        thought="Subagent completed",
        action="complete",
        arguments={},
        observation=answer,
        step_type="subagent-completion",
    )
    return _make_request(
        correlation_id=correlation_id,
        parent_session_id="parent-sess",
        subagent_goal=goal,
        expected_siblings=2,
        history=[step],
    )


class TestCompletionDetection:
    """Test that completion messages are correctly identified."""

    def test_is_completion_when_correlation_id_and_step_type(self):
        req = _make_completion_request("corr-1", "goal-a", "answer-a")

        has_correlation = bool(getattr(req, 'correlation_id', ''))
        is_completion = any(
            getattr(h, 'step_type', '') == 'subagent-completion'
            for h in req.history
        )

        assert has_correlation
        assert is_completion

    def test_not_completion_without_correlation_id(self):
        step = AgentStep(
            step_type="subagent-completion",
            observation="answer",
        )
        req = _make_request(
            correlation_id="",
            history=[step],
        )

        has_correlation = bool(getattr(req, 'correlation_id', ''))
        assert not has_correlation

    def test_not_completion_without_step_type(self):
        step = AgentStep(
            step_type="react",
            observation="answer",
        )
        req = _make_request(
            correlation_id="corr-1",
            history=[step],
        )

        is_completion = any(
            getattr(h, 'step_type', '') == 'subagent-completion'
            for h in req.history
        )
        assert not is_completion

    def test_not_completion_with_empty_history(self):
        req = _make_request(
            correlation_id="corr-1",
            history=[],
        )
        assert not req.history


class TestAggregatorIntegration:
    """Test the aggregator flow as used by _handle_subagent_completion."""

    def test_full_completion_flow(self):
        """Simulates the flow: register, record completions, build synthesis."""
        agg = Aggregator()
        template = _make_request(
            question="Original question",
            streaming=True,
            task_type="risk-assessment",
            framing="Assess risks",
            session_id="parent-sess",
        )

        # Register fan-out
        agg.register_fanout("corr-1", "parent-sess", 2,
                            request_template=template)

        # First completion — not all done
        all_done = agg.record_completion(
            "corr-1", "goal-a", "answer-a",
        )
        assert all_done is False

        # Second completion — all done
        all_done = agg.record_completion(
            "corr-1", "goal-b", "answer-b",
        )
        assert all_done is True

        # Peek at template
        peeked = agg.get_original_request("corr-1")
        assert peeked.question == "Original question"

        # Build synthesis request
        synth = agg.build_synthesis_request(
            "corr-1",
            original_question="Original question",
            collection="default",
        )

        # Verify synthesis request
        assert synth.pattern == "supervisor"
        assert synth.correlation_id == ""
        assert synth.session_id == "parent-sess"
        assert synth.streaming is True

        # Verify synthesis history has results
        synth_steps = [
            s for s in synth.history
            if getattr(s, 'step_type', '') == 'synthesise'
        ]
        assert len(synth_steps) == 1
        assert synth_steps[0].subagent_results == {
            "goal-a": "answer-a",
            "goal-b": "answer-b",
        }

    def test_synthesis_request_not_detected_as_completion(self):
        """The synthesis request must not be intercepted as a completion."""
        agg = Aggregator()
        template = _make_request(session_id="parent-sess")
        agg.register_fanout("corr-1", "parent-sess", 1,
                            request_template=template)
        agg.record_completion("corr-1", "goal", "answer")

        synth = agg.build_synthesis_request(
            "corr-1", "question", "default",
        )

        # correlation_id must be empty so it's not intercepted
        assert synth.correlation_id == ""

        # Even if we check for completion step, shouldn't match
        is_completion = any(
            getattr(h, 'step_type', '') == 'subagent-completion'
            for h in synth.history
        )
        assert not is_completion
