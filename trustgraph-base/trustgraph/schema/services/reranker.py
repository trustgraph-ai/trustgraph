
from dataclasses import dataclass, field

from ..core.primitives import Error

############################################################################

# Cross-encoder reranker

@dataclass
class RerankerQuery:
    query_id: str = ""
    query_text: str = ""

@dataclass
class RerankerDocument:
    document_id: str = ""
    document_text: str = ""

@dataclass
class RerankerRequest:
    queries: list[RerankerQuery] = field(default_factory=list)
    documents: list[RerankerDocument] = field(default_factory=list)
    limit: int = 10

@dataclass
class RerankerResult:
    document_id: str = ""
    query_id: str = ""
    score: float = 0.0

@dataclass
class RerankerResponse:
    error: Error | None = None
    results: list[RerankerResult] = field(default_factory=list)
