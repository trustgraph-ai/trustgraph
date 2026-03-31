"""
Unit tests for the Aggregator — tracks fan-out correlations and triggers
synthesis when all subagents complete.
"""

import time
import pytest

from trustgraph.schema import AgentRequest, AgentStep

from trustgraph.agent.orchestrator.aggregator import Aggregator


def _make_request(question="Test question", user="testuser",
                  collection="default", streaming=False,
                  session_id="parent-session", task_type="research",
                  framing="test framing", conversation_id="conv-1"):
    return AgentRequest(
        question=question,
        user=user,
        collection=collection,
        streaming=streaming,
        session_id=session_id,
        task_type=task_type,
        framing=framing,
        conversation_id=conversation_id,
    )


class TestRegisterFanout:

    def test_stores_correlation_entry(self):
        agg = Aggregator()
        agg.register_fanout("corr-1", "parent-1", 3)

        assert "corr-1" in agg.correlations
        entry = agg.correlations["corr-1"]
        assert entry["parent_session_id"] == "parent-1"
        assert entry["expected"] == 3
        assert entry["results"] == {}

    def test_stores_request_template(self):
        agg = Aggregator()
        template = _make_request()
        agg.register_fanout("corr-1", "parent-1", 2,
                            request_template=template)

        entry = agg.correlations["corr-1"]
        assert entry["request_template"] is template

    def test_records_creation_time(self):
        agg = Aggregator()
        before = time.time()
        agg.register_fanout("corr-1", "parent-1", 2)
        after = time.time()

        created = agg.correlations["corr-1"]["created_at"]
        assert before <= created <= after


class TestRecordCompletion:

    def test_returns_false_until_all_done(self):
        agg = Aggregator()
        agg.register_fanout("corr-1", "parent-1", 3)

        assert agg.record_completion("corr-1", "goal-a", "answer-a") is False
        assert agg.record_completion("corr-1", "goal-b", "answer-b") is False
        assert agg.record_completion("corr-1", "goal-c", "answer-c") is True

    def test_returns_none_for_unknown_correlation(self):
        agg = Aggregator()
        result = agg.record_completion("unknown", "goal", "answer")
        assert result is None

    def test_stores_results_by_goal(self):
        agg = Aggregator()
        agg.register_fanout("corr-1", "parent-1", 2)

        agg.record_completion("corr-1", "goal-a", "answer-a")
        agg.record_completion("corr-1", "goal-b", "answer-b")

        results = agg.correlations["corr-1"]["results"]
        assert results["goal-a"] == "answer-a"
        assert results["goal-b"] == "answer-b"

    def test_single_subagent(self):
        agg = Aggregator()
        agg.register_fanout("corr-1", "parent-1", 1)

        assert agg.record_completion("corr-1", "goal-a", "answer") is True


class TestGetOriginalRequest:

    def test_peeks_without_consuming(self):
        agg = Aggregator()
        template = _make_request()
        agg.register_fanout("corr-1", "parent-1", 2,
                            request_template=template)

        result = agg.get_original_request("corr-1")
        assert result is template
        # Entry still exists
        assert "corr-1" in agg.correlations

    def test_returns_none_for_unknown(self):
        agg = Aggregator()
        assert agg.get_original_request("unknown") is None


class TestBuildSynthesisRequest:

    def test_builds_correct_request(self):
        agg = Aggregator()
        template = _make_request(
            question="Original question",
            streaming=True,
            task_type="risk-assessment",
            framing="Assess risks",
        )
        agg.register_fanout("corr-1", "parent-1", 2,
                            request_template=template)
        agg.record_completion("corr-1", "goal-a", "answer-a")
        agg.record_completion("corr-1", "goal-b", "answer-b")

        req = agg.build_synthesis_request(
            "corr-1",
            original_question="Original question",
            user="testuser",
            collection="default",
        )

        assert req.question == "Original question"
        assert req.pattern == "supervisor"
        assert req.session_id == "parent-1"
        assert req.correlation_id == ""  # Must be empty
        assert req.streaming == True
        assert req.task_type == "risk-assessment"
        assert req.framing == "Assess risks"

    def test_synthesis_step_in_history(self):
        agg = Aggregator()
        template = _make_request()
        agg.register_fanout("corr-1", "parent-1", 2,
                            request_template=template)
        agg.record_completion("corr-1", "goal-a", "answer-a")
        agg.record_completion("corr-1", "goal-b", "answer-b")

        req = agg.build_synthesis_request(
            "corr-1", "question", "user", "default",
        )

        # Last history step should be the synthesis step
        assert len(req.history) >= 1
        synth_step = req.history[-1]
        assert synth_step.step_type == "synthesise"
        assert synth_step.subagent_results == {
            "goal-a": "answer-a",
            "goal-b": "answer-b",
        }

    def test_consumes_correlation_entry(self):
        agg = Aggregator()
        template = _make_request()
        agg.register_fanout("corr-1", "parent-1", 1,
                            request_template=template)
        agg.record_completion("corr-1", "goal-a", "answer-a")

        agg.build_synthesis_request(
            "corr-1", "question", "user", "default",
        )

        # Entry should be removed
        assert "corr-1" not in agg.correlations

    def test_raises_for_unknown_correlation(self):
        agg = Aggregator()
        with pytest.raises(RuntimeError, match="No results"):
            agg.build_synthesis_request(
                "unknown", "question", "user", "default",
            )


class TestCleanupStale:

    def test_removes_entries_older_than_timeout(self):
        agg = Aggregator(timeout=1)
        agg.register_fanout("corr-1", "parent-1", 2)

        # Backdate the creation time
        agg.correlations["corr-1"]["created_at"] = time.time() - 2

        stale = agg.cleanup_stale()
        assert "corr-1" in stale
        assert "corr-1" not in agg.correlations

    def test_keeps_recent_entries(self):
        agg = Aggregator(timeout=300)
        agg.register_fanout("corr-1", "parent-1", 2)

        stale = agg.cleanup_stale()
        assert stale == []
        assert "corr-1" in agg.correlations

    def test_mixed_stale_and_fresh(self):
        agg = Aggregator(timeout=1)
        agg.register_fanout("stale", "parent-1", 2)
        agg.register_fanout("fresh", "parent-2", 2)

        agg.correlations["stale"]["created_at"] = time.time() - 2

        stale = agg.cleanup_stale()
        assert "stale" in stale
        assert "stale" not in agg.correlations
        assert "fresh" in agg.correlations
