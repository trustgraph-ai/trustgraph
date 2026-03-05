"""
URI generation for provenance entities.

URI patterns:
- Document:  https://trustgraph.ai/doc/{doc_id}
- Page:      https://trustgraph.ai/page/{doc_id}/p{page_number}
- Chunk:     https://trustgraph.ai/chunk/{doc_id}/p{page}/c{chunk} (from page)
             https://trustgraph.ai/chunk/{doc_id}/c{chunk} (from text doc)
- Activity:  https://trustgraph.ai/activity/{uuid}
- Statement: https://trustgraph.ai/stmt/{uuid}
"""

import uuid
import urllib.parse

# Base URI prefix
TRUSTGRAPH_BASE = "https://trustgraph.ai"


def _encode_id(id_str: str) -> str:
    """URL-encode an ID component for safe inclusion in URIs."""
    return urllib.parse.quote(str(id_str), safe='')


def document_uri(doc_id: str) -> str:
    """Generate URI for a source document."""
    return f"{TRUSTGRAPH_BASE}/doc/{_encode_id(doc_id)}"


def page_uri(doc_id: str, page_number: int) -> str:
    """Generate URI for a page extracted from a document."""
    return f"{TRUSTGRAPH_BASE}/page/{_encode_id(doc_id)}/p{page_number}"


def chunk_uri_from_page(doc_id: str, page_number: int, chunk_index: int) -> str:
    """Generate URI for a chunk extracted from a page."""
    return f"{TRUSTGRAPH_BASE}/chunk/{_encode_id(doc_id)}/p{page_number}/c{chunk_index}"


def chunk_uri_from_doc(doc_id: str, chunk_index: int) -> str:
    """Generate URI for a chunk extracted directly from a text document."""
    return f"{TRUSTGRAPH_BASE}/chunk/{_encode_id(doc_id)}/c{chunk_index}"


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
