"""
Tests for inline explainability triples in response translators
and ProvenanceEvent parsing.
"""

import pytest
from trustgraph.schema import (
    GraphRagResponse, DocumentRagResponse, AgentResponse,
    Term, Triple, IRI, LITERAL, Error,
)
from trustgraph.messaging.translators.retrieval import (
    GraphRagResponseTranslator,
    DocumentRagResponseTranslator,
)
from trustgraph.messaging.translators.agent import (
    AgentResponseTranslator,
)
from trustgraph.api.types import ProvenanceEvent


# --- Helpers ---

def make_triple(s_iri, p_iri, o_value, o_type=LITERAL):
    """Create a Triple with IRI subject/predicate and typed object."""
    o = Term(type=IRI, iri=o_value) if o_type == IRI else Term(type=LITERAL, value=o_value)
    return Triple(
        s=Term(type=IRI, iri=s_iri),
        p=Term(type=IRI, iri=p_iri),
        o=o,
    )


def sample_triples():
    """A few provenance triples for a question entity."""
    return [
        make_triple(
            "urn:trustgraph:question:abc123",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "https://trustgraph.ai/ns/GraphRagQuestion",
            o_type=IRI,
        ),
        make_triple(
            "urn:trustgraph:question:abc123",
            "https://trustgraph.ai/ns/query",
            "What is the internet?",
        ),
        make_triple(
            "urn:trustgraph:question:abc123",
            "http://www.w3.org/ns/prov#startedAtTime",
            "2026-04-07T09:00:00Z",
        ),
    ]


# --- GraphRag Translator ---

class TestGraphRagExplainTriples:

    def test_explain_triples_encoded(self):
        translator = GraphRagResponseTranslator()
        triples = sample_triples()

        response = GraphRagResponse(
            message_type="explain",
            explain_id="urn:trustgraph:question:abc123",
            explain_graph="urn:graph:retrieval",
            explain_triples=triples,
        )

        result = translator.encode(response)

        assert "explain_triples" in result
        assert len(result["explain_triples"]) == 3

        # Check first triple is properly encoded
        t = result["explain_triples"][0]
        assert t["s"]["t"] == "i"
        assert t["s"]["i"] == "urn:trustgraph:question:abc123"
        assert t["p"]["t"] == "i"

    def test_explain_triples_empty_not_included(self):
        translator = GraphRagResponseTranslator()

        response = GraphRagResponse(
            message_type="chunk",
            response="Some answer text",
        )

        result = translator.encode(response)

        assert "explain_triples" not in result

    def test_explain_with_completion_returns_not_final(self):
        translator = GraphRagResponseTranslator()

        response = GraphRagResponse(
            message_type="explain",
            explain_id="urn:trustgraph:question:abc123",
            explain_triples=sample_triples(),
            end_of_session=False,
        )

        result, is_final = translator.encode_with_completion(response)
        assert is_final is False

    def test_explain_id_and_graph_included(self):
        translator = GraphRagResponseTranslator()

        response = GraphRagResponse(
            message_type="explain",
            explain_id="urn:trustgraph:question:abc123",
            explain_graph="urn:graph:retrieval",
            explain_triples=sample_triples(),
        )

        result = translator.encode(response)
        assert result["explain_id"] == "urn:trustgraph:question:abc123"
        assert result["explain_graph"] == "urn:graph:retrieval"


# --- DocumentRag Translator ---

class TestDocumentRagExplainTriples:

    def test_explain_triples_encoded(self):
        translator = DocumentRagResponseTranslator()

        response = DocumentRagResponse(
            response=None,
            message_type="explain",
            explain_id="urn:trustgraph:docrag:abc123",
            explain_graph="urn:graph:retrieval",
            explain_triples=sample_triples(),
        )

        result = translator.encode(response)

        assert "explain_triples" in result
        assert len(result["explain_triples"]) == 3

    def test_explain_triples_empty_not_included(self):
        translator = DocumentRagResponseTranslator()

        response = DocumentRagResponse(
            response="Answer text",
            message_type="chunk",
        )

        result = translator.encode(response)
        assert "explain_triples" not in result


# --- Agent Translator ---

