"""
Unit tests for parsing agent and RAG instrumentation predicates (latency,
token usage, tool errors, termination reason) in the explainability API.
"""

from trustgraph.schema import IRI
from trustgraph.provenance import (
    agent_iteration_triples,
    agent_observation_triples,
    agent_final_triples,
    agent_decomposition_triples,
    agent_plan_triples,
    agent_step_result_triples,
    agent_synthesis_triples,
    grounding_triples,
    focus_triples,
    synthesis_triples,
)
from trustgraph.api.explainability import (
    ExplainEntity,
    Analysis,
    Observation,
    Conclusion,
    Synthesis,
    Decomposition,
    Plan,
    StepResult,
    Grounding,
    Focus,
    TG_ANALYSIS,
    TG_TOOL_USE,
    TG_OBSERVATION_TYPE,
    TG_CONCLUSION,
    TG_ERROR_TYPE,
    TG_STEP_NUMBER,
    TG_LLM_DURATION_MS,
    TG_TOOL_DURATION_MS,
    TG_TOOL_ERROR,
    TG_IN_TOKEN,
    TG_OUT_TOKEN,
    TG_LLM_MODEL,
    RDF_TYPE,
)


def _to_tuples(triples):
    """Convert schema Triples from the provenance builders to (s, p, o)."""
    def value(term):
        return term.iri if term.type == IRI else term.value
    return [(value(t.s), value(t.p), value(t.o)) for t in triples]


def _parse(uri, triples):
    return ExplainEntity.from_triples(uri, _to_tuples(triples))


class TestAgentRoundTrip:
    """Triples written by the provenance builders parse back unchanged."""

    def test_analysis_instrumentation(self):
        uri = "urn:trustgraph:agent:s1/i2"
        entity = _parse(uri, agent_iteration_triples(
            uri,
            previous_uri="urn:trustgraph:agent:s1/i1/observation",
            action="knowledge-query",
            arguments={"question": "test"},
            tool_candidates=["knowledge-query", "calculator"],
            step_number=2,
            llm_duration_ms=1234,
            in_token=900,
            out_token=85,
            model="test-model",
        ))

        assert isinstance(entity, Analysis)
        assert entity.action == "knowledge-query"
        assert entity.tool_candidates == ["knowledge-query", "calculator"]
        assert entity.step_number == 2
        assert entity.llm_duration_ms == 1234
        assert entity.in_token == 900
        assert entity.out_token == 85
        assert entity.model == "test-model"

    def test_observation_success(self):
        uri = "urn:trustgraph:agent:s1/i1/observation"
        entity = _parse(uri, agent_observation_triples(
            uri, "urn:trustgraph:agent:s1/i1", tool_duration_ms=250,
        ))

        assert isinstance(entity, Observation)
        assert entity.tool_duration_ms == 250
        assert entity.tool_error == ""
        assert entity.is_error is False

    def test_observation_tool_error(self):
        uri = "urn:trustgraph:agent:s1/i1/observation"
        entity = _parse(uri, agent_observation_triples(
            uri, "urn:trustgraph:agent:s1/i1",
            tool_duration_ms=5000, tool_error="Tool timed out",
        ))

        assert isinstance(entity, Observation)
        assert entity.tool_duration_ms == 5000
        assert entity.tool_error == "Tool timed out"
        assert entity.is_error is True

    def test_conclusion(self):
        uri = "urn:trustgraph:agent:s1/final"
        entity = _parse(uri, agent_final_triples(
            uri, previous_uri="urn:trustgraph:agent:s1/i2/observation",
            document_id="urn:doc:answer", termination_reason="final-answer",
            in_token=1500, out_token=300, model="test-model",
        ))

        assert isinstance(entity, Conclusion)
        assert entity.document == "urn:doc:answer"
        assert entity.termination_reason == "final-answer"
        assert entity.in_token == 1500
        assert entity.out_token == 300
        assert entity.model == "test-model"

    def test_agent_synthesis(self):
        uri = "urn:trustgraph:agent:s1/synthesis"
        entity = _parse(uri, agent_synthesis_triples(
            uri, ["urn:trustgraph:agent:s1/finding/0"],
            termination_reason="subagents-complete",
            in_token=2000, out_token=400, model="test-model",
        ))

        assert isinstance(entity, Synthesis)
        assert entity.termination_reason == "subagents-complete"
        assert entity.in_token == 2000
        assert entity.out_token == 400

    def test_decomposition_plan_and_step_result_tokens(self):
        decomposition = _parse("urn:d", agent_decomposition_triples(
            "urn:d", "urn:s", ["goal"], in_token=10, out_token=20, model="m",
        ))
        plan = _parse("urn:p", agent_plan_triples(
            "urn:p", "urn:s", ["step"], in_token=30, out_token=40, model="m",
        ))
        step_result = _parse("urn:r", agent_step_result_triples(
            "urn:r", "urn:p", "step", in_token=50, out_token=60, model="m",
        ))

        assert isinstance(decomposition, Decomposition)
        assert (decomposition.in_token, decomposition.out_token) == (10, 20)
        assert isinstance(plan, Plan)
        assert (plan.in_token, plan.out_token) == (30, 40)
        assert isinstance(step_result, StepResult)
        assert (step_result.in_token, step_result.out_token) == (50, 60)
        assert step_result.model == "m"


