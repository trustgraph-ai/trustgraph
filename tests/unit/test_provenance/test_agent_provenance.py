"""
Tests for agent provenance triple builder functions.
"""

import json
import pytest

from trustgraph.schema import Triple, Term, IRI, LITERAL

from trustgraph.provenance.agent import (
    agent_session_triples,
    agent_iteration_triples,
    agent_final_triples,
)

from trustgraph.provenance.namespaces import (
    RDF_TYPE, RDFS_LABEL,
    PROV_ACTIVITY, PROV_ENTITY, PROV_WAS_DERIVED_FROM, PROV_STARTED_AT_TIME,
    TG_QUERY, TG_THOUGHT, TG_ACTION, TG_ARGUMENTS, TG_OBSERVATION, TG_ANSWER,
    TG_QUESTION, TG_ANALYSIS, TG_CONCLUSION, TG_DOCUMENT,
    TG_THOUGHT_DOCUMENT, TG_OBSERVATION_DOCUMENT,
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
        assert has_type(triples, self.SESSION_URI, PROV_ACTIVITY)
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
    PARENT_URI = "urn:trustgraph:agent:test-session"

    def test_iteration_types(self):
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            thought="thinking", action="search", observation="found it",
        )
        assert has_type(triples, self.ITER_URI, PROV_ENTITY)
        assert has_type(triples, self.ITER_URI, TG_ANALYSIS)

    def test_iteration_derived_from_parent(self):
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            action="search",
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.ITER_URI)
        assert derived is not None
        assert derived.o.iri == self.PARENT_URI

    def test_iteration_label_includes_action(self):
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            action="graph-rag-query",
        )
        label = find_triple(triples, RDFS_LABEL, self.ITER_URI)
        assert label is not None
        assert "graph-rag-query" in label.o.value

    def test_iteration_thought_inline(self):
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            thought="I need to search for info",
            action="search",
        )
        thought = find_triple(triples, TG_THOUGHT, self.ITER_URI)
        assert thought is not None
        assert thought.o.value == "I need to search for info"

    def test_iteration_thought_document_preferred(self):
        """When thought_document_id is provided, inline thought is not stored."""
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            thought="inline thought",
            action="search",
            thought_document_id="urn:doc:thought-1",
        )
        thought_doc = find_triple(triples, TG_THOUGHT_DOCUMENT, self.ITER_URI)
        assert thought_doc is not None
        assert thought_doc.o.iri == "urn:doc:thought-1"
        thought_inline = find_triple(triples, TG_THOUGHT, self.ITER_URI)
        assert thought_inline is None

    def test_iteration_observation_inline(self):
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            action="search",
            observation="Found 3 results",
        )
        obs = find_triple(triples, TG_OBSERVATION, self.ITER_URI)
        assert obs is not None
        assert obs.o.value == "Found 3 results"

    def test_iteration_observation_document_preferred(self):
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            action="search",
            observation="inline obs",
            observation_document_id="urn:doc:obs-1",
        )
        obs_doc = find_triple(triples, TG_OBSERVATION_DOCUMENT, self.ITER_URI)
        assert obs_doc is not None
        assert obs_doc.o.iri == "urn:doc:obs-1"
        obs_inline = find_triple(triples, TG_OBSERVATION, self.ITER_URI)
        assert obs_inline is None

    def test_iteration_action_recorded(self):
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            action="graph-rag-query",
        )
        action = find_triple(triples, TG_ACTION, self.ITER_URI)
        assert action is not None
        assert action.o.value == "graph-rag-query"

    def test_iteration_arguments_json_encoded(self):
        args = {"query": "test query", "limit": 10}
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            action="search",
            arguments=args,
        )
        arguments = find_triple(triples, TG_ARGUMENTS, self.ITER_URI)
        assert arguments is not None
        parsed = json.loads(arguments.o.value)
        assert parsed == args

    def test_iteration_default_arguments_empty_dict(self):
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            action="search",
        )
        arguments = find_triple(triples, TG_ARGUMENTS, self.ITER_URI)
        assert arguments is not None
        parsed = json.loads(arguments.o.value)
        assert parsed == {}

    def test_iteration_no_thought_or_observation(self):
        """Minimal iteration with just action — no thought or observation triples."""
        triples = agent_iteration_triples(
            self.ITER_URI, self.PARENT_URI,
            action="noop",
        )
        thought = find_triple(triples, TG_THOUGHT, self.ITER_URI)
        obs = find_triple(triples, TG_OBSERVATION, self.ITER_URI)
        assert thought is None
        assert obs is None

    def test_iteration_chaining(self):
        """Second iteration derives from first iteration, not session."""
        iter1_uri = "urn:trustgraph:agent:sess/i1"
        iter2_uri = "urn:trustgraph:agent:sess/i2"

        triples1 = agent_iteration_triples(
            iter1_uri, self.PARENT_URI, action="step1",
        )
        triples2 = agent_iteration_triples(
            iter2_uri, iter1_uri, action="step2",
        )

        derived1 = find_triple(triples1, PROV_WAS_DERIVED_FROM, iter1_uri)
        assert derived1.o.iri == self.PARENT_URI

        derived2 = find_triple(triples2, PROV_WAS_DERIVED_FROM, iter2_uri)
        assert derived2.o.iri == iter1_uri


