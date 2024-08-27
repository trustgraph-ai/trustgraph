
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double

from . documents import Source
from . types import Value
from . topic import topic

############################################################################

# Object embeddings are embeddings associated with the primary key of an
# object

class ObjectEmbeddings(Record):
    source = Source()
    vectors = Array(Array(Double()))
    id = Value()

object_embeddings_store_queue = topic('object-embeddings-store')
