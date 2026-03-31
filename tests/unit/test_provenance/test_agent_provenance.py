"""
Tests for agent provenance triple builder functions.
"""

import json
import pytest

from trustgraph.schema import Triple, Term, IRI, LITERAL

from trustgraph.provenance.agent import (
    agent_session_triples,
    agent_iteration_triples,
    agent_observation_triples,
    agent_final_triples,
)

from trustgraph.provenance.namespaces import (
    RDF_TYPE, RDFS_LABEL,
    PROV_ENTITY, PROV_WAS_DERIVED_FROM,
    PROV_STARTED_AT_TIME,
    TG_QUERY, TG_THOUGHT, TG_ACTION, TG_ARGUMENTS,
    TG_QUESTION, TG_ANALYSIS, TG_CONCLUSION, TG_DOCUMENT,
    TG_ANSWER_TYPE, TG_REFLECTION_TYPE, TG_THOUGHT_TYPE, TG_OBSERVATION_TYPE,
    TG_TOOL_USE,
    TG_AGENT_QUESTION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_triple(triples, predicate, subject=None):
    for t in triples:
        if t.p.iri == predicate:
            if subject is None or t.s.iri == subject:
                return t
    return None


def find_triples(triples, predicate, subject=None):
    return [
        t for t in triples
        if t.p.iri == predicate and (subject is None or t.s.iri == subject)
    ]


def has_type(triples, subject, rdf_type):
    for t in triples:
        if (t.s.iri == subject and t.p.iri == RDF_TYPE
                and t.o.type == IRI and t.o.iri == rdf_type):
            return True
    return False


# ---------------------------------------------------------------------------
# agent_session_triples
# ---------------------------------------------------------------------------

class TestAgentSessionTriples:

    SESSION_URI = "urn:trustgraph:agent:test-session"

    def test_session_types(self):
        triples = agent_session_triples(
            self.SESSION_URI, "What is X?", "2024-01-01T00:00:00Z"
        )
        assert has_type(triples, self.SESSION_URI, PROV_ENTITY)
        assert has_type(triples, self.SESSION_URI, TG_QUESTION)
        assert has_type(triples, self.SESSION_URI, TG_AGENT_QUESTION)

    def test_session_query_text(self):
        triples = agent_session_triples(
            self.SESSION_URI, "What is X?", "2024-01-01T00:00:00Z"
        )
        query = find_triple(triples, TG_QUERY, self.SESSION_URI)
        assert query is not None
        assert query.o.value == "What is X?"

    def test_session_timestamp(self):
        triples = agent_session_triples(
            self.SESSION_URI, "Q", "2024-06-15T10:00:00Z"
        )
        ts = find_triple(triples, PROV_STARTED_AT_TIME, self.SESSION_URI)
        assert ts is not None
        assert ts.o.value == "2024-06-15T10:00:00Z"

    def test_session_default_timestamp(self):
        triples = agent_session_triples(self.SESSION_URI, "Q")
        ts = find_triple(triples, PROV_STARTED_AT_TIME, self.SESSION_URI)
        assert ts is not None
        assert len(ts.o.value) > 0

    def test_session_label(self):
        triples = agent_session_triples(
            self.SESSION_URI, "Q", "2024-01-01T00:00:00Z"
        )
        label = find_triple(triples, RDFS_LABEL, self.SESSION_URI)
        assert label is not None
        assert label.o.value == "Agent Question"

    def test_session_triple_count(self):
        triples = agent_session_triples(
            self.SESSION_URI, "Q", "2024-01-01T00:00:00Z"
        )
        assert len(triples) == 6


# ---------------------------------------------------------------------------
# agent_iteration_triples
# ---------------------------------------------------------------------------

class TestAgentIterationTriples:

    ITER_URI = "urn:trustgraph:agent:test-session/i1"
    SESSION_URI = "urn:trustgraph:agent:test-session"
    PREV_URI = "urn:trustgraph:agent:test-session/i0"

    def test_iteration_types(self):
        triples = agent_iteration_triples(
            self.ITER_URI, question_uri=self.SESSION_URI,
            action="search",
        )
        assert has_type(triples, self.ITER_URI, PROV_ENTITY)
        assert has_type(triples, self.ITER_URI, TG_ANALYSIS)
        assert has_type(triples, self.ITER_URI, TG_TOOL_USE)

    def test_first_iteration_derived_from_question(self):
        """First iteration uses wasDerivedFrom to link to question entity."""
        triples = agent_iteration_triples(
            self.ITER_URI, question_uri=self.SESSION_URI,
            action="search",
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.ITER_URI)
        assert derived is not None
        assert derived.o.iri == self.SESSION_URI

    def test_subsequent_iteration_derived_from_previous(self):
        """Subsequent iterations use wasDerivedFrom to link to previous iteration."""
        triples = agent_iteration_triples(
            self.ITER_URI, previous_uri=self.PREV_URI,
            action="search",
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.ITER_URI)
        assert derived is not None
        assert derived.o.iri == self.PREV_URI

    def test_iteration_label_includes_action(self):
        triples = agent_iteration_triples(
            self.ITER_URI, question_uri=self.SESSION_URI,
            action="graph-rag-query",
        )
        label = find_triple(triples, RDFS_LABEL, self.ITER_URI)
        assert label is not None
        assert "graph-rag-query" in label.o.value

    def test_iteration_thought_sub_entity(self):
        """Thought is a sub-entity with Reflection and Thought types."""
        thought_uri = "urn:trustgraph:agent:test-session/i1/thought"
        thought_doc = "urn:doc:thought-1"
        triples = agent_iteration_triples(
            self.ITER_URI, question_uri=self.SESSION_URI,
            action="search",
            thought_uri=thought_uri,
            thought_document_id=thought_doc,
        )
        # Iteration links to thought sub-entity
        thought_link = find_triple(triples, TG_THOUGHT, self.ITER_URI)
        assert thought_link is not None
        assert thought_link.o.iri == thought_uri
        # Thought has correct types
        assert has_type(triples, thought_uri, TG_REFLECTION_TYPE)
        assert has_type(triples, thought_uri, TG_THOUGHT_TYPE)
        # Thought was derived from iteration
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, thought_uri)
        assert derived is not None
        assert derived.o.iri == self.ITER_URI
        # Thought has document reference
        doc = find_triple(triples, TG_DOCUMENT, thought_uri)
        assert doc is not None
        assert doc.o.iri == thought_doc

    def test_iteration_no_observation_sub_entity(self):
        """Iteration no longer embeds observation — it's a separate entity."""
        triples = agent_iteration_triples(
            self.ITER_URI, question_uri=self.SESSION_URI,
            action="search",
        )
        # No TG_OBSERVATION predicate on the iteration
        for t in triples:
            assert "observation" not in t.p.iri.lower() or "Observation" not in t.p.iri

    def test_iteration_action_recorded(self):
        triples = agent_iteration_triples(
            self.ITER_URI, question_uri=self.SESSION_URI,
            action="graph-rag-query",
        )
        action = find_triple(triples, TG_ACTION, self.ITER_URI)
        assert action is not None
        assert action.o.value == "graph-rag-query"

    def test_iteration_arguments_json_encoded(self):
        args = {"query": "test query", "limit": 10}
        triples = agent_iteration_triples(
            self.ITER_URI, question_uri=self.SESSION_URI,
            action="search",
            arguments=args,
        )
        arguments = find_triple(triples, TG_ARGUMENTS, self.ITER_URI)
        assert arguments is not None
        parsed = json.loads(arguments.o.value)
        assert parsed == args

    def test_iteration_default_arguments_empty_dict(self):
        triples = agent_iteration_triples(
            self.ITER_URI, question_uri=self.SESSION_URI,
            action="search",
        )
        arguments = find_triple(triples, TG_ARGUMENTS, self.ITER_URI)
        assert arguments is not None
        parsed = json.loads(arguments.o.value)
        assert parsed == {}

    def test_iteration_no_thought(self):
        """Minimal iteration with just action — no thought triples."""
        triples = agent_iteration_triples(
            self.ITER_URI, question_uri=self.SESSION_URI,
            action="noop",
        )
        thought = find_triple(triples, TG_THOUGHT, self.ITER_URI)
        assert thought is None

    def test_iteration_chaining(self):
        """Both first and second iterations use wasDerivedFrom."""
        iter1_uri = "urn:trustgraph:agent:sess/i1"
        iter2_uri = "urn:trustgraph:agent:sess/i2"

        triples1 = agent_iteration_triples(
            iter1_uri, question_uri=self.SESSION_URI, action="step1",
        )
        triples2 = agent_iteration_triples(
            iter2_uri, previous_uri=iter1_uri, action="step2",
        )

        derived1 = find_triple(triples1, PROV_WAS_DERIVED_FROM, iter1_uri)
        assert derived1.o.iri == self.SESSION_URI

        derived2 = find_triple(triples2, PROV_WAS_DERIVED_FROM, iter2_uri)
        assert derived2.o.iri == iter1_uri


