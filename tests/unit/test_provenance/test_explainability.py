"""
Tests for the explainability API (entity parsing, wire format conversion,
and ExplainabilityClient).
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.api.explainability import (
    EdgeSelection,
    ExplainEntity,
    Question,
    Grounding,
    Exploration,
    Focus,
    Synthesis,
    Reflection,
    Analysis,
    Conclusion,
    parse_edge_selection_triples,
    extract_term_value,
    wire_triples_to_tuples,
    ExplainabilityClient,
    TG_QUERY, TG_EDGE_COUNT, TG_SELECTED_EDGE, TG_EDGE, TG_REASONING,
    TG_DOCUMENT, TG_CHUNK_COUNT, TG_CONCEPT, TG_ENTITY,
    TG_THOUGHT, TG_ACTION, TG_ARGUMENTS, TG_OBSERVATION,
    TG_QUESTION, TG_GROUNDING, TG_EXPLORATION, TG_FOCUS, TG_SYNTHESIS,
    TG_ANALYSIS, TG_CONCLUSION,
    TG_REFLECTION_TYPE, TG_THOUGHT_TYPE, TG_OBSERVATION_TYPE,
    TG_GRAPH_RAG_QUESTION, TG_DOC_RAG_QUESTION, TG_AGENT_QUESTION,
    PROV_STARTED_AT_TIME, PROV_WAS_DERIVED_FROM, PROV_WAS_GENERATED_BY,
    RDF_TYPE, RDFS_LABEL,
)


# ---------------------------------------------------------------------------
# Entity from_triples parsing
# ---------------------------------------------------------------------------

class TestExplainEntityFromTriples:
    """Test ExplainEntity.from_triples dispatches to correct subclass."""

    def test_graphrag_question(self):
        triples = [
            ("urn:q:1", RDF_TYPE, TG_QUESTION),
            ("urn:q:1", RDF_TYPE, TG_GRAPH_RAG_QUESTION),
            ("urn:q:1", TG_QUERY, "What is AI?"),
            ("urn:q:1", PROV_STARTED_AT_TIME, "2024-01-01T00:00:00Z"),
        ]
        entity = ExplainEntity.from_triples("urn:q:1", triples)
        assert isinstance(entity, Question)
        assert entity.query == "What is AI?"
        assert entity.timestamp == "2024-01-01T00:00:00Z"
        assert entity.question_type == "graph-rag"

    def test_docrag_question(self):
        triples = [
            ("urn:q:2", RDF_TYPE, TG_QUESTION),
            ("urn:q:2", RDF_TYPE, TG_DOC_RAG_QUESTION),
            ("urn:q:2", TG_QUERY, "Find info"),
        ]
        entity = ExplainEntity.from_triples("urn:q:2", triples)
        assert isinstance(entity, Question)
        assert entity.question_type == "document-rag"

    def test_agent_question(self):
        triples = [
            ("urn:q:3", RDF_TYPE, TG_QUESTION),
            ("urn:q:3", RDF_TYPE, TG_AGENT_QUESTION),
            ("urn:q:3", TG_QUERY, "Agent query"),
        ]
        entity = ExplainEntity.from_triples("urn:q:3", triples)
        assert isinstance(entity, Question)
        assert entity.question_type == "agent"

    def test_grounding(self):
        triples = [
            ("urn:gnd:1", RDF_TYPE, TG_GROUNDING),
            ("urn:gnd:1", TG_CONCEPT, "machine learning"),
            ("urn:gnd:1", TG_CONCEPT, "neural networks"),
        ]
        entity = ExplainEntity.from_triples("urn:gnd:1", triples)
        assert isinstance(entity, Grounding)
        assert len(entity.concepts) == 2
        assert "machine learning" in entity.concepts
        assert "neural networks" in entity.concepts

    def test_exploration(self):
        triples = [
            ("urn:exp:1", RDF_TYPE, TG_EXPLORATION),
            ("urn:exp:1", TG_EDGE_COUNT, "15"),
        ]
        entity = ExplainEntity.from_triples("urn:exp:1", triples)
        assert isinstance(entity, Exploration)
        assert entity.edge_count == 15

    def test_exploration_with_chunk_count(self):
        triples = [
            ("urn:exp:2", RDF_TYPE, TG_EXPLORATION),
            ("urn:exp:2", TG_CHUNK_COUNT, "5"),
        ]
        entity = ExplainEntity.from_triples("urn:exp:2", triples)
        assert isinstance(entity, Exploration)
        assert entity.chunk_count == 5

    def test_exploration_with_entities(self):
        triples = [
            ("urn:exp:3", RDF_TYPE, TG_EXPLORATION),
            ("urn:exp:3", TG_EDGE_COUNT, "10"),
            ("urn:exp:3", TG_ENTITY, "urn:e:machine-learning"),
            ("urn:exp:3", TG_ENTITY, "urn:e:neural-networks"),
        ]
        entity = ExplainEntity.from_triples("urn:exp:3", triples)
        assert isinstance(entity, Exploration)
        assert len(entity.entities) == 2

    def test_exploration_invalid_count(self):
        triples = [
            ("urn:exp:3", RDF_TYPE, TG_EXPLORATION),
            ("urn:exp:3", TG_EDGE_COUNT, "not-a-number"),
        ]
        entity = ExplainEntity.from_triples("urn:exp:3", triples)
        assert isinstance(entity, Exploration)
        assert entity.edge_count == 0

    def test_focus(self):
        triples = [
            ("urn:foc:1", RDF_TYPE, TG_FOCUS),
            ("urn:foc:1", TG_SELECTED_EDGE, "urn:edge:1"),
            ("urn:foc:1", TG_SELECTED_EDGE, "urn:edge:2"),
        ]
        entity = ExplainEntity.from_triples("urn:foc:1", triples)
        assert isinstance(entity, Focus)
        assert len(entity.selected_edge_uris) == 2
        assert "urn:edge:1" in entity.selected_edge_uris
        assert "urn:edge:2" in entity.selected_edge_uris

    def test_synthesis_with_document(self):
        triples = [
            ("urn:syn:1", RDF_TYPE, TG_SYNTHESIS),
            ("urn:syn:1", TG_DOCUMENT, "urn:doc:answer-1"),
        ]
        entity = ExplainEntity.from_triples("urn:syn:1", triples)
        assert isinstance(entity, Synthesis)
        assert entity.document_uri == "urn:doc:answer-1"

    def test_synthesis_no_document(self):
        triples = [
            ("urn:syn:2", RDF_TYPE, TG_SYNTHESIS),
        ]
        entity = ExplainEntity.from_triples("urn:syn:2", triples)
        assert isinstance(entity, Synthesis)
        assert entity.document_uri == ""

    def test_reflection_thought(self):
        triples = [
            ("urn:ref:1", RDF_TYPE, TG_REFLECTION_TYPE),
            ("urn:ref:1", RDF_TYPE, TG_THOUGHT_TYPE),
            ("urn:ref:1", TG_DOCUMENT, "urn:doc:thought-1"),
        ]
        entity = ExplainEntity.from_triples("urn:ref:1", triples)
        assert isinstance(entity, Reflection)
        assert entity.reflection_type == "thought"
        assert entity.document_uri == "urn:doc:thought-1"

    def test_reflection_observation(self):
        triples = [
            ("urn:ref:2", RDF_TYPE, TG_REFLECTION_TYPE),
            ("urn:ref:2", RDF_TYPE, TG_OBSERVATION_TYPE),
            ("urn:ref:2", TG_DOCUMENT, "urn:doc:obs-1"),
        ]
        entity = ExplainEntity.from_triples("urn:ref:2", triples)
        assert isinstance(entity, Reflection)
        assert entity.reflection_type == "observation"
        assert entity.document_uri == "urn:doc:obs-1"

    def test_analysis(self):
        triples = [
            ("urn:ana:1", RDF_TYPE, TG_ANALYSIS),
            ("urn:ana:1", TG_ACTION, "graph-rag-query"),
            ("urn:ana:1", TG_ARGUMENTS, '{"query": "test"}'),
            ("urn:ana:1", TG_THOUGHT, "urn:ref:thought-1"),
            ("urn:ana:1", TG_OBSERVATION, "urn:ref:obs-1"),
        ]
        entity = ExplainEntity.from_triples("urn:ana:1", triples)
        assert isinstance(entity, Analysis)
        assert entity.action == "graph-rag-query"
        assert entity.arguments == '{"query": "test"}'
        assert entity.thought_uri == "urn:ref:thought-1"
        assert entity.observation_uri == "urn:ref:obs-1"

    def test_conclusion_with_document(self):
        triples = [
            ("urn:conc:1", RDF_TYPE, TG_CONCLUSION),
            ("urn:conc:1", TG_DOCUMENT, "urn:doc:final"),
        ]
        entity = ExplainEntity.from_triples("urn:conc:1", triples)
        assert isinstance(entity, Conclusion)
        assert entity.document_uri == "urn:doc:final"

    def test_conclusion_no_document(self):
        triples = [
            ("urn:conc:2", RDF_TYPE, TG_CONCLUSION),
        ]
        entity = ExplainEntity.from_triples("urn:conc:2", triples)
        assert isinstance(entity, Conclusion)
        assert entity.document_uri == ""

    def test_unknown_type(self):
        triples = [
            ("urn:x:1", RDF_TYPE, "http://example.com/UnknownType"),
        ]
        entity = ExplainEntity.from_triples("urn:x:1", triples)
        assert isinstance(entity, ExplainEntity)
        assert entity.entity_type == "unknown"


# ---------------------------------------------------------------------------
# parse_edge_selection_triples
# ---------------------------------------------------------------------------

class TestParseEdgeSelectionTriples:

    def test_with_edge_and_reasoning(self):
        triples = [
            ("urn:edge:1", TG_EDGE, {"s": "Alice", "p": "knows", "o": "Bob"}),
            ("urn:edge:1", TG_REASONING, "Alice and Bob are connected"),
        ]
        result = parse_edge_selection_triples(triples)
        assert isinstance(result, EdgeSelection)
        assert result.uri == "urn:edge:1"
        assert result.edge == {"s": "Alice", "p": "knows", "o": "Bob"}
        assert result.reasoning == "Alice and Bob are connected"

    def test_with_edge_only(self):
        triples = [
            ("urn:edge:2", TG_EDGE, {"s": "A", "p": "r", "o": "B"}),
        ]
        result = parse_edge_selection_triples(triples)
        assert result.edge is not None
        assert result.reasoning == ""

    def test_with_reasoning_only(self):
        triples = [
            ("urn:edge:3", TG_REASONING, "some reason"),
        ]
        result = parse_edge_selection_triples(triples)
        assert result.edge is None
        assert result.reasoning == "some reason"

    def test_empty_triples(self):
        result = parse_edge_selection_triples([])
        assert result.uri == ""
        assert result.edge is None
        assert result.reasoning == ""

    def test_edge_must_be_dict(self):
        """Non-dict values for TG_EDGE should not be treated as edges."""
        triples = [
            ("urn:edge:4", TG_EDGE, "not-a-dict"),
        ]
        result = parse_edge_selection_triples(triples)
        assert result.edge is None


# ---------------------------------------------------------------------------
# extract_term_value
# ---------------------------------------------------------------------------

class TestExtractTermValue:

    def test_iri_short_format(self):
        assert extract_term_value({"t": "i", "i": "urn:test"}) == "urn:test"

    def test_iri_long_format(self):
        assert extract_term_value({"type": "i", "iri": "urn:test"}) == "urn:test"

    def test_literal_short_format(self):
        assert extract_term_value({"t": "l", "v": "hello"}) == "hello"

    def test_literal_long_format(self):
        assert extract_term_value({"type": "l", "value": "hello"}) == "hello"

    def test_quoted_triple(self):
        term = {
            "t": "t",
            "tr": {
                "s": {"t": "i", "i": "urn:s"},
                "p": {"t": "i", "i": "urn:p"},
                "o": {"t": "i", "i": "urn:o"},
            }
        }
        result = extract_term_value(term)
        assert result == {"s": "urn:s", "p": "urn:p", "o": "urn:o"}

    def test_quoted_triple_long_format(self):
        term = {
            "type": "t",
            "triple": {
                "s": {"type": "i", "iri": "urn:s"},
                "p": {"type": "i", "iri": "urn:p"},
                "o": {"type": "l", "value": "val"},
            }
        }
        result = extract_term_value(term)
        assert result == {"s": "urn:s", "p": "urn:p", "o": "val"}

    def test_unknown_type_fallback(self):
        result = extract_term_value({"t": "x", "i": "urn:fallback"})
        assert result == "urn:fallback"


# ---------------------------------------------------------------------------
# wire_triples_to_tuples
# ---------------------------------------------------------------------------

class TestWireTriplesToTuples:

    def test_basic_conversion(self):
        wire = [
            {
                "s": {"t": "i", "i": "urn:s1"},
                "p": {"t": "i", "i": "urn:p1"},
                "o": {"t": "l", "v": "value1"},
            },
        ]
        result = wire_triples_to_tuples(wire)
        assert len(result) == 1
        assert result[0] == ("urn:s1", "urn:p1", "value1")

    def test_multiple_triples(self):
        wire = [
            {
                "s": {"t": "i", "i": "urn:s1"},
                "p": {"t": "i", "i": "urn:p1"},
                "o": {"t": "l", "v": "v1"},
            },
            {
                "s": {"t": "i", "i": "urn:s2"},
                "p": {"t": "i", "i": "urn:p2"},
                "o": {"t": "i", "i": "urn:o2"},
            },
        ]
        result = wire_triples_to_tuples(wire)
        assert len(result) == 2
        assert result[0] == ("urn:s1", "urn:p1", "v1")
        assert result[1] == ("urn:s2", "urn:p2", "urn:o2")

    def test_empty_list(self):
        assert wire_triples_to_tuples([]) == []

    def test_missing_fields(self):
        wire = [{"s": {}, "p": {}, "o": {}}]
        result = wire_triples_to_tuples(wire)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# ExplainabilityClient
# ---------------------------------------------------------------------------

def _make_wire_triples(tuples):
    """Convert (s, p, o) tuples to wire format for mocking."""
    result = []
    for s, p, o in tuples:
        entry = {
            "s": {"t": "i", "i": s},
            "p": {"t": "i", "i": p},
        }
        if o.startswith("urn:") or o.startswith("http"):
            entry["o"] = {"t": "i", "i": o}
        else:
            entry["o"] = {"t": "l", "v": o}
        result.append(entry)
    return result


class TestExplainabilityClientFetchEntity:

    def test_fetch_question_entity(self):
        wire = _make_wire_triples([
            ("urn:q:1", RDF_TYPE, TG_QUESTION),
            ("urn:q:1", RDF_TYPE, TG_GRAPH_RAG_QUESTION),
            ("urn:q:1", TG_QUERY, "What is AI?"),
            ("urn:q:1", PROV_STARTED_AT_TIME, "2024-01-01T00:00:00Z"),
        ])

        mock_flow = MagicMock()
        # Return same results twice for quiescence
        mock_flow.triples_query.side_effect = [wire, wire]

        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        entity = client.fetch_entity("urn:q:1", graph="urn:graph:retrieval")

        assert isinstance(entity, Question)
        assert entity.query == "What is AI?"
        assert entity.question_type == "graph-rag"

    def test_fetch_returns_none_when_no_data(self):
        mock_flow = MagicMock()
        mock_flow.triples_query.return_value = []

        client = ExplainabilityClient(mock_flow, retry_delay=0.0, max_retries=2)
        entity = client.fetch_entity("urn:nonexistent")

        assert entity is None

    def test_fetch_retries_on_empty_results(self):
        wire = _make_wire_triples([
            ("urn:q:1", RDF_TYPE, TG_QUESTION),
            ("urn:q:1", RDF_TYPE, TG_GRAPH_RAG_QUESTION),
            ("urn:q:1", TG_QUERY, "Q"),
        ])

        mock_flow = MagicMock()
        # Empty, then data, then same data (stable)
        mock_flow.triples_query.side_effect = [[], wire, wire]

        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        entity = client.fetch_entity("urn:q:1")

        assert isinstance(entity, Question)
        assert mock_flow.triples_query.call_count == 3


class TestExplainabilityClientResolveLabel:

    def test_resolve_label_found(self):
        mock_flow = MagicMock()
        mock_flow.triples_query.return_value = _make_wire_triples([
            ("urn:entity:1", RDFS_LABEL, "Entity One"),
        ])

        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        label = client.resolve_label("urn:entity:1")
        assert label == "Entity One"

    def test_resolve_label_not_found(self):
        mock_flow = MagicMock()
        mock_flow.triples_query.return_value = []

        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        label = client.resolve_label("urn:entity:1")
        assert label == "urn:entity:1"

    def test_resolve_label_cached(self):
        mock_flow = MagicMock()
        mock_flow.triples_query.return_value = _make_wire_triples([
            ("urn:entity:1", RDFS_LABEL, "Entity One"),
        ])

        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        client.resolve_label("urn:entity:1")
        client.resolve_label("urn:entity:1")

        # Only one query should be made
        assert mock_flow.triples_query.call_count == 1

    def test_resolve_label_non_uri(self):
        mock_flow = MagicMock()
        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        assert client.resolve_label("plain text") == "plain text"
        assert client.resolve_label("") == ""
        mock_flow.triples_query.assert_not_called()

    def test_resolve_edge_labels(self):
        mock_flow = MagicMock()

        def mock_query(s=None, p=None, **kwargs):
            labels = {
                "urn:e:Alice": "Alice",
                "urn:r:knows": "knows",
                "urn:e:Bob": "Bob",
            }
            if s in labels:
                return _make_wire_triples([(s, RDFS_LABEL, labels[s])])
            return []

        mock_flow.triples_query.side_effect = mock_query

        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        s, p, o = client.resolve_edge_labels(
            {"s": "urn:e:Alice", "p": "urn:r:knows", "o": "urn:e:Bob"}
        )
        assert s == "Alice"
        assert p == "knows"
        assert o == "Bob"


class TestExplainabilityClientContentFetching:

    def test_fetch_document_content_from_librarian(self):
        mock_flow = MagicMock()
        mock_api = MagicMock()
        mock_library = MagicMock()
        mock_api.library.return_value = mock_library
        mock_library.get_document_content.return_value = b"librarian content"

        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        result = client.fetch_document_content(
            "urn:document:abc123", api=mock_api
        )
        assert result == "librarian content"

    def test_fetch_document_content_truncated(self):
        mock_flow = MagicMock()
        mock_api = MagicMock()
        mock_library = MagicMock()
        mock_api.library.return_value = mock_library
        mock_library.get_document_content.return_value = b"x" * 20000

        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        result = client.fetch_document_content(
            "urn:doc:1", api=mock_api, max_content=100
        )
        assert len(result) < 20000
        assert result.endswith("... [truncated]")

    def test_fetch_document_content_empty_uri(self):
        mock_flow = MagicMock()
        mock_api = MagicMock()

        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        result = client.fetch_document_content("", api=mock_api)
        assert result == ""


class TestExplainabilityClientDetectSessionType:

    def test_detect_agent_from_uri(self):
        mock_flow = MagicMock()
        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        assert client.detect_session_type("urn:trustgraph:agent:abc") == "agent"

    def test_detect_graphrag_from_uri(self):
        mock_flow = MagicMock()
        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        assert client.detect_session_type("urn:trustgraph:question:abc") == "graphrag"

    def test_detect_docrag_from_uri(self):
        mock_flow = MagicMock()
        client = ExplainabilityClient(mock_flow, retry_delay=0.0)
        assert client.detect_session_type("urn:trustgraph:docrag:abc") == "docrag"