class TestRagRoundTrip:

    def test_grounding_tokens(self):
        entity = _parse("urn:g", grounding_triples(
            "urn:g", "urn:q", ["concept"], in_token=11, out_token=22, model="m",
        ))

        assert isinstance(entity, Grounding)
        assert entity.concepts == ["concept"]
        assert (entity.in_token, entity.out_token, entity.model) == (11, 22, "m")

    def test_focus_tokens(self):
        entity = _parse("urn:f", focus_triples(
            "urn:f", "urn:e", [], "session-1",
            in_token=33, out_token=44, model="m",
        ))

        assert isinstance(entity, Focus)
        assert (entity.in_token, entity.out_token, entity.model) == (33, 44, "m")

    def test_synthesis_tokens(self):
        entity = _parse("urn:s", synthesis_triples(
            "urn:s", "urn:f", document_id="urn:doc",
            in_token=55, out_token=66, model="m",
        ))

        assert isinstance(entity, Synthesis)
        assert entity.document == "urn:doc"
        assert (entity.in_token, entity.out_token, entity.model) == (55, 66, "m")
        assert entity.termination_reason == ""


class TestMissingAndMalformedValues:

    def test_analysis_without_instrumentation(self):
        triples = [
            ("urn:a", RDF_TYPE, TG_ANALYSIS),
            ("urn:a", RDF_TYPE, TG_TOOL_USE),
        ]
        entity = ExplainEntity.from_triples("urn:a", triples)

        assert isinstance(entity, Analysis)
        assert entity.tool_candidates == []
        assert entity.step_number is None
        assert entity.llm_duration_ms is None
        assert entity.in_token is None
        assert entity.out_token is None
        assert entity.model is None

    def test_malformed_integers_are_ignored(self):
        triples = [
            ("urn:a", RDF_TYPE, TG_ANALYSIS),
            ("urn:a", TG_STEP_NUMBER, "first"),
            ("urn:a", TG_LLM_DURATION_MS, ""),
            ("urn:a", TG_IN_TOKEN, "n/a"),
            ("urn:a", TG_OUT_TOKEN, "12"),
            ("urn:a", TG_LLM_MODEL, "m"),
        ]
        entity = ExplainEntity.from_triples("urn:a", triples)

        assert entity.step_number is None
        assert entity.llm_duration_ms is None
        assert entity.in_token is None
        assert entity.out_token == 12
        assert entity.model == "m"

    def test_malformed_tool_duration_is_ignored(self):
        triples = [
            ("urn:o", RDF_TYPE, TG_OBSERVATION_TYPE),
            ("urn:o", TG_TOOL_DURATION_MS, "slow"),
        ]
        entity = ExplainEntity.from_triples("urn:o", triples)

        assert isinstance(entity, Observation)
        assert entity.tool_duration_ms is None

    def test_error_type_without_message(self):
        triples = [
            ("urn:o", RDF_TYPE, TG_OBSERVATION_TYPE),
            ("urn:o", RDF_TYPE, TG_ERROR_TYPE),
        ]
        entity = ExplainEntity.from_triples("urn:o", triples)

        assert isinstance(entity, Observation)
        assert entity.is_error is True
        assert entity.tool_error == ""

    def test_tool_error_without_error_type(self):
        triples = [
            ("urn:o", RDF_TYPE, TG_OBSERVATION_TYPE),
            ("urn:o", TG_TOOL_ERROR, "parse error"),
        ]
        entity = ExplainEntity.from_triples("urn:o", triples)

        assert entity.is_error is True
        assert entity.tool_error == "parse error"

    def test_conclusion_without_termination_reason(self):
        triples = [("urn:c", RDF_TYPE, TG_CONCLUSION)]
        entity = ExplainEntity.from_triples("urn:c", triples)

        assert isinstance(entity, Conclusion)
        assert entity.termination_reason == ""
        assert entity.in_token is None
