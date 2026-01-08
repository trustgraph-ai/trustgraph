from dataclasses import dataclass, field

from ..core.primitives import Error, Value, Triple
from ..core.topic import topic

############################################################################

# Graph embeddings query

@dataclass
class GraphEmbeddingsRequest:
    vectors: list[list[float]] = field(default_factory=list)
    limit: int = 0
    user: str = ""
    collection: str = ""

@dataclass
class GraphEmbeddingsResponse:
    error: Error | None = None
    entities: list[Value] = field(default_factory=list)

############################################################################

# Graph triples query

@dataclass
class TriplesQueryRequest:
    user: str = ""
    collection: str = ""
    s: Value | None = None
    p: Value | None = None
    o: Value | None = None
    limit: int = 0

@dataclass
class TriplesQueryResponse:
    error: Error | None = None
    triples: list[Triple] = field(default_factory=list)

############################################################################

# Doc embeddings query

@dataclass
class DocumentEmbeddingsRequest:
    vectors: list[list[float]] = field(default_factory=list)
    limit: int = 0
    user: str = ""
    collection: str = ""

@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunks: list[str] = field(default_factory=list)

document_embeddings_request_queue = topic(
    "document-embeddings-request", qos='q0', tenant='trustgraph', namespace='flow'
)
document_embeddings_response_queue = topic(
    "document-embeddings-response", qos='q0', tenant='trustgraph', namespace='flow'
)