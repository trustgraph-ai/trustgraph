"""
Contract tests for provenance triple wire format — verifies that triples
built by the provenance library can be parsed by the explainability API
through the wire format conversion.
"""

import pytest

from trustgraph.schema import IRI, LITERAL

from trustgraph.provenance import (
    agent_decomposition_triples,
    agent_finding_triples,
    agent_plan_triples,
    agent_step_result_triples,
    agent_synthesis_triples,
)

from trustgraph.api.explainability import (
    ExplainEntity,
    Decomposition,
    Finding,
    Plan,
    StepResult,
    Synthesis,
    wire_triples_to_tuples,
)


def _triples_to_wire(triples):
    """Convert provenance Triple objects to the wire format dicts
    that the gateway/socket client would produce."""
    wire = []
    for t in triples:
        entry = {
            "s": _term_to_wire(t.s),
            "p": _term_to_wire(t.p),
            "o": _term_to_wire(t.o),
        }
        wire.append(entry)
    return wire


def _term_to_wire(term):
    """Convert a Term to wire format dict."""
    if term.type == IRI:
        return {"t": "i", "i": term.iri}
    elif term.type == LITERAL:
        return {"t": "l", "v": term.value}
    return {"t": "l", "v": str(term)}


def _roundtrip(triples, uri):
    """Convert triples through wire format and parse via from_triples."""
    wire = _triples_to_wire(triples)
    tuples = wire_triples_to_tuples(wire)
    return ExplainEntity.from_triples(uri, tuples)


@pytest.mark.contract
class TestDecompositionWireFormat:

    def test_roundtrip(self):
        triples = agent_decomposition_triples(
            "urn:decompose", "urn:session",
            ["What is X?", "What is Y?"],
        )
        entity = _roundtrip(triples, "urn:decompose")

        assert isinstance(entity, Decomposition)
        assert set(entity.goals) == {"What is X?", "What is Y?"}


@pytest.mark.contract
class TestFindingWireFormat:

    def test_roundtrip(self):
        triples = agent_finding_triples(
            "urn:finding", "urn:decompose", "What is X?",
            document_id="urn:doc/finding",
        )
        entity = _roundtrip(triples, "urn:finding")

        assert isinstance(entity, Finding)
        assert entity.goal == "What is X?"
        assert entity.document == "urn:doc/finding"


@pytest.mark.contract
class TestPlanWireFormat:

    def test_roundtrip(self):
        triples = agent_plan_triples(
            "urn:plan", "urn:session",
            ["Step 1", "Step 2", "Step 3"],
        )
        entity = _roundtrip(triples, "urn:plan")

        assert isinstance(entity, Plan)
        assert set(entity.steps) == {"Step 1", "Step 2", "Step 3"}


@pytest.mark.contract
class TestStepResultWireFormat:

    def test_roundtrip(self):
        triples = agent_step_result_triples(
            "urn:step", "urn:plan", "Define X",
            document_id="urn:doc/step",
        )
        entity = _roundtrip(triples, "urn:step")

        assert isinstance(entity, StepResult)
        assert entity.step == "Define X"
        assert entity.document == "urn:doc/step"


@pytest.mark.contract
class TestSynthesisWireFormat:

    def test_roundtrip(self):
        triples = agent_synthesis_triples(
            "urn:synthesis", "urn:previous",
            document_id="urn:doc/synthesis",
        )
        entity = _roundtrip(triples, "urn:synthesis")

        assert isinstance(entity, Synthesis)
        assert entity.document == "urn:doc/synthesis"
