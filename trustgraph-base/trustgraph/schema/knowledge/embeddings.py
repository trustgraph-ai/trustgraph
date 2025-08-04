from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double, Map

from ..core.metadata import Metadata
from ..core.primitives import Value, RowSchema
from ..core.topic import topic

############################################################################

# Graph embeddings are embeddings associated with a graph entity

class EntityEmbeddings(Record):
    entity = Value()
    vectors = Array(Array(Double()))

# This is a 'batching' mechanism for the above data
class GraphEmbeddings(Record):
    metadata = Metadata()
    entities = Array(EntityEmbeddings())

############################################################################

# Document embeddings are embeddings associated with a chunk

class ChunkEmbeddings(Record):
    chunk = Bytes()
    vectors = Array(Array(Double()))

# This is a 'batching' mechanism for the above data
class DocumentEmbeddings(Record):
    metadata = Metadata()
    chunks = Array(ChunkEmbeddings())

############################################################################

# Object embeddings are embeddings associated with the primary key of an
# object

class ObjectEmbeddings(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    name = String()
    key_name = String()
    id = String()