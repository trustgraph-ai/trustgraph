"""
Helper functions to build PROV-O triples for extraction-time provenance.
"""

from datetime import datetime
from typing import List, Optional

from .. schema import Triple, Term, IRI, LITERAL

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
)

from . uris import activity_uri, agent_uri


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
    subject_uri: str,
    predicate_uri: str,
    object_term: Term,
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
    - Statement object that reifies the triple
    - wasDerivedFrom link to source chunk
    - Activity and agent metadata

    Args:
        stmt_uri: URI for the reified statement
        subject_uri: Subject of the extracted triple
        predicate_uri: Predicate of the extracted triple
        object_term: Object of the extracted triple (Term)
        chunk_uri: URI of source chunk
        component_name: Name of extractor component
        component_version: Version of the component
        llm_model: LLM model used for extraction
        ontology_uri: Ontology URI used for extraction
        timestamp: ISO timestamp

    Returns:
        List of Triple objects for the provenance (not the triple itself)
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"

    act_uri = activity_uri()
    agt_uri = agent_uri(component_name)

    # Note: The actual reification (tg:reifies pointing at the edge) requires
    # RDF 1.2 triple term support. This builds the surrounding provenance.
    # The actual reification link must be handled by the knowledge extractor
    # using the graph store's reification API.

    triples = [
        # Statement provenance
        _triple(stmt_uri, PROV_WAS_DERIVED_FROM, _iri(chunk_uri)),
        _triple(stmt_uri, PROV_WAS_GENERATED_BY, _iri(act_uri)),

        # Activity
        _triple(act_uri, RDF_TYPE, _iri(PROV_ACTIVITY)),
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
