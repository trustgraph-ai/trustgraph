"""
Tests for provenance URI generation functions.
"""

import pytest
from unittest.mock import patch

from trustgraph.provenance.uris import (
    TRUSTGRAPH_BASE,
    _encode_id,
    document_uri,
    page_uri,
    chunk_uri_from_page,
    chunk_uri_from_doc,
    activity_uri,
    subgraph_uri,
    agent_uri,
    question_uri,
    exploration_uri,
    focus_uri,
    synthesis_uri,
    edge_selection_uri,
    agent_session_uri,
    agent_iteration_uri,
    agent_final_uri,
    docrag_question_uri,
    docrag_exploration_uri,
    docrag_synthesis_uri,
)


class TestEncodeId:
    """Tests for the _encode_id helper."""

    def test_plain_string(self):
        assert _encode_id("abc123") == "abc123"

    def test_string_with_spaces(self):
        assert _encode_id("hello world") == "hello%20world"

    def test_string_with_slashes(self):
        assert _encode_id("a/b/c") == "a%2Fb%2Fc"

    def test_integer_input(self):
        assert _encode_id(42) == "42"

    def test_empty_string(self):
        assert _encode_id("") == ""

    def test_special_characters(self):
        result = _encode_id("name@domain.com")
        assert "@" not in result or result == "name%40domain.com"


class TestDocumentUris:
    """Tests for document, page, and chunk URI generation."""

    def test_document_uri_passthrough(self):
        iri = "https://example.com/doc/123"
        assert document_uri(iri) == iri

    def test_page_uri_format(self):
        result = page_uri("https://example.com/doc/123", 5)
        assert result == "https://example.com/doc/123/p5"

    def test_page_uri_page_zero(self):
        result = page_uri("https://example.com/doc/123", 0)
        assert result == "https://example.com/doc/123/p0"

    def test_chunk_uri_from_page_format(self):
        result = chunk_uri_from_page("https://example.com/doc/123", 2, 3)
        assert result == "https://example.com/doc/123/p2/c3"

    def test_chunk_uri_from_doc_format(self):
        result = chunk_uri_from_doc("https://example.com/doc/123", 7)
        assert result == "https://example.com/doc/123/c7"

    def test_page_uri_preserves_doc_iri(self):
        doc = "urn:isbn:978-3-16-148410-0"
        result = page_uri(doc, 1)
        assert result.startswith(doc)

    def test_chunk_from_page_hierarchy(self):
        """Chunk URI should contain both page and chunk identifiers."""
        result = chunk_uri_from_page("https://example.com/doc", 3, 5)
        assert "/p3/" in result
        assert result.endswith("/c5")


class TestActivityAndSubgraphUris:
    """Tests for activity_uri, subgraph_uri, and agent_uri."""

    def test_activity_uri_with_id(self):
        result = activity_uri("my-activity-id")
        assert result == f"{TRUSTGRAPH_BASE}/activity/my-activity-id"

    def test_activity_uri_auto_generates_uuid(self):
        result = activity_uri()
        assert result.startswith(f"{TRUSTGRAPH_BASE}/activity/")
        # UUID part should be non-empty
        uuid_part = result.split("/activity/")[1]
        assert len(uuid_part) > 0

    def test_activity_uri_unique_uuids(self):
        r1 = activity_uri()
        r2 = activity_uri()
        assert r1 != r2

    def test_activity_uri_encodes_special_chars(self):
        result = activity_uri("id with spaces")
        assert "id%20with%20spaces" in result

    def test_subgraph_uri_with_id(self):
        result = subgraph_uri("sg-123")
        assert result == f"{TRUSTGRAPH_BASE}/subgraph/sg-123"

    def test_subgraph_uri_auto_generates_uuid(self):
        result = subgraph_uri()
        assert result.startswith(f"{TRUSTGRAPH_BASE}/subgraph/")
        uuid_part = result.split("/subgraph/")[1]
        assert len(uuid_part) > 0

    def test_subgraph_uri_unique_uuids(self):
        r1 = subgraph_uri()
        r2 = subgraph_uri()
        assert r1 != r2

    def test_agent_uri_format(self):
        result = agent_uri("pdf-extractor")
        assert result == f"{TRUSTGRAPH_BASE}/agent/pdf-extractor"

    def test_agent_uri_encodes_special_chars(self):
        result = agent_uri("my component")
        assert "my%20component" in result


