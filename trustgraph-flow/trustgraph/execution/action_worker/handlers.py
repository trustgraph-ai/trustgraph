"""
Capability handler registry for the action worker.
"""

from . common import HandlerError

from . retrieval import (
    ConceptExtractionHandler,
    KnowledgeRetrievalHandler,
    GraphRagQueryHandler,
    GraphEmbeddingsQueryHandler,
    EntityTriplesQueryHandler,
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

from . external import ErpFinanceQueryHandler


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
    "cloze": ClozeHandler(),
    "decision-scoring": DecisionScoringHandler(),
    "field-extraction": FieldExtractionHandler(),
    "erp-finance-query": ErpFinanceQueryHandler(),
}
