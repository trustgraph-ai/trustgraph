"""
Provenance module for extraction-time provenance support.

Provides helpers for:
- URI generation for documents, pages, chunks, activities, subgraphs
- PROV-O triple building for provenance metadata
- Vocabulary bootstrap for per-collection initialization

Usage example:

    from trustgraph.provenance import (
        document_uri, page_uri, chunk_uri,
        document_triples, derived_entity_triples,
        get_vocabulary_triples,
    )

    # Generate URIs
    doc_uri = document_uri("my-doc-123")
    pg_uri = page_uri()

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
    section_uri,
    chunk_uri,
    image_uri,
    activity_uri,
    subgraph_uri,
    agent_uri,
    # Query-time provenance URIs (GraphRAG)
    question_uri,
    grounding_uri,
    exploration_uri,
    focus_uri,
    synthesis_uri,
    # Agent provenance URIs
    agent_session_uri,
    agent_iteration_uri,
    agent_thought_uri,
    agent_observation_uri,
    agent_final_uri,
    # Document RAG provenance URIs
    docrag_question_uri,
    docrag_grounding_uri,
    docrag_exploration_uri,
    docrag_synthesis_uri,
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
    TG, TG_CONTAINS, TG_PAGE_COUNT, TG_MIME_TYPE, TG_PAGE_NUMBER,
    TG_CHUNK_INDEX, TG_CHAR_OFFSET, TG_CHAR_LENGTH,
    TG_CHUNK_SIZE, TG_CHUNK_OVERLAP, TG_COMPONENT_VERSION,
    TG_LLM_MODEL, TG_ONTOLOGY, TG_EMBEDDING_MODEL,
    TG_SOURCE_TEXT, TG_SOURCE_CHAR_OFFSET, TG_SOURCE_CHAR_LENGTH,
    TG_ELEMENT_TYPES, TG_TABLE_COUNT, TG_IMAGE_COUNT,
    # Extraction provenance entity types
    TG_DOCUMENT_TYPE, TG_PAGE_TYPE, TG_SECTION_TYPE, TG_CHUNK_TYPE,
    TG_IMAGE_TYPE, TG_SUBGRAPH_TYPE,
    # Query-time provenance predicates (GraphRAG)
    TG_QUERY, TG_CONCEPT, TG_ENTITY,
    TG_EDGE_COUNT, TG_SELECTED_EDGE, TG_REASONING,
    # Query-time provenance predicates (DocumentRAG)
    TG_CHUNK_COUNT, TG_SELECTED_CHUNK,
    # Explainability entity types
    TG_QUESTION, TG_GROUNDING, TG_EXPLORATION, TG_FOCUS, TG_SYNTHESIS,
    TG_ANALYSIS, TG_CONCLUSION,
    # Unifying types
    TG_ANSWER_TYPE, TG_REFLECTION_TYPE, TG_THOUGHT_TYPE, TG_OBSERVATION_TYPE,
    # Question subtypes (to distinguish retrieval mechanism)
    TG_GRAPH_RAG_QUESTION, TG_DOC_RAG_QUESTION, TG_AGENT_QUESTION,
    # Agent provenance predicates
    TG_THOUGHT, TG_ACTION, TG_ARGUMENTS, TG_OBSERVATION,
    # Document reference predicate
    TG_DOCUMENT,
    # Named graphs
    GRAPH_DEFAULT, GRAPH_SOURCE, GRAPH_RETRIEVAL,
)

# Triple builders
from . triples import (
    document_triples,
    derived_entity_triples,
    subgraph_provenance_triples,
    # Query-time provenance triple builders (GraphRAG)
    question_triples,
    grounding_triples,
    exploration_triples,
    focus_triples,
    synthesis_triples,
    # Query-time provenance triple builders (DocumentRAG)
    docrag_question_triples,
    docrag_exploration_triples,
    docrag_synthesis_triples,
    # Utility
    set_graph,
)

# Agent provenance triple builders
from . agent import (
    agent_session_triples,
    agent_iteration_triples,
    agent_final_triples,
)

# Vocabulary bootstrap
from . vocabulary import (
    get_vocabulary_triples,
    PROV_CLASS_LABELS,
    PROV_PREDICATE_LABELS,
    DC_PREDICATE_LABELS,
    TG_CLASS_LABELS,
    TG_PREDICATE_LABELS,
)

__all__ = [
    # URIs
    "TRUSTGRAPH_BASE",
    "document_uri",
    "page_uri",
    "section_uri",
    "chunk_uri",
    "image_uri",
    "activity_uri",
    "subgraph_uri",
    "agent_uri",
    # Query-time provenance URIs
    "question_uri",
    "grounding_uri",
    "exploration_uri",
    "focus_uri",
    "synthesis_uri",
    # Agent provenance URIs
    "agent_session_uri",
    "agent_iteration_uri",
    "agent_thought_uri",
    "agent_observation_uri",
    "agent_final_uri",
    # Document RAG provenance URIs
    "docrag_question_uri",
    "docrag_grounding_uri",
    "docrag_exploration_uri",
    "docrag_synthesis_uri",
    # Namespaces
    "PROV", "PROV_ENTITY", "PROV_ACTIVITY", "PROV_AGENT",
    "PROV_WAS_DERIVED_FROM", "PROV_WAS_GENERATED_BY",
    "PROV_USED", "PROV_WAS_ASSOCIATED_WITH", "PROV_STARTED_AT_TIME",
    "DC", "DC_TITLE", "DC_SOURCE", "DC_DATE", "DC_CREATOR",
    "RDF", "RDF_TYPE", "RDFS", "RDFS_LABEL",
    "TG", "TG_CONTAINS", "TG_PAGE_COUNT", "TG_MIME_TYPE", "TG_PAGE_NUMBER",
    "TG_CHUNK_INDEX", "TG_CHAR_OFFSET", "TG_CHAR_LENGTH",
    "TG_CHUNK_SIZE", "TG_CHUNK_OVERLAP", "TG_COMPONENT_VERSION",
    "TG_LLM_MODEL", "TG_ONTOLOGY", "TG_EMBEDDING_MODEL",
    "TG_SOURCE_TEXT", "TG_SOURCE_CHAR_OFFSET", "TG_SOURCE_CHAR_LENGTH",
    "TG_ELEMENT_TYPES", "TG_TABLE_COUNT", "TG_IMAGE_COUNT",
    # Extraction provenance entity types
    "TG_DOCUMENT_TYPE", "TG_PAGE_TYPE", "TG_SECTION_TYPE",
    "TG_CHUNK_TYPE", "TG_IMAGE_TYPE", "TG_SUBGRAPH_TYPE",
    # Query-time provenance predicates (GraphRAG)
    "TG_QUERY", "TG_CONCEPT", "TG_ENTITY",
    "TG_EDGE_COUNT", "TG_SELECTED_EDGE", "TG_REASONING",
    # Query-time provenance predicates (DocumentRAG)
    "TG_CHUNK_COUNT", "TG_SELECTED_CHUNK",
    # Explainability entity types
    "TG_QUESTION", "TG_GROUNDING", "TG_EXPLORATION", "TG_FOCUS", "TG_SYNTHESIS",
    "TG_ANALYSIS", "TG_CONCLUSION",
    # Unifying types
    "TG_ANSWER_TYPE", "TG_REFLECTION_TYPE", "TG_THOUGHT_TYPE", "TG_OBSERVATION_TYPE",
    # Question subtypes
    "TG_GRAPH_RAG_QUESTION", "TG_DOC_RAG_QUESTION", "TG_AGENT_QUESTION",
    # Agent provenance predicates
    "TG_THOUGHT", "TG_ACTION", "TG_ARGUMENTS", "TG_OBSERVATION",
    # Document reference predicate
    "TG_DOCUMENT",
    # Named graphs
    "GRAPH_DEFAULT", "GRAPH_SOURCE", "GRAPH_RETRIEVAL",
    # Triple builders
    "document_triples",
    "derived_entity_triples",
    "subgraph_provenance_triples",
    # Query-time provenance triple builders (GraphRAG)
    "question_triples",
    "grounding_triples",
    "exploration_triples",
    "focus_triples",
    "synthesis_triples",
    # Query-time provenance triple builders (DocumentRAG)
    "docrag_question_triples",
    "docrag_exploration_triples",
    "docrag_synthesis_triples",
    # Agent provenance triple builders
    "agent_session_triples",
    "agent_iteration_triples",
    "agent_final_triples",
    # Utility
    "set_graph",
    # Vocabulary
    "get_vocabulary_triples",
    "PROV_CLASS_LABELS",
    "PROV_PREDICATE_LABELS",
    "DC_PREDICATE_LABELS",
    "TG_CLASS_LABELS",
    "TG_PREDICATE_LABELS",
]
