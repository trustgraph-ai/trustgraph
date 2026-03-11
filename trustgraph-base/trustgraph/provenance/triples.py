"""
Helper functions to build PROV-O triples for extraction-time provenance.
"""

from datetime import datetime
from typing import List, Optional

from .. schema import Triple, Term, IRI, LITERAL, TRIPLE

from . namespaces import (
    RDF_TYPE, RDFS_LABEL,
    PROV_ENTITY, PROV_ACTIVITY, PROV_AGENT,
    PROV_WAS_DERIVED_FROM, PROV_WAS_GENERATED_BY,
    PROV_USED, PROV_WAS_ASSOCIATED_WITH, PROV_STARTED_AT_TIME,
    DC_TITLE, DC_SOURCE, DC_DATE, DC_CREATOR,
    TG_PAGE_COUNT, TG_MIME_TYPE, TG_PAGE_NUMBER,
    TG_CHUNK_INDEX, TG_CHAR_OFFSET, TG_CHAR_LENGTH,
    TG_CHUNK_SIZE, TG_CHUNK_OVERLAP, TG_COMPONENT_VERSION,
    TG_LLM_MODEL, TG_ONTOLOGY, TG_REIFIES,
    # Query-time provenance predicates
    TG_QUERY, TG_EDGE_COUNT, TG_SELECTED_EDGE, TG_EDGE, TG_REASONING, TG_CONTENT,
    TG_DOCUMENT,
    # Explainability entity types
    TG_QUESTION, TG_EXPLORATION, TG_FOCUS, TG_SYNTHESIS,
)

from . uris import activity_uri, agent_uri, edge_selection_uri


def set_graph(triples: List[Triple], graph: str) -> List[Triple]:
    """
    Set the named graph on a list of triples.

    This creates new Triple objects with the graph field set,
    leaving the original triples unchanged.

    Args:
        triples: List of Triple objects
        graph: Named graph URI (e.g., "urn:graph:retrieval")

    Returns:
        List of Triple objects with graph field set
    """
    return [
        Triple(s=t.s, p=t.p, o=t.o, g=graph)
        for t in triples
    ]


def _iri(uri: str) -> Term:
    """Create an IRI term."""
    return Term(type=IRI, iri=uri)


def _literal(value) -> Term:
    """Create a literal term."""
    return Term(type=LITERAL, value=str(value))


def _triple(s: str, p: str, o_term: Term) -> Triple:
    """Create a triple with IRI subject and predicate."""
    return Triple(s=_iri(s), p=_iri(p), o=o_term)


def document_triples(
    doc_uri: str,
    title: Optional[str] = None,
    source: Optional[str] = None,
    date: Optional[str] = None,
    creator: Optional[str] = None,
    page_count: Optional[int] = None,
    mime_type: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for a source document entity.

    Args:
        doc_uri: The document URI (from uris.document_uri)
        title: Document title
        source: Source URL/path
        date: Document date
        creator: Author/creator
        page_count: Number of pages (for PDFs)
        mime_type: MIME type

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(doc_uri, RDF_TYPE, _iri(PROV_ENTITY)),
    ]

    if title:
        triples.append(_triple(doc_uri, DC_TITLE, _literal(title)))
        triples.append(_triple(doc_uri, RDFS_LABEL, _literal(title)))

    if source:
        triples.append(_triple(doc_uri, DC_SOURCE, _iri(source)))

    if date:
        triples.append(_triple(doc_uri, DC_DATE, _literal(date)))

    if creator:
        triples.append(_triple(doc_uri, DC_CREATOR, _literal(creator)))

    if page_count is not None:
        triples.append(_triple(doc_uri, TG_PAGE_COUNT, _literal(page_count)))

    if mime_type:
        triples.append(_triple(doc_uri, TG_MIME_TYPE, _literal(mime_type)))

    return triples


