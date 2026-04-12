"""
URI generation for provenance entities.

Document IDs are externally provided (e.g., https://trustgraph.ai/doc/abc123).
Child entities (pages, chunks) use UUID-based URNs:
- Document:  {doc_iri} (as provided, not generated here)
- Page:      urn:page:{uuid}
- Section:   urn:section:{uuid}
- Chunk:     urn:chunk:{uuid}
- Image:     urn:image:{uuid}
- Activity:  https://trustgraph.ai/activity/{uuid}
- Subgraph:  https://trustgraph.ai/subgraph/{uuid}
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


def page_uri() -> str:
    """Generate a unique URI for a page."""
    return f"urn:page:{uuid.uuid4()}"


def section_uri() -> str:
    """Generate a unique URI for a document section."""
    return f"urn:section:{uuid.uuid4()}"


def chunk_uri() -> str:
    """Generate a unique URI for a chunk."""
    return f"urn:chunk:{uuid.uuid4()}"


def image_uri() -> str:
    """Generate a unique URI for an image."""
    return f"urn:image:{uuid.uuid4()}"


def activity_uri(activity_id: str = None) -> str:
    """Generate URI for a PROV-O activity. Auto-generates UUID if not provided."""
    if activity_id is None:
        activity_id = str(uuid.uuid4())
    return f"{TRUSTGRAPH_BASE}/activity/{_encode_id(activity_id)}"


def subgraph_uri(subgraph_id: str = None) -> str:
    """Generate URI for an extraction subgraph. Auto-generates UUID if not provided."""
    if subgraph_id is None:
        subgraph_id = str(uuid.uuid4())
    return f"{TRUSTGRAPH_BASE}/subgraph/{_encode_id(subgraph_id)}"


def agent_uri(component_name: str) -> str:
    """Generate URI for a TrustGraph component agent."""
    return f"{TRUSTGRAPH_BASE}/agent/{_encode_id(component_name)}"


# Query-time provenance URIs
# These URIs use the urn:trustgraph: namespace to distinguish query-time
# provenance from extraction-time provenance (which uses https://trustgraph.ai/)
#
# Terminology:
#   Question    - What was asked, the anchor for everything
#   Grounding   - Decomposing the question into concepts
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


def grounding_uri(session_id: str) -> str:
    """
    Generate URI for a grounding entity (concept decomposition of query).

    Args:
        session_id: The session UUID (same as question_uri).

    Returns:
        URN in format: urn:trustgraph:prov:grounding:{uuid}
    """
    return f"urn:trustgraph:prov:grounding:{session_id}"


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


def agent_thought_uri(session_id: str, iteration_num: int) -> str:
    """
    Generate URI for an agent thought sub-entity.

    Args:
        session_id: The session UUID.
        iteration_num: 1-based iteration number.

    Returns:
        URN in format: urn:trustgraph:agent:{uuid}/i{num}/thought
    """
    return f"urn:trustgraph:agent:{session_id}/i{iteration_num}/thought"


def agent_observation_uri(session_id: str, iteration_num: int) -> str:
    """
    Generate URI for an agent observation sub-entity.

    Args:
        session_id: The session UUID.
        iteration_num: 1-based iteration number.

    Returns:
        URN in format: urn:trustgraph:agent:{uuid}/i{num}/observation
    """
    return f"urn:trustgraph:agent:{session_id}/i{iteration_num}/observation"


def agent_final_uri(session_id: str) -> str:
    """
    Generate URI for an agent final answer.

    Args:
        session_id: The session UUID.

    Returns:
        URN in format: urn:trustgraph:agent:{uuid}/final
    """
    return f"urn:trustgraph:agent:{session_id}/final"


def agent_decomposition_uri(session_id: str) -> str:
    """Generate URI for a supervisor decomposition step."""
    return f"urn:trustgraph:agent:{session_id}/decompose"


def agent_finding_uri(session_id: str, index: int) -> str:
    """Generate URI for a subagent finding."""
    return f"urn:trustgraph:agent:{session_id}/finding/{index}"


def agent_plan_uri(session_id: str) -> str:
    """Generate URI for a plan-then-execute plan."""
    return f"urn:trustgraph:agent:{session_id}/plan"


def agent_step_result_uri(session_id: str, index: int) -> str:
    """Generate URI for a plan step result."""
    return f"urn:trustgraph:agent:{session_id}/step/{index}"


def agent_synthesis_uri(session_id: str) -> str:
    """Generate URI for a synthesis answer."""
    return f"urn:trustgraph:agent:{session_id}/synthesis"


# Document RAG provenance URIs
# These URIs use the urn:trustgraph:docrag: namespace to distinguish
# document RAG provenance from graph RAG provenance

def docrag_question_uri(session_id: str = None) -> str:
    """
    Generate URI for a document RAG question activity.

    Args:
        session_id: Optional UUID string. Auto-generates if not provided.

    Returns:
        URN in format: urn:trustgraph:docrag:{uuid}
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    return f"urn:trustgraph:docrag:{session_id}"


def docrag_grounding_uri(session_id: str) -> str:
    """
    Generate URI for a document RAG grounding entity (concept decomposition).

    Args:
        session_id: The session UUID.

    Returns:
        URN in format: urn:trustgraph:docrag:{uuid}/grounding
    """
    return f"urn:trustgraph:docrag:{session_id}/grounding"


def docrag_exploration_uri(session_id: str) -> str:
    """
    Generate URI for a document RAG exploration entity (chunks retrieved).

    Args:
        session_id: The session UUID.

    Returns:
        URN in format: urn:trustgraph:docrag:{uuid}/exploration
    """
    return f"urn:trustgraph:docrag:{session_id}/exploration"


def docrag_synthesis_uri(session_id: str) -> str:
    """
    Generate URI for a document RAG synthesis entity (final answer).

    Args:
        session_id: The session UUID.

    Returns:
        URN in format: urn:trustgraph:docrag:{uuid}/synthesis
    """
    return f"urn:trustgraph:docrag:{session_id}/synthesis"
