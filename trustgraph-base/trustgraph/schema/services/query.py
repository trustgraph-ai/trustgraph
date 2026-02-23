from dataclasses import dataclass, field

from ..core.primitives import Error, Term, Triple
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
    entities: list[Term] = field(default_factory=list)

############################################################################

# Graph triples query

@dataclass
class TriplesQueryRequest:
    user: str = ""
    collection: str = ""
    s: Term | None = None
    p: Term | None = None
    o: Term | None = None
    g: str | None = None  # Graph IRI. None=default graph, "*"=all graphs
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

############################################################################

# Row embeddings query - for semantic/fuzzy matching on row index values

@dataclass
class RowIndexMatch:
    """A single matching row index from a semantic search"""
    index_name: str = ""                    # The indexed field(s)
    index_value: list[str] = field(default_factory=list)  # The index values
    text: str = ""                          # The text that was embedded
    score: float = 0.0                      # Similarity score

@dataclass
class RowEmbeddingsRequest:
    """Request for row embeddings semantic search"""
    vectors: list[list[float]] = field(default_factory=list)  # Query vectors
    limit: int = 10                         # Max results to return
    user: str = ""                          # User/keyspace
    collection: str = ""                    # Collection name
    schema_name: str = ""                   # Schema name to search within
    index_name: str | None = None           # Optional: filter to specific index

@dataclass
class RowEmbeddingsResponse:
    """Response from row embeddings semantic search"""
    error: Error | None = None
    matches: list[RowIndexMatch] = field(default_factory=list)

row_embeddings_request_queue = topic(
    "row-embeddings-request", qos='q0', tenant='trustgraph', namespace='flow'
)
row_embeddings_response_queue = topic(
    "row-embeddings-response", qos='q0', tenant='trustgraph', namespace='flow'
)