def derived_entity_triples(
    entity_uri: str,
    parent_uri: str,
    component_name: str,
    component_version: str,
    label: Optional[str] = None,
    page_number: Optional[int] = None,
    chunk_index: Optional[int] = None,
    char_offset: Optional[int] = None,
    char_length: Optional[int] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for a derived entity (page or chunk) with full PROV-O provenance.

    Creates:
    - Entity declaration
    - wasDerivedFrom relationship to parent
    - Activity for the extraction
    - Agent for the component

    Args:
        entity_uri: URI of the derived entity (page or chunk)
        parent_uri: URI of the parent entity
        component_name: Name of TG component (e.g., "pdf-extractor", "chunker")
        component_version: Version of the component
        label: Human-readable label
        page_number: Page number (for pages)
        chunk_index: Chunk index (for chunks)
        char_offset: Character offset in parent (for chunks)
        char_length: Character length (for chunks)
        chunk_size: Configured chunk size (for chunking activity)
        chunk_overlap: Configured chunk overlap (for chunking activity)
        timestamp: ISO timestamp (defaults to now)

    Returns:
        List of Triple objects
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"

    act_uri = activity_uri()
    agt_uri = agent_uri(component_name)

    triples = [
        # Entity declaration
        _triple(entity_uri, RDF_TYPE, _iri(PROV_ENTITY)),

        # Derivation from parent
        _triple(entity_uri, PROV_WAS_DERIVED_FROM, _iri(parent_uri)),

        # Generation by activity
        _triple(entity_uri, PROV_WAS_GENERATED_BY, _iri(act_uri)),

        # Activity declaration
        _triple(act_uri, RDF_TYPE, _iri(PROV_ACTIVITY)),
        _triple(act_uri, RDFS_LABEL, _literal(f"{component_name} extraction")),
        _triple(act_uri, PROV_USED, _iri(parent_uri)),
        _triple(act_uri, PROV_WAS_ASSOCIATED_WITH, _iri(agt_uri)),
        _triple(act_uri, PROV_STARTED_AT_TIME, _literal(timestamp)),
        _triple(act_uri, TG_COMPONENT_VERSION, _literal(component_version)),

        # Agent declaration
        _triple(agt_uri, RDF_TYPE, _iri(PROV_AGENT)),
        _triple(agt_uri, RDFS_LABEL, _literal(component_name)),
    ]

    if label:
        triples.append(_triple(entity_uri, RDFS_LABEL, _literal(label)))

    if page_number is not None:
        triples.append(_triple(entity_uri, TG_PAGE_NUMBER, _literal(page_number)))

    if chunk_index is not None:
        triples.append(_triple(entity_uri, TG_CHUNK_INDEX, _literal(chunk_index)))

    if char_offset is not None:
        triples.append(_triple(entity_uri, TG_CHAR_OFFSET, _literal(char_offset)))

    if char_length is not None:
        triples.append(_triple(entity_uri, TG_CHAR_LENGTH, _literal(char_length)))

    if chunk_size is not None:
        triples.append(_triple(act_uri, TG_CHUNK_SIZE, _literal(chunk_size)))

    if chunk_overlap is not None:
        triples.append(_triple(act_uri, TG_CHUNK_OVERLAP, _literal(chunk_overlap)))

    return triples


def triple_provenance_triples(
    stmt_uri: str,
    extracted_triple: Triple,
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for an extracted knowledge triple using reification.

    Creates:
    - Reification triple: stmt_uri tg:reifies <<extracted_triple>>
    - wasDerivedFrom link to source chunk
    - Activity and agent metadata

    Args:
        stmt_uri: URI for the reified statement
        extracted_triple: The extracted Triple to reify
        chunk_uri: URI of source chunk
        component_name: Name of extractor component
        component_version: Version of the component
        llm_model: LLM model used for extraction
        ontology_uri: Ontology URI used for extraction
        timestamp: ISO timestamp

    Returns:
        List of Triple objects for the provenance (including reification)
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"

    act_uri = activity_uri()
    agt_uri = agent_uri(component_name)

    # Create the quoted triple term (RDF-star reification)
    triple_term = Term(type=TRIPLE, triple=extracted_triple)

    triples = [
        # Reification: stmt_uri tg:reifies <<s p o>>
        Triple(
            s=_iri(stmt_uri),
            p=_iri(TG_REIFIES),
            o=triple_term
        ),

        # Statement provenance
        _triple(stmt_uri, PROV_WAS_DERIVED_FROM, _iri(chunk_uri)),
        _triple(stmt_uri, PROV_WAS_GENERATED_BY, _iri(act_uri)),

        # Activity
        _triple(act_uri, RDF_TYPE, _iri(PROV_ACTIVITY)),
        _triple(act_uri, RDFS_LABEL, _literal(f"{component_name} extraction")),
        _triple(act_uri, PROV_USED, _iri(chunk_uri)),
        _triple(act_uri, PROV_WAS_ASSOCIATED_WITH, _iri(agt_uri)),
        _triple(act_uri, PROV_STARTED_AT_TIME, _literal(timestamp)),
        _triple(act_uri, TG_COMPONENT_VERSION, _literal(component_version)),

        # Agent
        _triple(agt_uri, RDF_TYPE, _iri(PROV_AGENT)),
        _triple(agt_uri, RDFS_LABEL, _literal(component_name)),
    ]

    if llm_model:
        triples.append(_triple(act_uri, TG_LLM_MODEL, _literal(llm_model)))

    if ontology_uri:
        triples.append(_triple(act_uri, TG_ONTOLOGY, _iri(ontology_uri)))

    return triples


# Query-time provenance triple builders
#
# Terminology:
#   Question    - What was asked, the anchor for everything
#   Exploration - Casting wide, what do we know about this space
#   Focus       - Closing down, what's actually relevant here
#   Synthesis   - Weaving the relevant pieces into an answer

def question_triples(
    question_uri: str,
    query: str,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for a question activity.

    Creates:
    - Activity declaration for the question
    - Query text and timestamp

    Args:
        question_uri: URI of the question (from question_uri)
        query: The user's query text
        timestamp: ISO timestamp (defaults to now)

    Returns:
        List of Triple objects
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"

    return [
        _triple(question_uri, RDF_TYPE, _iri(PROV_ACTIVITY)),
        _triple(question_uri, RDF_TYPE, _iri(TG_QUESTION)),
        _triple(question_uri, RDFS_LABEL, _literal("GraphRAG Question")),
        _triple(question_uri, PROV_STARTED_AT_TIME, _literal(timestamp)),
        _triple(question_uri, TG_QUERY, _literal(query)),
    ]


def exploration_triples(
    exploration_uri: str,
    question_uri: str,
    edge_count: int,
) -> List[Triple]:
    """
    Build triples for an exploration entity (all edges retrieved from subgraph).

    Creates:
    - Entity declaration for exploration
    - wasGeneratedBy link to question
    - Edge count metadata

    Args:
        exploration_uri: URI of the exploration entity (from exploration_uri)
        question_uri: URI of the parent question
        edge_count: Number of edges retrieved

    Returns:
        List of Triple objects
    """
    return [
        _triple(exploration_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(exploration_uri, RDF_TYPE, _iri(TG_EXPLORATION)),
        _triple(exploration_uri, RDFS_LABEL, _literal("Exploration")),
        _triple(exploration_uri, PROV_WAS_GENERATED_BY, _iri(question_uri)),
        _triple(exploration_uri, TG_EDGE_COUNT, _literal(edge_count)),
    ]


def _quoted_triple(s: str, p: str, o: str) -> Term:
    """Create a quoted triple term (RDF-star) from string values."""
    return Term(
        type=TRIPLE,
        triple=Triple(s=_iri(s), p=_iri(p), o=_iri(o))
    )


def focus_triples(
    focus_uri: str,
    exploration_uri: str,
    selected_edges_with_reasoning: List[dict],
    session_id: str = "",
) -> List[Triple]:
    """
    Build triples for a focus entity (selected edges with reasoning).

    Creates:
    - Entity declaration for focus
    - wasDerivedFrom link to exploration
    - For each selected edge: an edge selection entity with quoted triple and reasoning

    Structure:
        <focus> tg:selectedEdge <edge_sel_1> .
        <edge_sel_1> tg:edge << <s> <p> <o> >> .
        <edge_sel_1> tg:reasoning "reason" .

    Args:
        focus_uri: URI of the focus entity (from focus_uri)
        exploration_uri: URI of the parent exploration entity
        selected_edges_with_reasoning: List of dicts with 'edge' (s,p,o tuple) and 'reasoning'
        session_id: Session UUID for generating edge selection URIs

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(focus_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(focus_uri, RDF_TYPE, _iri(TG_FOCUS)),
        _triple(focus_uri, RDFS_LABEL, _literal("Focus")),
        _triple(focus_uri, PROV_WAS_DERIVED_FROM, _iri(exploration_uri)),
    ]

    # Add each selected edge with its reasoning via intermediate entity
    for idx, edge_info in enumerate(selected_edges_with_reasoning):
        edge = edge_info.get("edge")
        reasoning = edge_info.get("reasoning", "")

        if edge:
            s, p, o = edge

            # Create intermediate entity for this edge selection
            edge_sel_uri = edge_selection_uri(session_id, idx)

            # Link focus to edge selection entity
            triples.append(
                _triple(focus_uri, TG_SELECTED_EDGE, _iri(edge_sel_uri))
            )

            # Attach quoted triple to edge selection entity
            quoted = _quoted_triple(s, p, o)
            triples.append(
                Triple(s=_iri(edge_sel_uri), p=_iri(TG_EDGE), o=quoted)
            )

            # Attach reasoning to edge selection entity
            if reasoning:
                triples.append(
                    _triple(edge_sel_uri, TG_REASONING, _literal(reasoning))
                )

    return triples


def synthesis_triples(
    synthesis_uri: str,
    focus_uri: str,
    answer_text: str = "",
    document_id: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for a synthesis entity (final answer text).

    Creates:
    - Entity declaration for synthesis
    - wasDerivedFrom link to focus
    - Either document reference (if document_id provided) or inline content

    Args:
        synthesis_uri: URI of the synthesis entity (from synthesis_uri)
        focus_uri: URI of the parent focus entity
        answer_text: The synthesized answer text (used if no document_id)
        document_id: Optional librarian document ID (preferred over inline content)

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(synthesis_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(synthesis_uri, RDF_TYPE, _iri(TG_SYNTHESIS)),
        _triple(synthesis_uri, RDFS_LABEL, _literal("Synthesis")),
        _triple(synthesis_uri, PROV_WAS_DERIVED_FROM, _iri(focus_uri)),
    ]

    if document_id:
        # Store reference to document in librarian (as IRI)
        triples.append(_triple(synthesis_uri, TG_DOCUMENT, _iri(document_id)))
    elif answer_text:
        # Fallback: store inline content
        triples.append(_triple(synthesis_uri, TG_CONTENT, _literal(answer_text)))

    return triples
