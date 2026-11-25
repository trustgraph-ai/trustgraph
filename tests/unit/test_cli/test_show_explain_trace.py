"""
Unit tests for tg-show-explain-trace output: agent and RAG instrumentation
(latency, token usage, tool errors, termination reason) in JSON and text.
"""

import json
from unittest.mock import MagicMock

from trustgraph.api import (
    Question,
    Grounding,
    Exploration,
    Focus,
    Synthesis,
    Analysis,
    Observation,
    Conclusion,
    PatternDecision,
)
from trustgraph.cli.show_explain_trace import (
    trace_to_dict,
    print_agent_text,
)


def _agent_trace():
    return {
        "question": Question(
            uri="urn:trustgraph:agent:s1",
            entity_type="question",
            query="What is the capital of France?",
            timestamp="2026-11-01T09:00:00Z",
            question_type="agent",
        ),
        "steps": [
            Analysis(
                uri="urn:trustgraph:agent:s1/i1",
                entity_type="analysis",
                action="knowledge-query",
                arguments='{"question": "capital of France"}',
                tool_candidates=["knowledge-query", "calculator"],
                step_number=1,
                llm_duration_ms=1234,
                in_token=900,
                out_token=85,
                model="test-model",
            ),
            Observation(
                uri="urn:trustgraph:agent:s1/i1/observation",
                entity_type="observation",
                tool_duration_ms=5000,
                tool_error="Tool timed out",
                is_error=True,
            ),
            Conclusion(
                uri="urn:trustgraph:agent:s1/final",
                entity_type="conclusion",
                document="urn:doc:answer",
                termination_reason="final-answer",
                in_token=1500,
                out_token=300,
                model="test-model",
            ),
        ],
    }


class TestAgentTraceJson:

    def test_analysis_includes_instrumentation(self):
        result = trace_to_dict(_agent_trace(), "agent")

        analysis = result["steps"][0]
        assert analysis["type"] == "analysis"
        assert analysis["step_number"] == 1
        assert analysis["tool_candidates"] == ["knowledge-query", "calculator"]
        assert analysis["llm_duration_ms"] == 1234
        assert analysis["in_token"] == 900
        assert analysis["out_token"] == 85
        assert analysis["model"] == "test-model"

    def test_observation_includes_duration_and_error(self):
        result = trace_to_dict(_agent_trace(), "agent")

        observation = result["steps"][1]
        assert observation["type"] == "observation"
        assert observation["tool_duration_ms"] == 5000
        assert observation["tool_error"] == "Tool timed out"
        assert observation["is_error"] is True

    def test_conclusion_includes_termination_and_tokens(self):
        result = trace_to_dict(_agent_trace(), "agent")

        conclusion = result["steps"][2]
        assert conclusion["termination_reason"] == "final-answer"
        assert conclusion["in_token"] == 1500
        assert conclusion["out_token"] == 300

    def test_unrecorded_values_are_null(self):
        trace = {
            "question": None,
            "steps": [
                Analysis(uri="urn:a", entity_type="analysis"),
                Observation(uri="urn:o", entity_type="observation"),
                Conclusion(uri="urn:c", entity_type="conclusion"),
            ],
        }

        analysis, observation, conclusion = trace_to_dict(trace, "agent")["steps"]

        assert analysis["step_number"] is None
        assert analysis["llm_duration_ms"] is None
        assert analysis["in_token"] is None
        assert observation["tool_duration_ms"] is None
        assert observation["tool_error"] is None
        assert observation["is_error"] is False
        assert conclusion["termination_reason"] is None

    def test_output_is_json_serializable(self):
        result = trace_to_dict(_agent_trace(), "agent")

        assert json.loads(json.dumps(result)) == result


class TestRagTraceJson:

    def test_graphrag_includes_tokens(self):
        trace = {
            "question": None,
            "exploration": Exploration(uri="urn:e", entity_type="exploration"),
            "focus": Focus(
                uri="urn:f", entity_type="focus",
                in_token=10, out_token=20, model="m",
            ),
            "synthesis": Synthesis(
                uri="urn:s", entity_type="synthesis",
                in_token=30, out_token=40, model="m",
            ),
        }

        result = trace_to_dict(trace, "graphrag")

        assert (result["focus"]["in_token"], result["focus"]["out_token"]) == (10, 20)
        assert result["synthesis"]["in_token"] == 30
        assert result["synthesis"]["model"] == "m"

    def test_docrag_includes_tokens(self):
        trace = {
            "question": None,
            "grounding": Grounding(
                uri="urn:g", entity_type="grounding", concepts=["c"],
                in_token=5, out_token=6, model="m",
            ),
            "exploration": None,
            "synthesis": Synthesis(uri="urn:s", entity_type="synthesis"),
        }

        result = trace_to_dict(trace, "docrag")

        assert result["grounding"]["in_token"] == 5
        assert result["grounding"]["out_token"] == 6
        assert result["synthesis"]["in_token"] is None


class TestAgentTraceText:

    def test_prints_instrumentation(self, capsys):
        print_agent_text(_agent_trace(), MagicMock(), api=None)

        output = capsys.readouterr().out
        assert "Step: 1" in output
        assert "LLM: 1234 ms, 900 in / 85 out tokens, test-model" in output
        assert "Duration: 5000 ms" in output
        assert "Error: Tool timed out" in output
        assert "Termination: final-answer" in output
        assert "LLM: 1500 in / 300 out tokens, test-model" in output

    def test_omits_unrecorded_values(self, capsys):
        trace = {
            "question": None,
            "steps": [
                Analysis(uri="urn:a", entity_type="analysis", action="calc"),
                Observation(uri="urn:o", entity_type="observation"),
            ],
        }

        print_agent_text(trace, MagicMock(), api=None)

        output = capsys.readouterr().out
        assert "Action: calc" in output
        assert "Step:" not in output
        assert "LLM:" not in output
        assert "Duration:" not in output
        assert "Error:" not in output


def _pattern_trace(task_type="general"):
    return {
        "question": None,
        "steps": [
            PatternDecision(
                uri="urn:trustgraph:agent:s1/pattern-decision",
                entity_type="pattern-decision",
                pattern="react",
                task_type=task_type,
            ),
            Analysis(uri="urn:trustgraph:agent:s1/i1", entity_type="analysis"),
        ],
    }


class TestPatternDecision:

    def test_json_includes_pattern_decision(self):
        steps = trace_to_dict(_pattern_trace(), "agent")["steps"]

        assert steps[0] == {
            "type": "pattern-decision",
            "id": "urn:trustgraph:agent:s1/pattern-decision",
            "pattern": "react",
            "task_type": "general",
        }
        assert steps[1]["type"] == "analysis"

    def test_json_missing_task_type_is_null(self):
        steps = trace_to_dict(_pattern_trace(task_type=""), "agent")["steps"]

        assert steps[0]["task_type"] is None

    def test_text_shows_pattern(self, capsys):
        print_agent_text(_pattern_trace(), MagicMock(), api=None)

        output = capsys.readouterr().out
        assert "--- Pattern Decision ---" in output
        assert "Pattern: react" in output
        assert "Task type: general" in output
        assert "--- Analysis ---" in output
