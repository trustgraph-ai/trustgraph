"""
Capability handler registry for the action worker.
"""

from . common import HandlerError, ActionHandler

from . retrieval import (
    ConceptExtractionHandler,
    KnowledgeRetrievalHandler,
    GraphRagQueryHandler,
    GraphEmbeddingsQueryHandler,
    EntityTriplesQueryHandler,
    DocumentRagQueryHandler,
    TriplesQueryHandler,
    SparqlQueryHandler,
)

from . transform import (
    RerankHandler,
    TabularRedactHandler,
    TabularJoinHandler,
)

from . synthesis import LlmSynthesisHandler

from . system1 import (
    ClozeHandler,
    DecisionScoringHandler,
    FieldExtractionHandler,
)

from . decoding import DocumentDecodeHandler
from . chunking import ChunkHandler
from . extraction import ExtractionHandler
from . mcp_tool import McpToolHandler
from . query_formulation import QueryFormulationHandler


BUILTIN_HANDLERS = {
    "concept-extraction": ConceptExtractionHandler(),
    "knowledge-retrieval": KnowledgeRetrievalHandler(),
    "graph-rag-query": GraphRagQueryHandler(),
    "graph-embeddings-query": GraphEmbeddingsQueryHandler(),
    "entity-triples-query": EntityTriplesQueryHandler(),
    "rerank": RerankHandler(),
    "llm-synthesis": LlmSynthesisHandler(),
    "tabular-redact": TabularRedactHandler(),
    "tabular-join": TabularJoinHandler(),
    "document-rag-query": DocumentRagQueryHandler(),
    "triples-query": TriplesQueryHandler(),
    "sparql-query": SparqlQueryHandler(),
    "cloze": ClozeHandler(),
    "decision-scoring": DecisionScoringHandler(),
    "field-extraction": FieldExtractionHandler(),
    "document-decode": DocumentDecodeHandler(),
    "chunk": ChunkHandler(),
    "extract-definitions": ExtractionHandler("extract-definitions-request"),
    "extract-relationships": ExtractionHandler("extract-relationships-request"),
    "extract-ontology": ExtractionHandler("extract-ontology-request"),
    "mcp-tool": McpToolHandler(),
    "query-formulation": QueryFormulationHandler(),
}
