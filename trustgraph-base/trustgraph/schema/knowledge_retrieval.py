
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Knowledge retrieval edge

@dataclass
class RetrievedEdge:
    s: str = ""
    p: str = ""
    o: str = ""
    s_label: str = ""
    p_label: str = ""
    o_label: str = ""
    score: float = 0.0
    concept: str = ""

############################################################################

# Knowledge retrieval request/response

@dataclass
class KnowledgeRetrievalRequest:
    concepts: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    entity_limit: int = 50
    triple_limit: int = 30
    max_path_length: int = 2
    edge_limit: int = 25
    max_reranker_input: int = 350
    languages: list[str] = field(default_factory=list)
    graph: str = ""

@dataclass
class KnowledgeRetrievalResponse:
    error: Error | None = None
    edges: list[RetrievedEdge] = field(default_factory=list)
    seed_entities: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)

knowledge_retrieval_request_queue = queue(
    'knowledge-retrieval', cls='request',
)
knowledge_retrieval_response_queue = queue(
    'knowledge-retrieval', cls='response',
)

############################################################################
