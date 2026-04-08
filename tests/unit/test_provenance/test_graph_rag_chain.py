"""
Structural test for the graph-rag provenance chain.

Verifies that a complete graph-rag query produces the expected
provenance chain:

    question → grounding → exploration → focus → synthesis

Each step must:
- Have the correct rdf:type
- Link to its predecessor via prov:wasDerivedFrom
- Carry expected domain-specific data
"""

import pytest

from trustgraph.provenance.triples import (
    question_triples,
    grounding_triples,
    exploration_triples,
    focus_triples,
    synthesis_triples,
)
from trustgraph.provenance.uris import (
    question_uri,
    grounding_uri,
    exploration_uri,
    focus_uri,
    synthesis_uri,
)
from trustgraph.provenance.namespaces import (
    RDF_TYPE, RDFS_LABEL,
    PROV_ENTITY, PROV_WAS_DERIVED_FROM,
    TG_QUESTION, TG_GROUNDING, TG_EXPLORATION, TG_FOCUS, TG_SYNTHESIS,
    TG_GRAPH_RAG_QUESTION, TG_ANSWER_TYPE,
    TG_QUERY, TG_CONCEPT, TG_ENTITY,
    TG_EDGE_COUNT, TG_SELECTED_EDGE, TG_EDGE, TG_REASONING,
    TG_DOCUMENT,
    PROV_STARTED_AT_TIME,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION_ID = "test-session-1234"


def find_triple(triples, predicate, subject=None):
    """Find first triple matching predicate (and optionally subject)."""
    for t in triples:
        if t.p.iri == predicate:
            if subject is None or t.s.iri == subject:
                return t
    return None


def find_triples(triples, predicate, subject=None):
    """Find all triples matching predicate (and optionally subject)."""
    return [
        t for t in triples
        if t.p.iri == predicate
        and (subject is None or t.s.iri == subject)
    ]


def has_type(triples, subject, rdf_type):
    """Check if subject has the given rdf:type."""
    return any(
        t.s.iri == subject and t.p.iri == RDF_TYPE and t.o.iri == rdf_type
        for t in triples
    )


def derived_from(triples, subject):
    """Get the wasDerivedFrom target URI for a subject."""
    t = find_triple(triples, PROV_WAS_DERIVED_FROM, subject)
    return t.o.iri if t else None


# ---------------------------------------------------------------------------
# Build the full chain
# ---------------------------------------------------------------------------

@pytest.fixture
def chain():
    """Build all provenance triples for a complete graph-rag query."""
    q_uri = question_uri(SESSION_ID)
    gnd_uri = grounding_uri(SESSION_ID)
    exp_uri = exploration_uri(SESSION_ID)
    foc_uri = focus_uri(SESSION_ID)
    syn_uri = synthesis_uri(SESSION_ID)

    q = question_triples(q_uri, "What is quantum computing?", "2026-01-01T00:00:00Z")
    gnd = grounding_triples(gnd_uri, q_uri, ["quantum", "computing"])
    exp = exploration_triples(
        exp_uri, gnd_uri, edge_count=42,
        entities=["urn:entity:1", "urn:entity:2"],
    )
    foc = focus_triples(
        foc_uri, exp_uri,
        selected_edges_with_reasoning=[
            {
                "edge": (
                    "http://example.com/QuantumComputing",
                    "http://schema.org/relatedTo",
                    "http://example.com/Physics",
                ),
                "reasoning": "Directly relevant to the query",
            },
            {
                "edge": (
                    "http://example.com/QuantumComputing",
                    "http://schema.org/name",
                    "Quantum Computing",
                ),
                "reasoning": "Provides the entity label",
            },
        ],
        session_id=SESSION_ID,
    )
    syn = synthesis_triples(syn_uri, foc_uri, document_id="urn:doc:answer-1")

    return {
        "uris": {
            "question": q_uri,
            "grounding": gnd_uri,
            "exploration": exp_uri,
            "focus": foc_uri,
            "synthesis": syn_uri,
        },
        "triples": {
            "question": q,
            "grounding": gnd,
            "exploration": exp,
            "focus": foc,
            "synthesis": syn,
        },
        "all": q + gnd + exp + foc + syn,
    }


# ---------------------------------------------------------------------------
# Chain structure tests
# ---------------------------------------------------------------------------

class TestGraphRagProvenanceChain:
    """Verify the full question → grounding → exploration → focus → synthesis chain."""

    def test_chain_has_five_stages(self, chain):
        """Each stage should produce at least some triples."""
        for stage in ["question", "grounding", "exploration", "focus", "synthesis"]:
            assert len(chain["triples"][stage]) > 0, f"{stage} produced no triples"

    def test_derivation_chain(self, chain):
        """
        The wasDerivedFrom links must form:
        grounding → question, exploration → grounding,
        focus → exploration, synthesis → focus.
        """
        uris = chain["uris"]
        all_triples = chain["all"]

        assert derived_from(all_triples, uris["grounding"]) == uris["question"]
        assert derived_from(all_triples, uris["exploration"]) == uris["grounding"]
        assert derived_from(all_triples, uris["focus"]) == uris["exploration"]
        assert derived_from(all_triples, uris["synthesis"]) == uris["focus"]

    def test_question_has_no_parent(self, chain):
        """The root question should not derive from anything (no parent_uri)."""
        uris = chain["uris"]
        all_triples = chain["all"]
        assert derived_from(all_triples, uris["question"]) is None

    def test_question_with_parent(self):
        """When a parent_uri is given, question should derive from it."""
        q_uri = question_uri("child-session")
        parent = "urn:trustgraph:agent:iteration:parent"
        q = question_triples(q_uri, "sub-query", "2026-01-01T00:00:00Z",
                             parent_uri=parent)
        assert derived_from(q, q_uri) == parent


# ---------------------------------------------------------------------------
# Type annotation tests
# ---------------------------------------------------------------------------

class TestGraphRagProvenanceTypes:
    """Each stage must have the correct rdf:type annotations."""

    def test_question_types(self, chain):
        uris = chain["uris"]
        triples = chain["triples"]["question"]
        assert has_type(triples, uris["question"], PROV_ENTITY)
        assert has_type(triples, uris["question"], TG_GRAPH_RAG_QUESTION)

    def test_grounding_types(self, chain):
        uris = chain["uris"]
        triples = chain["triples"]["grounding"]
        assert has_type(triples, uris["grounding"], PROV_ENTITY)
        assert has_type(triples, uris["grounding"], TG_GROUNDING)

    def test_exploration_types(self, chain):
        uris = chain["uris"]
        triples = chain["triples"]["exploration"]
        assert has_type(triples, uris["exploration"], PROV_ENTITY)
        assert has_type(triples, uris["exploration"], TG_EXPLORATION)

    def test_focus_types(self, chain):
        uris = chain["uris"]
        triples = chain["triples"]["focus"]
        assert has_type(triples, uris["focus"], PROV_ENTITY)
        assert has_type(triples, uris["focus"], TG_FOCUS)

    def test_synthesis_types(self, chain):
        uris = chain["uris"]
        triples = chain["triples"]["synthesis"]
        assert has_type(triples, uris["synthesis"], PROV_ENTITY)
        assert has_type(triples, uris["synthesis"], TG_SYNTHESIS)
        assert has_type(triples, uris["synthesis"], TG_ANSWER_TYPE)


# ---------------------------------------------------------------------------
# Domain-specific content tests
# ---------------------------------------------------------------------------

class TestGraphRagProvenanceContent:
    """Each stage should carry the expected domain data."""

    def test_question_has_query_text(self, chain):
        uris = chain["uris"]
        t = find_triple(chain["triples"]["question"], TG_QUERY, uris["question"])
        assert t is not None
        assert t.o.value == "What is quantum computing?"

    def test_question_has_timestamp(self, chain):
        uris = chain["uris"]
        t = find_triple(chain["triples"]["question"], PROV_STARTED_AT_TIME, uris["question"])
        assert t is not None
        assert t.o.value == "2026-01-01T00:00:00Z"

    def test_grounding_has_concepts(self, chain):
        uris = chain["uris"]
        concepts = find_triples(chain["triples"]["grounding"], TG_CONCEPT, uris["grounding"])
        concept_values = {t.o.value for t in concepts}
        assert concept_values == {"quantum", "computing"}

    def test_exploration_has_edge_count(self, chain):
        uris = chain["uris"]
        t = find_triple(chain["triples"]["exploration"], TG_EDGE_COUNT, uris["exploration"])
        assert t is not None
        assert t.o.value == "42"

    def test_exploration_has_entities(self, chain):
        uris = chain["uris"]
        entities = find_triples(chain["triples"]["exploration"], TG_ENTITY, uris["exploration"])
        entity_iris = {t.o.iri for t in entities}
        assert entity_iris == {"urn:entity:1", "urn:entity:2"}

    def test_focus_has_selected_edges(self, chain):
        uris = chain["uris"]
        edges = find_triples(chain["triples"]["focus"], TG_SELECTED_EDGE, uris["focus"])
        assert len(edges) == 2

    def test_focus_edges_have_quoted_triples(self, chain):
        """Each edge selection entity should have a tg:edge with a quoted triple."""
        focus = chain["triples"]["focus"]
        edge_triples = find_triples(focus, TG_EDGE)
        assert len(edge_triples) == 2

        # Each should have a quoted triple as the object
        for t in edge_triples:
            assert t.o.triple is not None, "tg:edge object should be a quoted triple"

    def test_focus_edges_have_reasoning(self, chain):
        """Each edge selection entity should have tg:reasoning."""
        focus = chain["triples"]["focus"]
        reasoning = find_triples(focus, TG_REASONING)
        assert len(reasoning) == 2
        reasoning_texts = {t.o.value for t in reasoning}
        assert "Directly relevant to the query" in reasoning_texts
        assert "Provides the entity label" in reasoning_texts

    def test_synthesis_has_document_ref(self, chain):
        uris = chain["uris"]
        t = find_triple(chain["triples"]["synthesis"], TG_DOCUMENT, uris["synthesis"])
        assert t is not None
        assert t.o.iri == "urn:doc:answer-1"

    def test_synthesis_has_labels(self, chain):
        uris = chain["uris"]
        t = find_triple(chain["triples"]["synthesis"], RDFS_LABEL, uris["synthesis"])
        assert t is not None
        assert t.o.value == "Synthesis"
