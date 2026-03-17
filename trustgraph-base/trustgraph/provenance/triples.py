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
    TG_LLM_MODEL, TG_ONTOLOGY, TG_CONTAINS,
    # Extraction provenance entity types
    TG_DOCUMENT_TYPE, TG_PAGE_TYPE, TG_CHUNK_TYPE, TG_SUBGRAPH_TYPE,
    # Query-time provenance predicates (GraphRAG)
    TG_QUERY, TG_CONCEPT, TG_ENTITY,
    TG_EDGE_COUNT, TG_SELECTED_EDGE, TG_EDGE, TG_REASONING,
    TG_DOCUMENT,
    # Query-time provenance predicates (DocumentRAG)
    TG_CHUNK_COUNT, TG_SELECTED_CHUNK,
    # Explainability entity types
    TG_QUESTION, TG_GROUNDING, TG_EXPLORATION, TG_FOCUS, TG_SYNTHESIS,
    # Unifying types
    TG_ANSWER_TYPE,
    # Question subtypes
    TG_GRAPH_RAG_QUESTION, TG_DOC_RAG_QUESTION,
)

from . uris import activity_uri, agent_uri, subgraph_uri, edge_selection_uri


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
        _triple(doc_uri, RDF_TYPE, _iri(TG_DOCUMENT_TYPE)),
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

    # Determine specific type from parameters
    if page_number is not None:
        specific_type = TG_PAGE_TYPE
    elif chunk_index is not None:
        specific_type = TG_CHUNK_TYPE
    else:
        specific_type = None

    triples = [
        # Entity declaration
        _triple(entity_uri, RDF_TYPE, _iri(PROV_ENTITY)),
    ]

    if specific_type:
        triples.append(_triple(entity_uri, RDF_TYPE, _iri(specific_type)))

    triples.extend([
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
    ])

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


def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    One subgraph per chunk extraction, shared across all triples produced
    from that chunk.  This replaces per-triple reification with a
    containment model.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata

    Args:
        subgraph_uri: URI for the extraction subgraph
        extracted_triples: The extracted Triple objects to include
        chunk_uri: URI of source chunk
        component_name: Name of extractor component
        component_version: Version of the component
        llm_model: LLM model used for extraction
        ontology_uri: Ontology URI used for extraction
        timestamp: ISO timestamp

    Returns:
        List of Triple objects for the provenance
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"

    act_uri = activity_uri()
    agt_uri = agent_uri(component_name)

    triples = []

    # Containment: subgraph tg:contains <<s p o>> for each extracted triple
    for extracted_triple in extracted_triples:
        triple_term = Term(type=TRIPLE, triple=extracted_triple)
        triples.append(Triple(
            s=_iri(subgraph_uri),
            p=_iri(TG_CONTAINS),
            o=triple_term
        ))

    # Subgraph provenance
    triples.extend([
        _triple(subgraph_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(subgraph_uri, RDF_TYPE, _iri(TG_SUBGRAPH_TYPE)),
        _triple(subgraph_uri, PROV_WAS_DERIVED_FROM, _iri(chunk_uri)),
        _triple(subgraph_uri, PROV_WAS_GENERATED_BY, _iri(act_uri)),

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
    ])

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
        _triple(question_uri, RDF_TYPE, _iri(TG_GRAPH_RAG_QUESTION)),
        _triple(question_uri, RDFS_LABEL, _literal("GraphRAG Question")),
        _triple(question_uri, PROV_STARTED_AT_TIME, _literal(timestamp)),
        _triple(question_uri, TG_QUERY, _literal(query)),
    ]


