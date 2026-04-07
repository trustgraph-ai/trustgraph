"""
Unit tests for orchestrator provenance triple builders.
"""

import pytest

from trustgraph.provenance import (
    agent_decomposition_triples,
    agent_finding_triples,
    agent_plan_triples,
    agent_step_result_triples,
    agent_synthesis_triples,
)

from trustgraph.provenance.namespaces import (
    RDF_TYPE, RDFS_LABEL,
    PROV_ENTITY, PROV_WAS_DERIVED_FROM,
    TG_DECOMPOSITION, TG_FINDING, TG_PLAN_TYPE, TG_STEP_RESULT,
    TG_SYNTHESIS, TG_ANSWER_TYPE, TG_DOCUMENT,
    TG_SUBAGENT_GOAL, TG_PLAN_STEP,
)


def _triple_set(triples):
    """Convert triples to a set of (s_iri, p_iri, o_value) for easy assertion."""
    result = set()
    for t in triples:
        s = t.s.iri
        p = t.p.iri
        o = t.o.iri if t.o.iri else t.o.value
        result.add((s, p, o))
    return result


def _has_type(triples, uri, rdf_type):
    """Check if a URI has a given rdf:type in the triples."""
    return (uri, RDF_TYPE, rdf_type) in _triple_set(triples)


def _get_values(triples, uri, predicate):
    """Get all object values for a given subject + predicate."""
    ts = _triple_set(triples)
    return [o for s, p, o in ts if s == uri and p == predicate]


class TestDecompositionTriples:

    def test_has_correct_types(self):
        triples = agent_decomposition_triples(
            "urn:decompose", "urn:session", ["goal-a", "goal-b"],
        )
        assert _has_type(triples, "urn:decompose", PROV_ENTITY)
        assert _has_type(triples, "urn:decompose", TG_DECOMPOSITION)

    def test_not_answer_type(self):
        triples = agent_decomposition_triples(
            "urn:decompose", "urn:session", ["goal-a"],
        )
        assert not _has_type(triples, "urn:decompose", TG_ANSWER_TYPE)

    def test_links_to_session(self):
        triples = agent_decomposition_triples(
            "urn:decompose", "urn:session", ["goal-a"],
        )
        ts = _triple_set(triples)
        assert ("urn:decompose", PROV_WAS_DERIVED_FROM, "urn:session") in ts

    def test_includes_goals(self):
        goals = ["What is X?", "What is Y?", "What is Z?"]
        triples = agent_decomposition_triples(
            "urn:decompose", "urn:session", goals,
        )
        values = _get_values(triples, "urn:decompose", TG_SUBAGENT_GOAL)
        assert set(values) == set(goals)

    def test_label_includes_count(self):
        triples = agent_decomposition_triples(
            "urn:decompose", "urn:session", ["a", "b", "c"],
        )
        labels = _get_values(triples, "urn:decompose", RDFS_LABEL)
        assert any("3" in label for label in labels)


class TestFindingTriples:

    def test_has_correct_types(self):
        triples = agent_finding_triples(
            "urn:finding", "urn:decompose", "What is X?",
        )
        assert _has_type(triples, "urn:finding", PROV_ENTITY)
        assert _has_type(triples, "urn:finding", TG_FINDING)
        assert _has_type(triples, "urn:finding", TG_ANSWER_TYPE)

    def test_links_to_decomposition(self):
        triples = agent_finding_triples(
            "urn:finding", "urn:decompose", "What is X?",
        )
        ts = _triple_set(triples)
        assert ("urn:finding", PROV_WAS_DERIVED_FROM, "urn:decompose") in ts

    def test_includes_goal(self):
        triples = agent_finding_triples(
            "urn:finding", "urn:decompose", "What is X?",
        )
        values = _get_values(triples, "urn:finding", TG_SUBAGENT_GOAL)
        assert "What is X?" in values

    def test_includes_document_when_provided(self):
        triples = agent_finding_triples(
            "urn:finding", "urn:decompose", "goal",
            document_id="urn:doc/1",
        )
        values = _get_values(triples, "urn:finding", TG_DOCUMENT)
        assert "urn:doc/1" in values

    def test_no_document_when_none(self):
        triples = agent_finding_triples(
            "urn:finding", "urn:decompose", "goal",
        )
        values = _get_values(triples, "urn:finding", TG_DOCUMENT)
        assert values == []


