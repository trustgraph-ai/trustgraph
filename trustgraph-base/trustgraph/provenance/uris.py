"""
URI generation for provenance entities.

Document IDs are already IRIs (e.g., https://trustgraph.ai/doc/abc123).
Child entities (pages, chunks) append path segments to the parent IRI:
- Document:  {doc_iri} (as provided)
- Page:      {doc_iri}/p{page_number}
- Chunk:     {page_iri}/c{chunk_index} (from page)
             {doc_iri}/c{chunk_index} (from text doc)
- Activity:  https://trustgraph.ai/activity/{uuid}
- Statement: https://trustgraph.ai/stmt/{uuid}
"""

import uuid
import urllib.parse

# Base URI prefix for generated URIs (activities, statements, agents)
TRUSTGRAPH_BASE = "https://trustgraph.ai"


def _encode_id(id_str: str) -> str:
    """URL-encode an ID component for safe inclusion in URIs."""
    return urllib.parse.quote(str(id_str), safe='')


def document_uri(doc_iri: str) -> str:
    """Return the document IRI as-is (already a full URI)."""
    return doc_iri


def page_uri(doc_iri: str, page_number: int) -> str:
    """Generate URI for a page by appending to document IRI."""
    return f"{doc_iri}/p{page_number}"


def chunk_uri_from_page(doc_iri: str, page_number: int, chunk_index: int) -> str:
    """Generate URI for a chunk extracted from a page."""
    return f"{doc_iri}/p{page_number}/c{chunk_index}"


def chunk_uri_from_doc(doc_iri: str, chunk_index: int) -> str:
    """Generate URI for a chunk extracted directly from a text document."""
    return f"{doc_iri}/c{chunk_index}"


def activity_uri(activity_id: str = None) -> str:
    """Generate URI for a PROV-O activity. Auto-generates UUID if not provided."""
    if activity_id is None:
        activity_id = str(uuid.uuid4())
    return f"{TRUSTGRAPH_BASE}/activity/{_encode_id(activity_id)}"


def statement_uri(stmt_id: str = None) -> str:
    """Generate URI for a reified statement. Auto-generates UUID if not provided."""
    if stmt_id is None:
        stmt_id = str(uuid.uuid4())
    return f"{TRUSTGRAPH_BASE}/stmt/{_encode_id(stmt_id)}"


def agent_uri(component_name: str) -> str:
    """Generate URI for a TrustGraph component agent."""
    return f"{TRUSTGRAPH_BASE}/agent/{_encode_id(component_name)}"


# Query-time provenance URIs
# These URIs use the urn:trustgraph: namespace to distinguish query-time
# provenance from extraction-time provenance (which uses https://trustgraph.ai/)
#
# Terminology:
#   Question    - What was asked, the anchor for everything
#   Exploration - Casting wide, what do we know about this space
#   Focus       - Closing down, what's actually relevant here
#   Synthesis   - Weaving the relevant pieces into an answer

def question_uri(session_id: str = None) -> str:
    """
    Generate URI for a question activity.

    Args:
        session_id: Optional UUID string. Auto-generates if not provided.

    Returns:
        URN in format: urn:trustgraph:question:{uuid}
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    return f"urn:trustgraph:question:{session_id}"


def exploration_uri(session_id: str) -> str:
    """
    Generate URI for an exploration entity (edges retrieved from subgraph).

    Args:
        session_id: The session UUID (same as question_uri).

    Returns:
        URN in format: urn:trustgraph:prov:exploration:{uuid}
    """
    return f"urn:trustgraph:prov:exploration:{session_id}"


def focus_uri(session_id: str) -> str:
    """
    Generate URI for a focus entity (selected edges with reasoning).

    Args:
        session_id: The session UUID (same as question_uri).

    Returns:
        URN in format: urn:trustgraph:prov:focus:{uuid}
    """
    return f"urn:trustgraph:prov:focus:{session_id}"


def synthesis_uri(session_id: str) -> str:
    """
    Generate URI for a synthesis entity (final answer text).

    Args:
        session_id: The session UUID (same as question_uri).

    Returns:
        URN in format: urn:trustgraph:prov:synthesis:{uuid}
    """
    return f"urn:trustgraph:prov:synthesis:{session_id}"


def edge_selection_uri(session_id: str, edge_index: int) -> str:
    """
    Generate URI for an edge selection item (links edge to reasoning).

    Args:
        session_id: The session UUID.
        edge_index: Index of this edge in the selection (0-based).

    Returns:
        URN in format: urn:trustgraph:prov:edge:{uuid}:{index}
    """
    return f"urn:trustgraph:prov:edge:{session_id}:{edge_index}"


# Agent provenance URIs
# These URIs use the urn:trustgraph:agent: namespace to distinguish agent
# provenance from GraphRAG question provenance

def agent_session_uri(session_id: str = None) -> str:
    """
    Generate URI for an agent session.

    Args:
        session_id: Optional UUID string. Auto-generates if not provided.

    Returns:
        URN in format: urn:trustgraph:agent:{uuid}
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    return f"urn:trustgraph:agent:{session_id}"


def agent_iteration_uri(session_id: str, iteration_num: int) -> str:
    """
    Generate URI for an agent iteration.

    Args:
        session_id: The session UUID.
        iteration_num: 1-based iteration number.

    Returns:
        URN in format: urn:trustgraph:agent:{uuid}/i{num}
    """
    return f"urn:trustgraph:agent:{session_id}/i{iteration_num}"


def agent_final_uri(session_id: str) -> str:
    """
    Generate URI for an agent final answer.

    Args:
        session_id: The session UUID.

    Returns:
        URN in format: urn:trustgraph:agent:{uuid}/final
    """
    return f"urn:trustgraph:agent:{session_id}/final"
