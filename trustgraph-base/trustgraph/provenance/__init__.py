"""
Provenance module for extraction-time provenance support.

Provides helpers for:
- URI generation for documents, pages, chunks, activities, statements
- PROV-O triple building for provenance metadata
- Vocabulary bootstrap for per-collection initialization

Usage example:

    from trustgraph.provenance import (
        document_uri, page_uri, chunk_uri_from_page,
        document_triples, derived_entity_triples,
        get_vocabulary_triples,
    )

    # Generate URIs
    doc_uri = document_uri("my-doc-123")
    page_uri = page_uri("my-doc-123", page_number=1)

    # Build provenance triples
    triples = document_triples(
        doc_uri,
        title="My Document",
        mime_type="application/pdf",
        page_count=10,
    )

    # Get vocabulary bootstrap triples (once per collection)
    vocab_triples = get_vocabulary_triples()
"""

# URI generation
from . uris import (
    TRUSTGRAPH_BASE,
    document_uri,
    page_uri,
    chunk_uri_from_page,
    chunk_uri_from_doc,
    activity_uri,
    statement_uri,
    agent_uri,
)

# Namespace constants
from . namespaces import (
    # PROV-O
    PROV, PROV_ENTITY, PROV_ACTIVITY, PROV_AGENT,
    PROV_WAS_DERIVED_FROM, PROV_WAS_GENERATED_BY,
    PROV_USED, PROV_WAS_ASSOCIATED_WITH, PROV_STARTED_AT_TIME,
    # Dublin Core
    DC, DC_TITLE, DC_SOURCE, DC_DATE, DC_CREATOR,
    # RDF/RDFS
    RDF, RDF_TYPE, RDFS, RDFS_LABEL,
    # TrustGraph
    TG, TG_REIFIES, TG_PAGE_COUNT, TG_MIME_TYPE, TG_PAGE_NUMBER,
    TG_CHUNK_INDEX, TG_CHAR_OFFSET, TG_CHAR_LENGTH,
    TG_CHUNK_SIZE, TG_CHUNK_OVERLAP, TG_COMPONENT_VERSION,
    TG_LLM_MODEL, TG_ONTOLOGY, TG_EMBEDDING_MODEL,
    TG_SOURCE_TEXT, TG_SOURCE_CHAR_OFFSET, TG_SOURCE_CHAR_LENGTH,
)

# Triple builders
from . triples import (
    document_triples,
    derived_entity_triples,
    triple_provenance_triples,
)

# Vocabulary bootstrap
from . vocabulary import (
    get_vocabulary_triples,
    PROV_CLASS_LABELS,
    PROV_PREDICATE_LABELS,
    DC_PREDICATE_LABELS,
    TG_PREDICATE_LABELS,
)

__all__ = [
    # URIs
    "TRUSTGRAPH_BASE",
    "document_uri",
    "page_uri",
    "chunk_uri_from_page",
    "chunk_uri_from_doc",
    "activity_uri",
    "statement_uri",
    "agent_uri",
    # Namespaces
    "PROV", "PROV_ENTITY", "PROV_ACTIVITY", "PROV_AGENT",
    "PROV_WAS_DERIVED_FROM", "PROV_WAS_GENERATED_BY",
    "PROV_USED", "PROV_WAS_ASSOCIATED_WITH", "PROV_STARTED_AT_TIME",
    "DC", "DC_TITLE", "DC_SOURCE", "DC_DATE", "DC_CREATOR",
    "RDF", "RDF_TYPE", "RDFS", "RDFS_LABEL",
    "TG", "TG_REIFIES", "TG_PAGE_COUNT", "TG_MIME_TYPE", "TG_PAGE_NUMBER",
    "TG_CHUNK_INDEX", "TG_CHAR_OFFSET", "TG_CHAR_LENGTH",
    "TG_CHUNK_SIZE", "TG_CHUNK_OVERLAP", "TG_COMPONENT_VERSION",
    "TG_LLM_MODEL", "TG_ONTOLOGY", "TG_EMBEDDING_MODEL",
    "TG_SOURCE_TEXT", "TG_SOURCE_CHAR_OFFSET", "TG_SOURCE_CHAR_LENGTH",
    # Triple builders
    "document_triples",
    "derived_entity_triples",
    "triple_provenance_triples",
    # Vocabulary
    "get_vocabulary_triples",
    "PROV_CLASS_LABELS",
    "PROV_PREDICATE_LABELS",
    "DC_PREDICATE_LABELS",
    "TG_PREDICATE_LABELS",
]
