from dataclasses import dataclass, field

from ..core.primitives import Error, Term, Triple
from ..core.topic import queue

############################################################################

# Graph embeddings query

@dataclass
class GraphEmbeddingsRequest:
    vector: list[float] = field(default_factory=list)
    limit: int = 0
    collection: str = ""

@dataclass
class EntityMatch:
    """A matching entity from a semantic search with similarity score"""
    entity: Term | None = None
    score: float = 0.0

@dataclass
class GraphEmbeddingsResponse:
    error: Error | None = None
    entities: list[EntityMatch] = field(default_factory=list)

############################################################################

# Graph triples query

@dataclass
class TriplesQueryRequest:
    collection: str = ""
    s: Term | None = None
    p: Term | None = None
    o: Term | None = None
    g: str | None = None  # Graph IRI. None=default graph, "*"=all graphs
    limit: int = 0
    streaming: bool = False  # Enable streaming mode (multiple batched responses)
    batch_size: int = 20     # Triples per batch in streaming mode

@dataclass
class TriplesQueryResponse:
    error: Error | None = None
    triples: list[Triple] = field(default_factory=list)
    is_final: bool = True    # False for intermediate batches in streaming mode

############################################################################

# Doc embeddings query

@dataclass
class DocumentEmbeddingsRequest:
    vector: list[float] = field(default_factory=list)
    limit: int = 0
    collection: str = ""

@dataclass
class ChunkMatch:
    """A matching chunk from a semantic search with similarity score"""
    chunk_id: str = ""
    score: float = 0.0

@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunks: list[ChunkMatch] = field(default_factory=list)

document_embeddings_request_queue = queue('document-embeddings', cls='request')
document_embeddings_response_queue = queue('document-embeddings', cls='response')

############################################################################

# Keyword index query - lexical (BM25) search over chunk text, the sparse
# counterpart to the doc embeddings query above. Matches share the ChunkMatch
# shape so both retrieval paths key on chunk_id; score is "higher is better"
# in both (BM25 rank scores are negated by the service to match).

@dataclass
class KeywordIndexRequest:
    query: str = ""
    limit: int = 0
    collection: str = ""

@dataclass
class KeywordIndexResponse:
    error: Error | None = None
    chunks: list[ChunkMatch] = field(default_factory=list)

keyword_index_request_queue = queue('keyword-index', cls='request')
keyword_index_response_queue = queue('keyword-index', cls='response')

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
    vector: list[float] = field(default_factory=list)  # Query vector
    limit: int = 10                         # Max results to return
    collection: str = ""                    # Collection name
    schema_name: str = ""                   # Schema name to search within
    index_name: str | None = None           # Optional: filter to specific index

@dataclass
class RowEmbeddingsResponse:
    """Response from row embeddings semantic search"""
    error: Error | None = None
    matches: list[RowIndexMatch] = field(default_factory=list)

row_embeddings_request_queue = queue('row-embeddings', cls='request')
row_embeddings_response_queue = queue('row-embeddings', cls='response')