# ---------------------------------------------------------------------------
# agent_observation_triples
# ---------------------------------------------------------------------------

class TestAgentObservationTriples:

    OBS_URI = "urn:trustgraph:agent:test-session/i1/observation"
    ITER_URI = "urn:trustgraph:agent:test-session/i1"

    def test_observation_types(self):
        triples = agent_observation_triples(
            self.OBS_URI, self.ITER_URI,
        )
        assert has_type(triples, self.OBS_URI, PROV_ENTITY)
        assert has_type(triples, self.OBS_URI, TG_OBSERVATION_TYPE)

    def test_observation_derived_from_iteration(self):
        triples = agent_observation_triples(
            self.OBS_URI, self.ITER_URI,
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.OBS_URI)
        assert derived is not None
        assert derived.o.iri == self.ITER_URI

    def test_observation_label(self):
        triples = agent_observation_triples(
            self.OBS_URI, self.ITER_URI,
        )
        label = find_triple(triples, RDFS_LABEL, self.OBS_URI)
        assert label is not None
        assert label.o.value == "Observation"

    def test_observation_document(self):
        doc_id = "urn:doc:obs-1"
        triples = agent_observation_triples(
            self.OBS_URI, self.ITER_URI, document_id=doc_id,
        )
        doc = find_triple(triples, TG_DOCUMENT, self.OBS_URI)
        assert doc is not None
        assert doc.o.iri == doc_id

    def test_observation_no_document(self):
        triples = agent_observation_triples(
            self.OBS_URI, self.ITER_URI,
        )
        doc = find_triple(triples, TG_DOCUMENT, self.OBS_URI)
        assert doc is None