# ---------------------------------------------------------------------------
# agent_final_triples
# ---------------------------------------------------------------------------

class TestAgentFinalTriples:

    FINAL_URI = "urn:trustgraph:agent:test-session/final"
    PARENT_URI = "urn:trustgraph:agent:test-session/i3"

    def test_final_types(self):
        triples = agent_final_triples(
            self.FINAL_URI, self.PARENT_URI, answer="42"
        )
        assert has_type(triples, self.FINAL_URI, PROV_ENTITY)
        assert has_type(triples, self.FINAL_URI, TG_CONCLUSION)

    def test_final_derived_from_parent(self):
        triples = agent_final_triples(
            self.FINAL_URI, self.PARENT_URI, answer="42"
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.FINAL_URI)
        assert derived is not None
        assert derived.o.iri == self.PARENT_URI

    def test_final_label(self):
        triples = agent_final_triples(
            self.FINAL_URI, self.PARENT_URI, answer="42"
        )
        label = find_triple(triples, RDFS_LABEL, self.FINAL_URI)
        assert label is not None
        assert label.o.value == "Conclusion"

    def test_final_inline_answer(self):
        triples = agent_final_triples(
            self.FINAL_URI, self.PARENT_URI, answer="The answer is 42"
        )
        answer = find_triple(triples, TG_ANSWER, self.FINAL_URI)
        assert answer is not None
        assert answer.o.value == "The answer is 42"

    def test_final_document_reference(self):
        triples = agent_final_triples(
            self.FINAL_URI, self.PARENT_URI,
            document_id="urn:trustgraph:agent:sess/answer",
        )
        doc = find_triple(triples, TG_DOCUMENT, self.FINAL_URI)
        assert doc is not None
        assert doc.o.type == IRI
        assert doc.o.iri == "urn:trustgraph:agent:sess/answer"

    def test_final_document_takes_precedence(self):
        triples = agent_final_triples(
            self.FINAL_URI, self.PARENT_URI,
            answer="inline",
            document_id="urn:doc:123",
        )
        doc = find_triple(triples, TG_DOCUMENT, self.FINAL_URI)
        assert doc is not None
        answer = find_triple(triples, TG_ANSWER, self.FINAL_URI)
        assert answer is None

    def test_final_no_answer_or_document(self):
        triples = agent_final_triples(self.FINAL_URI, self.PARENT_URI)
        answer = find_triple(triples, TG_ANSWER, self.FINAL_URI)
        doc = find_triple(triples, TG_DOCUMENT, self.FINAL_URI)
        assert answer is None
        assert doc is None

    def test_final_derives_from_session_when_no_iterations(self):
        """When agent answers immediately, final derives from session."""
        session_uri = "urn:trustgraph:agent:test-session"
        triples = agent_final_triples(
            self.FINAL_URI, session_uri, answer="direct answer"
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.FINAL_URI)
        assert derived.o.iri == session_uri
