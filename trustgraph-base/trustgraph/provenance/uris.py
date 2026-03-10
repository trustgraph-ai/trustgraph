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

def query_session_uri(session_id: str = None) -> str:
    """
    Generate URI for a query session activity.

    Args:
        session_id: Optional UUID string. Auto-generates if not provided.

    Returns:
        URN in format: urn:trustgraph:session:{uuid}
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    return f"urn:trustgraph:session:{session_id}"


def retrieval_uri(session_id: str) -> str:
    """
    Generate URI for a retrieval entity (edges retrieved from subgraph).

    Args:
        session_id: The session UUID (same as query_session_uri).

    Returns:
        URN in format: urn:trustgraph:prov:retrieval:{uuid}
    """
    return f"urn:trustgraph:prov:retrieval:{session_id}"


def selection_uri(session_id: str) -> str:
    """
    Generate URI for a selection entity (selected edges with reasoning).

    Args:
        session_id: The session UUID (same as query_session_uri).

    Returns:
        URN in format: urn:trustgraph:prov:selection:{uuid}
    """
    return f"urn:trustgraph:prov:selection:{session_id}"


def answer_uri(session_id: str) -> str:
    """
    Generate URI for an answer entity (final synthesis text).

    Args:
        session_id: The session UUID (same as query_session_uri).

    Returns:
        URN in format: urn:trustgraph:prov:answer:{uuid}
    """
    return f"urn:trustgraph:prov:answer:{session_id}"


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