# ---------------------------------------------------------------------------
# agent_final_triples
# ---------------------------------------------------------------------------

class TestAgentFinalTriples:

    FINAL_URI = "urn:trustgraph:agent:test-session/final"
    PREV_URI = "urn:trustgraph:agent:test-session/i3"
    SESSION_URI = "urn:trustgraph:agent:test-session"

    def test_final_types(self):
        triples = agent_final_triples(
            self.FINAL_URI, previous_uri=self.PREV_URI,
        )
        assert has_type(triples, self.FINAL_URI, PROV_ENTITY)
        assert has_type(triples, self.FINAL_URI, TG_CONCLUSION)
        assert has_type(triples, self.FINAL_URI, TG_ANSWER_TYPE)

    def test_final_derived_from_previous(self):
        """Conclusion with iterations uses wasDerivedFrom."""
        triples = agent_final_triples(
            self.FINAL_URI, previous_uri=self.PREV_URI,
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.FINAL_URI)
        assert derived is not None
        assert derived.o.iri == self.PREV_URI

    def test_final_derived_from_question_when_no_iterations(self):
        """When agent answers immediately, final uses wasDerivedFrom to question."""
        triples = agent_final_triples(
            self.FINAL_URI, question_uri=self.SESSION_URI,
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.FINAL_URI)
        assert derived is not None
        assert derived.o.iri == self.SESSION_URI

    def test_final_label(self):
        triples = agent_final_triples(
            self.FINAL_URI, previous_uri=self.PREV_URI,
        )
        label = find_triple(triples, RDFS_LABEL, self.FINAL_URI)
        assert label is not None
        assert label.o.value == "Conclusion"

    def test_final_document_reference(self):
        triples = agent_final_triples(
            self.FINAL_URI, previous_uri=self.PREV_URI,
            document_id="urn:trustgraph:agent:sess/answer",
        )
        doc = find_triple(triples, TG_DOCUMENT, self.FINAL_URI)
        assert doc is not None
        assert doc.o.type == IRI
        assert doc.o.iri == "urn:trustgraph:agent:sess/answer"

    def test_final_no_document(self):
        triples = agent_final_triples(
            self.FINAL_URI, previous_uri=self.PREV_URI,
        )
        doc = find_triple(triples, TG_DOCUMENT, self.FINAL_URI)
        assert doc is None
