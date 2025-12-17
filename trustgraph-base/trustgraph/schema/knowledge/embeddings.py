from dataclasses import dataclass, field

from ..core.metadata import Metadata
from ..core.primitives import Value, RowSchema
from ..core.topic import topic

############################################################################

# Graph embeddings are embeddings associated with a graph entity

@dataclass
class EntityEmbeddings:
    entity: Value | None = None
    vectors: list[list[float]] = field(default_factory=list)

# This is a 'batching' mechanism for the above data
@dataclass
class GraphEmbeddings:
    metadata: Metadata | None = None
    entities: list[EntityEmbeddings] = field(default_factory=list)

############################################################################

# Document embeddings are embeddings associated with a chunk

@dataclass
class ChunkEmbeddings:
    chunk: bytes = b""
    vectors: list[list[float]] = field(default_factory=list)

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
    vectors: list[list[float]] = field(default_factory=list)
    name: str = ""
    key_name: str = ""
    id: str = ""

############################################################################

# Structured object embeddings with enhanced capabilities

@dataclass
class StructuredObjectEmbedding:
    metadata: Metadata | None = None
    vectors: list[list[float]] = field(default_factory=list)
    schema_name: str = ""
    object_id: str = ""  # Primary key value
    field_embeddings: dict[str, list[float]] = field(default_factory=dict)  # Per-field embeddings

############################################################################
