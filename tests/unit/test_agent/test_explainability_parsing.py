"""
Unit tests for explainability API parsing — verifies that from_triples()
correctly dispatches and parses the new orchestrator entity types.
"""

import pytest

from trustgraph.api.explainability import (
    ExplainEntity,
    Decomposition,
    Finding,
    Plan,
    StepResult,
    Synthesis,
    Analysis,
    Observation,
    Conclusion,
    TG_DECOMPOSITION,
    TG_FINDING,
    TG_PLAN_TYPE,
    TG_STEP_RESULT,
    TG_SYNTHESIS,
    TG_ANSWER_TYPE,
    TG_OBSERVATION_TYPE,
    TG_TOOL_USE,
    TG_ANALYSIS,
    TG_CONCLUSION,
    TG_DOCUMENT,
    TG_SUBAGENT_GOAL,
    TG_PLAN_STEP,
    RDF_TYPE,
)

PROV_ENTITY = "http://www.w3.org/ns/prov#Entity"


def _make_triples(uri, types, extras=None):
    """Build a list of (s, p, o) tuples for testing."""
    triples = [(uri, RDF_TYPE, t) for t in types]
    if extras:
        triples.extend((uri, p, o) for p, o in extras)
    return triples


class TestFromTriplesDispatch:

    def test_dispatches_decomposition(self):
        triples = _make_triples("urn:d", [PROV_ENTITY, TG_DECOMPOSITION])
        entity = ExplainEntity.from_triples("urn:d", triples)
        assert isinstance(entity, Decomposition)

    def test_dispatches_finding(self):
        triples = _make_triples("urn:f",
                                [PROV_ENTITY, TG_FINDING, TG_ANSWER_TYPE])
        entity = ExplainEntity.from_triples("urn:f", triples)
        assert isinstance(entity, Finding)

    def test_dispatches_plan(self):
        triples = _make_triples("urn:p", [PROV_ENTITY, TG_PLAN_TYPE])
        entity = ExplainEntity.from_triples("urn:p", triples)
        assert isinstance(entity, Plan)

    def test_dispatches_step_result(self):
        triples = _make_triples("urn:sr",
                                [PROV_ENTITY, TG_STEP_RESULT, TG_ANSWER_TYPE])
        entity = ExplainEntity.from_triples("urn:sr", triples)
        assert isinstance(entity, StepResult)

    def test_dispatches_synthesis(self):
        triples = _make_triples("urn:s",
                                [PROV_ENTITY, TG_SYNTHESIS, TG_ANSWER_TYPE])
        entity = ExplainEntity.from_triples("urn:s", triples)
        assert isinstance(entity, Synthesis)

    def test_dispatches_analysis_unchanged(self):
        triples = _make_triples("urn:a", [PROV_ENTITY, TG_ANALYSIS])
        entity = ExplainEntity.from_triples("urn:a", triples)
        assert isinstance(entity, Analysis)

    def test_dispatches_analysis_with_tooluse(self):
        """Analysis+ToolUse mixin still dispatches to Analysis."""
        triples = _make_triples("urn:a",
                                [PROV_ENTITY, TG_ANALYSIS, TG_TOOL_USE])
        entity = ExplainEntity.from_triples("urn:a", triples)
        assert isinstance(entity, Analysis)

    def test_dispatches_observation(self):
        triples = _make_triples("urn:o", [PROV_ENTITY, TG_OBSERVATION_TYPE])
        entity = ExplainEntity.from_triples("urn:o", triples)
        assert isinstance(entity, Observation)

    def test_dispatches_conclusion_unchanged(self):
        triples = _make_triples("urn:c",
                                [PROV_ENTITY, TG_CONCLUSION, TG_ANSWER_TYPE])
        entity = ExplainEntity.from_triples("urn:c", triples)
        assert isinstance(entity, Conclusion)

    def test_finding_takes_precedence_over_synthesis(self):
        """Finding has Answer mixin but should dispatch to Finding, not
        Synthesis, because Finding is checked first."""
        triples = _make_triples("urn:f",
                                [PROV_ENTITY, TG_FINDING, TG_ANSWER_TYPE])
        entity = ExplainEntity.from_triples("urn:f", triples)
        assert isinstance(entity, Finding)
        assert not isinstance(entity, Synthesis)


class TestDecompositionParsing:

    def test_parses_goals(self):
        triples = _make_triples("urn:d", [TG_DECOMPOSITION], [
            (TG_SUBAGENT_GOAL, "What is X?"),
            (TG_SUBAGENT_GOAL, "What is Y?"),
        ])
        entity = Decomposition.from_triples("urn:d", triples)
        assert set(entity.goals) == {"What is X?", "What is Y?"}

    def test_entity_type_field(self):
        triples = _make_triples("urn:d", [TG_DECOMPOSITION])
        entity = Decomposition.from_triples("urn:d", triples)
        assert entity.entity_type == "decomposition"

    def test_empty_goals(self):
        triples = _make_triples("urn:d", [TG_DECOMPOSITION])
        entity = Decomposition.from_triples("urn:d", triples)
        assert entity.goals == []


class TestFindingParsing:

    def test_parses_goal_and_document(self):
        triples = _make_triples("urn:f", [TG_FINDING, TG_ANSWER_TYPE], [
            (TG_SUBAGENT_GOAL, "What is X?"),
            (TG_DOCUMENT, "urn:doc/finding"),
        ])
        entity = Finding.from_triples("urn:f", triples)
        assert entity.goal == "What is X?"
        assert entity.document == "urn:doc/finding"

    def test_entity_type_field(self):
        triples = _make_triples("urn:f", [TG_FINDING])
        entity = Finding.from_triples("urn:f", triples)
        assert entity.entity_type == "finding"


class TestPlanParsing:

    def test_parses_steps(self):
        triples = _make_triples("urn:p", [TG_PLAN_TYPE], [
            (TG_PLAN_STEP, "Define X"),
            (TG_PLAN_STEP, "Research Y"),
            (TG_PLAN_STEP, "Analyse Z"),
        ])
        entity = Plan.from_triples("urn:p", triples)
        assert set(entity.steps) == {"Define X", "Research Y", "Analyse Z"}

    def test_entity_type_field(self):
        triples = _make_triples("urn:p", [TG_PLAN_TYPE])
        entity = Plan.from_triples("urn:p", triples)
        assert entity.entity_type == "plan"


class TestStepResultParsing:

    def test_parses_step_and_document(self):
        triples = _make_triples("urn:sr", [TG_STEP_RESULT, TG_ANSWER_TYPE], [
            (TG_PLAN_STEP, "Define X"),
            (TG_DOCUMENT, "urn:doc/step"),
        ])
        entity = StepResult.from_triples("urn:sr", triples)
        assert entity.step == "Define X"
        assert entity.document == "urn:doc/step"

    def test_entity_type_field(self):
        triples = _make_triples("urn:sr", [TG_STEP_RESULT])
        entity = StepResult.from_triples("urn:sr", triples)
        assert entity.entity_type == "step-result"