def grounding_triples(
    grounding_uri: str,
    question_uri: str,
    concepts: List[str],
) -> List[Triple]:
    """
    Build triples for a grounding entity (concept decomposition of query).

    Creates:
    - Entity declaration for grounding
    - wasGeneratedBy link to question
    - Concept literals for each extracted concept

    Args:
        grounding_uri: URI of the grounding entity (from grounding_uri)
        question_uri: URI of the parent question
        concepts: List of concept strings extracted from the query

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(grounding_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(grounding_uri, RDF_TYPE, _iri(TG_GROUNDING)),
        _triple(grounding_uri, RDFS_LABEL, _literal("Grounding")),
        _triple(grounding_uri, PROV_WAS_GENERATED_BY, _iri(question_uri)),
    ]

    for concept in concepts:
        triples.append(_triple(grounding_uri, TG_CONCEPT, _literal(concept)))

    return triples


def exploration_triples(
    exploration_uri: str,
    grounding_uri: str,
    edge_count: int,
    entities: Optional[List[str]] = None,
) -> List[Triple]:
    """
    Build triples for an exploration entity (all edges retrieved from subgraph).

    Creates:
    - Entity declaration for exploration
    - wasDerivedFrom link to grounding
    - Edge count metadata
    - Entity IRIs for each seed entity

    Args:
        exploration_uri: URI of the exploration entity (from exploration_uri)
        grounding_uri: URI of the parent grounding entity
        edge_count: Number of edges retrieved
        entities: Optional list of seed entity URIs

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(exploration_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(exploration_uri, RDF_TYPE, _iri(TG_EXPLORATION)),
        _triple(exploration_uri, RDFS_LABEL, _literal("Exploration")),
        _triple(exploration_uri, PROV_WAS_DERIVED_FROM, _iri(grounding_uri)),
        _triple(exploration_uri, TG_EDGE_COUNT, _literal(edge_count)),
    ]

    if entities:
        for entity in entities:
            triples.append(_triple(exploration_uri, TG_ENTITY, _iri(entity)))

    return triples


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
    document_id: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for a synthesis entity (final answer).

    Creates:
    - Entity declaration for synthesis with tg:Answer type
    - wasDerivedFrom link to focus
    - Document reference to librarian

    Args:
        synthesis_uri: URI of the synthesis entity (from synthesis_uri)
        focus_uri: URI of the parent focus entity
        document_id: Librarian document ID for the answer content

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(synthesis_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(synthesis_uri, RDF_TYPE, _iri(TG_SYNTHESIS)),
        _triple(synthesis_uri, RDF_TYPE, _iri(TG_ANSWER_TYPE)),
        _triple(synthesis_uri, RDFS_LABEL, _literal("Synthesis")),
        _triple(synthesis_uri, PROV_WAS_DERIVED_FROM, _iri(focus_uri)),
    ]

    if document_id:
        triples.append(_triple(synthesis_uri, TG_DOCUMENT, _iri(document_id)))

    return triples


# Document RAG provenance triple builders
#
# Document RAG uses a subset of GraphRAG's model:
#   Question    - What was asked
#   Exploration - Chunks retrieved from document store
#   Synthesis   - The final answer (no Focus step)

def docrag_question_triples(
    question_uri: str,
    query: str,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for a document RAG question activity.

    Creates:
    - Activity declaration with tg:Question type
    - Query text and timestamp

    Args:
        question_uri: URI of the question (from docrag_question_uri)
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
        _triple(question_uri, RDF_TYPE, _iri(TG_DOC_RAG_QUESTION)),
        _triple(question_uri, RDFS_LABEL, _literal("DocumentRAG Question")),
        _triple(question_uri, PROV_STARTED_AT_TIME, _literal(timestamp)),
        _triple(question_uri, TG_QUERY, _literal(query)),
    ]


def docrag_exploration_triples(
    exploration_uri: str,
    grounding_uri: str,
    chunk_count: int,
    chunk_ids: Optional[List[str]] = None,
) -> List[Triple]:
    """
    Build triples for a document RAG exploration entity (chunks retrieved).

    Creates:
    - Entity declaration with tg:Exploration type
    - wasDerivedFrom link to grounding
    - Chunk count and optional chunk references

    Args:
        exploration_uri: URI of the exploration entity
        grounding_uri: URI of the parent grounding entity
        chunk_count: Number of chunks retrieved
        chunk_ids: Optional list of chunk URIs/IDs

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(exploration_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(exploration_uri, RDF_TYPE, _iri(TG_EXPLORATION)),
        _triple(exploration_uri, RDFS_LABEL, _literal("Exploration")),
        _triple(exploration_uri, PROV_WAS_DERIVED_FROM, _iri(grounding_uri)),
        _triple(exploration_uri, TG_CHUNK_COUNT, _literal(chunk_count)),
    ]

    # Add references to selected chunks
    if chunk_ids:
        for chunk_id in chunk_ids:
            triples.append(_triple(exploration_uri, TG_SELECTED_CHUNK, _iri(chunk_id)))

    return triples


def docrag_synthesis_triples(
    synthesis_uri: str,
    exploration_uri: str,
    document_id: Optional[str] = None,
) -> List[Triple]:
    """
    Build triples for a document RAG synthesis entity (final answer).

    Creates:
    - Entity declaration with tg:Synthesis and tg:Answer types
    - wasDerivedFrom link to exploration (skips focus step)
    - Document reference to librarian

    Args:
        synthesis_uri: URI of the synthesis entity
        exploration_uri: URI of the parent exploration entity
        document_id: Librarian document ID for the answer content

    Returns:
        List of Triple objects
    """
    triples = [
        _triple(synthesis_uri, RDF_TYPE, _iri(PROV_ENTITY)),
        _triple(synthesis_uri, RDF_TYPE, _iri(TG_SYNTHESIS)),
        _triple(synthesis_uri, RDF_TYPE, _iri(TG_ANSWER_TYPE)),
        _triple(synthesis_uri, RDFS_LABEL, _literal("Synthesis")),
        _triple(synthesis_uri, PROV_WAS_DERIVED_FROM, _iri(exploration_uri)),
    ]

    if document_id:
        triples.append(_triple(synthesis_uri, TG_DOCUMENT, _iri(document_id)))

    return triples
