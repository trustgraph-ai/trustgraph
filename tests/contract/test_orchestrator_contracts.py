"""
Contract tests for orchestrator message schemas.

Verifies that AgentRequest/AgentStep with orchestration fields
serialise and deserialise correctly through the Pulsar schema layer.
"""

import pytest
import json

from trustgraph.schema import AgentRequest, AgentStep, PlanStep


@pytest.mark.contract
class TestOrchestrationFieldContracts:
    """Contract tests for orchestration fields on AgentRequest."""

    def test_agent_request_orchestration_fields_roundtrip(self):
        req = AgentRequest(
            question="Test question",
            user="testuser",
            collection="default",
            correlation_id="corr-123",
            parent_session_id="parent-sess",
            subagent_goal="What is X?",
            expected_siblings=4,
            pattern="react",
            task_type="research",
            framing="Focus on accuracy",
            conversation_id="conv-456",
        )

        assert req.correlation_id == "corr-123"
        assert req.parent_session_id == "parent-sess"
        assert req.subagent_goal == "What is X?"
        assert req.expected_siblings == 4
        assert req.pattern == "react"
        assert req.task_type == "research"
        assert req.framing == "Focus on accuracy"
        assert req.conversation_id == "conv-456"

    def test_agent_request_orchestration_fields_default_empty(self):
        req = AgentRequest(
            question="Test question",
            user="testuser",
        )

        assert req.correlation_id == ""
        assert req.parent_session_id == ""
        assert req.subagent_goal == ""
        assert req.expected_siblings == 0
        assert req.pattern == ""
        assert req.task_type == ""
        assert req.framing == ""


@pytest.mark.contract
class TestSubagentCompletionStepContract:
    """Contract tests for subagent-completion step type."""

    def test_subagent_completion_step_fields(self):
        step = AgentStep(
            thought="Subagent completed",
            action="complete",
            arguments={},
            observation="The answer text",
            step_type="subagent-completion",
        )

        assert step.step_type == "subagent-completion"
        assert step.observation == "The answer text"
        assert step.thought == "Subagent completed"
        assert step.action == "complete"

    def test_subagent_completion_in_request_history(self):
        step = AgentStep(
            thought="Subagent completed",
            action="complete",
            arguments={},
            observation="answer",
            step_type="subagent-completion",
        )
        req = AgentRequest(
            question="goal",
            user="testuser",
            correlation_id="corr-123",
            history=[step],
        )

        assert len(req.history) == 1
        assert req.history[0].step_type == "subagent-completion"
        assert req.history[0].observation == "answer"


@pytest.mark.contract
class TestSynthesisStepContract:
    """Contract tests for synthesis step type with subagent_results."""

    def test_synthesis_step_with_results(self):
        results = {"goal-a": "answer-a", "goal-b": "answer-b"}
        step = AgentStep(
            thought="All subagents completed",
            action="aggregate",
            arguments={},
            observation=json.dumps(results),
            step_type="synthesise",
            subagent_results=results,
        )

        assert step.step_type == "synthesise"
        assert step.subagent_results == results
        assert json.loads(step.observation) == results

    def test_synthesis_request_matches_supervisor_expectations(self):
        """The synthesis request built by the aggregator must be
        recognisable by SupervisorPattern._synthesise()."""
        results = {"goal-a": "answer-a", "goal-b": "answer-b"}
        step = AgentStep(
            thought="All subagents completed",
            action="aggregate",
            arguments={},
            observation=json.dumps(results),
            step_type="synthesise",
            subagent_results=results,
        )

        req = AgentRequest(
            question="Original question",
            user="testuser",
            pattern="supervisor",
            correlation_id="",
            session_id="parent-sess",
            history=[step],
        )

        # SupervisorPattern checks for step_type='synthesise' with
        # subagent_results
        has_results = bool(
            req.history
            and any(
                getattr(h, 'step_type', '') == 'synthesise'
                and getattr(h, 'subagent_results', None)
                for h in req.history
            )
        )
        assert has_results

        # Pattern must be supervisor
        assert req.pattern == "supervisor"

        # Correlation ID must be empty (not re-intercepted)
        assert req.correlation_id == ""


@pytest.mark.contract
class TestPlanStepContract:
    """Contract tests for plan steps in history."""

    def test_plan_step_in_history(self):
        plan = [
            PlanStep(goal="Step 1", tool_hint="knowledge-query",
                     depends_on=[], status="completed", result="done"),
            PlanStep(goal="Step 2", tool_hint="",
                     depends_on=[0], status="pending", result=""),
        ]
        step = AgentStep(
            thought="Created plan",
            action="plan",
            step_type="plan",
            plan=plan,
        )

        assert step.step_type == "plan"
        assert len(step.plan) == 2
        assert step.plan[0].goal == "Step 1"
        assert step.plan[0].status == "completed"
        assert step.plan[1].depends_on == [0]