class TestPlanTriples:

    def test_has_correct_types(self):
        triples = agent_plan_triples(
            "urn:plan", "urn:session", ["step-a"],
        )
        assert _has_type(triples, "urn:plan", PROV_ENTITY)
        assert _has_type(triples, "urn:plan", TG_PLAN_TYPE)

    def test_not_answer_type(self):
        triples = agent_plan_triples(
            "urn:plan", "urn:session", ["step-a"],
        )
        assert not _has_type(triples, "urn:plan", TG_ANSWER_TYPE)

    def test_links_to_session(self):
        triples = agent_plan_triples(
            "urn:plan", "urn:session", ["step-a"],
        )
        ts = _triple_set(triples)
        assert ("urn:plan", PROV_WAS_DERIVED_FROM, "urn:session") in ts

    def test_includes_steps(self):
        steps = ["Define X", "Research Y", "Analyse Z"]
        triples = agent_plan_triples(
            "urn:plan", "urn:session", steps,
        )
        values = _get_values(triples, "urn:plan", TG_PLAN_STEP)
        assert set(values) == set(steps)

    def test_label_includes_count(self):
        triples = agent_plan_triples(
            "urn:plan", "urn:session", ["a", "b"],
        )
        labels = _get_values(triples, "urn:plan", RDFS_LABEL)
        assert any("2" in label for label in labels)


class TestStepResultTriples:

    def test_has_correct_types(self):
        triples = agent_step_result_triples(
            "urn:step", "urn:plan", "Define X",
        )
        assert _has_type(triples, "urn:step", PROV_ENTITY)
        assert _has_type(triples, "urn:step", TG_STEP_RESULT)
        assert _has_type(triples, "urn:step", TG_ANSWER_TYPE)

    def test_links_to_plan(self):
        triples = agent_step_result_triples(
            "urn:step", "urn:plan", "Define X",
        )
        ts = _triple_set(triples)
        assert ("urn:step", PROV_WAS_DERIVED_FROM, "urn:plan") in ts

    def test_includes_goal(self):
        triples = agent_step_result_triples(
            "urn:step", "urn:plan", "Define X",
        )
        values = _get_values(triples, "urn:step", TG_PLAN_STEP)
        assert "Define X" in values

    def test_includes_document_when_provided(self):
        triples = agent_step_result_triples(
            "urn:step", "urn:plan", "goal",
            document_id="urn:doc/step",
        )
        values = _get_values(triples, "urn:step", TG_DOCUMENT)
        assert "urn:doc/step" in values


class TestSynthesisTriples:

    def test_has_correct_types(self):
        triples = agent_synthesis_triples(
            "urn:synthesis", "urn:previous",
        )
        assert _has_type(triples, "urn:synthesis", PROV_ENTITY)
        assert _has_type(triples, "urn:synthesis", TG_SYNTHESIS)
        assert _has_type(triples, "urn:synthesis", TG_ANSWER_TYPE)

    def test_links_to_previous(self):
        triples = agent_synthesis_triples(
            "urn:synthesis", "urn:last-finding",
        )
        ts = _triple_set(triples)
        assert ("urn:synthesis", PROV_WAS_DERIVED_FROM,
                "urn:last-finding") in ts

    def test_includes_document_when_provided(self):
        triples = agent_synthesis_triples(
            "urn:synthesis", "urn:previous",
            document_id="urn:doc/synthesis",
        )
        values = _get_values(triples, "urn:synthesis", TG_DOCUMENT)
        assert "urn:doc/synthesis" in values

    def test_label_is_synthesis(self):
        triples = agent_synthesis_triples(
            "urn:synthesis", "urn:previous",
        )
        labels = _get_values(triples, "urn:synthesis", RDFS_LABEL)
        assert "Synthesis" in labels