class TestGraphRagQueryUris:
    """Tests for GraphRAG query-time provenance URIs."""

    FIXED_UUID = "550e8400-e29b-41d4-a716-446655440000"

    def test_question_uri_with_session_id(self):
        result = question_uri(self.FIXED_UUID)
        assert result == f"urn:trustgraph:question:{self.FIXED_UUID}"

    def test_question_uri_auto_generates(self):
        result = question_uri()
        assert result.startswith("urn:trustgraph:question:")
        uuid_part = result.split("urn:trustgraph:question:")[1]
        assert len(uuid_part) > 0

    def test_question_uri_unique(self):
        r1 = question_uri()
        r2 = question_uri()
        assert r1 != r2

    def test_exploration_uri_format(self):
        result = exploration_uri(self.FIXED_UUID)
        assert result == f"urn:trustgraph:prov:exploration:{self.FIXED_UUID}"

    def test_focus_uri_format(self):
        result = focus_uri(self.FIXED_UUID)
        assert result == f"urn:trustgraph:prov:focus:{self.FIXED_UUID}"

    def test_synthesis_uri_format(self):
        result = synthesis_uri(self.FIXED_UUID)
        assert result == f"urn:trustgraph:prov:synthesis:{self.FIXED_UUID}"

    def test_edge_selection_uri_format(self):
        result = edge_selection_uri(self.FIXED_UUID, 3)
        assert result == f"urn:trustgraph:prov:edge:{self.FIXED_UUID}:3"

    def test_edge_selection_uri_zero_index(self):
        result = edge_selection_uri(self.FIXED_UUID, 0)
        assert result.endswith(":0")

    def test_session_uris_share_session_id(self):
        """All URIs for a session should contain the same session ID."""
        sid = self.FIXED_UUID
        q = question_uri(sid)
        e = exploration_uri(sid)
        f = focus_uri(sid)
        s = synthesis_uri(sid)
        for uri in [q, e, f, s]:
            assert sid in uri


class TestAgentProvenanceUris:
    """Tests for agent provenance URIs."""

    FIXED_UUID = "661e8400-e29b-41d4-a716-446655440000"

    def test_agent_session_uri_with_id(self):
        result = agent_session_uri(self.FIXED_UUID)
        assert result == f"urn:trustgraph:agent:{self.FIXED_UUID}"

    def test_agent_session_uri_auto_generates(self):
        result = agent_session_uri()
        assert result.startswith("urn:trustgraph:agent:")

    def test_agent_session_uri_unique(self):
        r1 = agent_session_uri()
        r2 = agent_session_uri()
        assert r1 != r2

    def test_agent_iteration_uri_format(self):
        result = agent_iteration_uri(self.FIXED_UUID, 1)
        assert result == f"urn:trustgraph:agent:{self.FIXED_UUID}/i1"

    def test_agent_iteration_uri_numbering(self):
        r1 = agent_iteration_uri(self.FIXED_UUID, 1)
        r2 = agent_iteration_uri(self.FIXED_UUID, 2)
        assert r1 != r2
        assert r1.endswith("/i1")
        assert r2.endswith("/i2")

    def test_agent_final_uri_format(self):
        result = agent_final_uri(self.FIXED_UUID)
        assert result == f"urn:trustgraph:agent:{self.FIXED_UUID}/final"

    def test_agent_uris_share_session_id(self):
        sid = self.FIXED_UUID
        session = agent_session_uri(sid)
        iteration = agent_iteration_uri(sid, 1)
        final = agent_final_uri(sid)
        for uri in [session, iteration, final]:
            assert sid in uri


class TestDocRagProvenanceUris:
    """Tests for Document RAG provenance URIs."""

    FIXED_UUID = "772e8400-e29b-41d4-a716-446655440000"

    def test_docrag_question_uri_with_id(self):
        result = docrag_question_uri(self.FIXED_UUID)
        assert result == f"urn:trustgraph:docrag:{self.FIXED_UUID}"

    def test_docrag_question_uri_auto_generates(self):
        result = docrag_question_uri()
        assert result.startswith("urn:trustgraph:docrag:")

    def test_docrag_question_uri_unique(self):
        r1 = docrag_question_uri()
        r2 = docrag_question_uri()
        assert r1 != r2

    def test_docrag_exploration_uri_format(self):
        result = docrag_exploration_uri(self.FIXED_UUID)
        assert result == f"urn:trustgraph:docrag:{self.FIXED_UUID}/exploration"

    def test_docrag_synthesis_uri_format(self):
        result = docrag_synthesis_uri(self.FIXED_UUID)
        assert result == f"urn:trustgraph:docrag:{self.FIXED_UUID}/synthesis"

    def test_docrag_uris_share_session_id(self):
        sid = self.FIXED_UUID
        q = docrag_question_uri(sid)
        e = docrag_exploration_uri(sid)
        s = docrag_synthesis_uri(sid)
        for uri in [q, e, s]:
            assert sid in uri


class TestUriNamespaceIsolation:
    """Verify that different provenance types use distinct URI namespaces."""

    FIXED_UUID = "883e8400-e29b-41d4-a716-446655440000"

    def test_graphrag_vs_agent_namespace(self):
        graphrag = question_uri(self.FIXED_UUID)
        agent = agent_session_uri(self.FIXED_UUID)
        assert graphrag != agent
        assert "question" in graphrag
        assert "agent" in agent

    def test_graphrag_vs_docrag_namespace(self):
        graphrag = question_uri(self.FIXED_UUID)
        docrag = docrag_question_uri(self.FIXED_UUID)
        assert graphrag != docrag

    def test_agent_vs_docrag_namespace(self):
        agent = agent_session_uri(self.FIXED_UUID)
        docrag = docrag_question_uri(self.FIXED_UUID)
        assert agent != docrag

    def test_extraction_vs_query_namespace(self):
        """Extraction URIs use https://, query URIs use urn:."""
        ext = activity_uri(self.FIXED_UUID)
        query = question_uri(self.FIXED_UUID)
        assert ext.startswith("https://")
        assert query.startswith("urn:")