class TestAgentExplainTriples:

    def test_explain_triples_encoded(self):
        translator = AgentResponseTranslator()

        response = AgentResponse(
            chunk_type="explain",
            content="",
            explain_id="urn:trustgraph:agent:session:abc123",
            explain_graph="urn:graph:retrieval",
            explain_triples=sample_triples(),
        )

        result = translator.encode(response)

        assert "explain_triples" in result
        assert len(result["explain_triples"]) == 3

        t = result["explain_triples"][1]
        assert t["p"]["i"] == "https://trustgraph.ai/ns/query"
        assert t["o"]["t"] == "l"
        assert t["o"]["v"] == "What is the internet?"

    def test_explain_triples_empty_not_included(self):
        translator = AgentResponseTranslator()

        response = AgentResponse(
            chunk_type="thought",
            content="I need to think...",
        )

        result = translator.encode(response)
        assert "explain_triples" not in result

    def test_explain_with_completion_not_final(self):
        translator = AgentResponseTranslator()

        response = AgentResponse(
            chunk_type="explain",
            explain_id="urn:trustgraph:agent:session:abc123",
            explain_triples=sample_triples(),
            end_of_dialog=False,
        )

        result, is_final = translator.encode_with_completion(response)
        assert is_final is False

    def test_explain_with_completion_final(self):
        translator = AgentResponseTranslator()

        response = AgentResponse(
            chunk_type="answer",
            content="The answer is...",
            end_of_dialog=True,
        )

        result, is_final = translator.encode_with_completion(response)
        assert is_final is True


# --- ProvenanceEvent ---

class TestProvenanceEvent:

    def test_question_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:question:abc123",
        )
        assert event.event_type == "question"

    def test_exploration_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:exploration:abc123",
        )
        assert event.event_type == "exploration"

    def test_focus_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:focus:abc123",
        )
        assert event.event_type == "focus"

    def test_synthesis_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:synthesis:abc123",
        )
        assert event.event_type == "synthesis"

    def test_grounding_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:grounding:abc123",
        )
        assert event.event_type == "grounding"

    def test_session_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:agent:session:abc123",
        )
        assert event.event_type == "session"

    def test_iteration_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:agent:iteration:abc123:1",
        )
        assert event.event_type == "iteration"

    def test_observation_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:agent:observation:abc123:1",
        )
        assert event.event_type == "observation"

    def test_conclusion_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:agent:conclusion:abc123",
        )
        assert event.event_type == "conclusion"

    def test_decomposition_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:agent:decomposition:abc123",
        )
        assert event.event_type == "decomposition"

    def test_finding_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:agent:finding:abc123:0",
        )
        assert event.event_type == "finding"

    def test_plan_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:agent:plan:abc123",
        )
        assert event.event_type == "plan"

    def test_step_result_event_type(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:agent:step-result:abc123:0",
        )
        assert event.event_type == "step-result"

    def test_defaults(self):
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:question:abc123",
        )
        assert event.entity is None
        assert event.triples == []
        assert event.explain_graph == ""

    def test_with_triples(self):
        raw = [{"s": {"t": "i", "i": "urn:x"}, "p": {"t": "i", "i": "urn:y"}, "o": {"t": "l", "v": "z"}}]
        event = ProvenanceEvent(
            explain_id="urn:trustgraph:question:abc123",
            triples=raw,
        )
        assert len(event.triples) == 1


# --- Build ProvenanceEvent with entity parsing ---

class TestBuildProvenanceEvent:

    def _make_client(self):
        """Create a minimal WebSocketClient-like object with _build_provenance_event."""
        from trustgraph.api.socket_client import WebSocketClient
        # We can't instantiate WebSocketClient easily, so test the method logic directly
        return None

    def test_entity_parsed_from_wire_triples(self):
        """Test that wire-format triples are parsed into an ExplainEntity."""
        from trustgraph.api.explainability import ExplainEntity

        wire_triples = [
            {
                "s": {"t": "i", "i": "urn:trustgraph:question:abc123"},
                "p": {"t": "i", "i": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
                "o": {"t": "i", "i": "https://trustgraph.ai/ns/GraphRagQuestion"},
            },
            {
                "s": {"t": "i", "i": "urn:trustgraph:question:abc123"},
                "p": {"t": "i", "i": "https://trustgraph.ai/ns/query"},
                "o": {"t": "l", "v": "What is the internet?"},
            },
        ]

        # Parse triples the same way _build_provenance_event does
        parsed = []
        for t in wire_triples:
            s = t.get("s", {}).get("i", "")
            p = t.get("p", {}).get("i", "")
            o_term = t.get("o", {})
            if o_term.get("t") == "i":
                o = o_term.get("i", "")
            else:
                o = o_term.get("v", "")
            parsed.append((s, p, o))

        entity = ExplainEntity.from_triples(
            "urn:trustgraph:question:abc123", parsed
        )

        assert entity.entity_type == "question"
        assert entity.query == "What is the internet?"
        assert entity.question_type == "graph-rag"
