
from dataclasses import dataclass, field

from .core.metadata import Metadata
from .core.primitives import Term, Error, RowSchema
from .core.topic import queue

############################################################################

# Graph embeddings are embeddings associated with a graph entity

@dataclass
class EntityEmbeddings:
    entity: Term | None = None
    vector: list[float] = field(default_factory=list)
    # Provenance: which chunk this embedding was derived from
    chunk_id: str = ""

# This is a 'batching' mechanism for the above data
@dataclass
class GraphEmbeddings:
    metadata: Metadata | None = None
    entities: list[EntityEmbeddings] = field(default_factory=list)

############################################################################

# Document embeddings are embeddings associated with a chunk

@dataclass
class ChunkEmbeddings:
    chunk_id: str = ""
    vector: list[float] = field(default_factory=list)

# This is a 'batching' mechanism for the above data
@dataclass
class DocumentEmbeddings:
    metadata: Metadata | None = None
    chunks: list[ChunkEmbeddings] = field(default_factory=list)

############################################################################

# Object embeddings are embeddings associated with the primary key of an
# object

@dataclass
class ObjectEmbeddings:
    metadata: Metadata | None = None
    vector: list[float] = field(default_factory=list)
    name: str = ""
    key_name: str = ""
    id: str = ""

############################################################################

# Structured object embeddings with enhanced capabilities

@dataclass
class StructuredObjectEmbedding:
    metadata: Metadata | None = None
    vector: list[float] = field(default_factory=list)
    schema_name: str = ""
    object_id: str = ""  # Primary key value
    field_embeddings: dict[str, list[float]] = field(default_factory=dict)  # Per-field embeddings

############################################################################

# Row embeddings are embeddings associated with indexed field values
# in structured row data. Each index gets embedded separately.

@dataclass
class RowIndexEmbedding:
    """Single row's embedding for one index"""
    index_name: str = ""              # The indexed field name(s)
    index_value: list[str] = field(default_factory=list)  # The field value(s)
    text: str = ""                    # Text that was embedded
    vector: list[float] = field(default_factory=list)

@dataclass
class RowEmbeddings:
    """Batched row embeddings for a schema"""
    metadata: Metadata | None = None
    schema_name: str = ""
    embeddings: list[RowIndexEmbedding] = field(default_factory=list)

############################################################################

# Embeddings service request/response

@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)

@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[float]] = field(default_factory=list)

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

# Keyword index query

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

# Row embeddings query

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

############################################################################
