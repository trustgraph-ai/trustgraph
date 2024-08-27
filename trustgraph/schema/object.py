
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array
from pulsar.schema import Double, Map

from . documents import Source
from . types import Value, RowSchema
from . topic import topic

############################################################################

# Object embeddings are embeddings associated with the primary key of an
# object

class ObjectEmbeddings(Record):
    source = Source()
    vectors = Array(Array(Double()))
    key_name = String()
    id = String()

object_embeddings_store_queue = topic('object-embeddings-store')

############################################################################

# Stores rows of information

class Rows(Record):
    source = Source()
    row_schema = RowSchema()
    rows = Array(Map(String()))

rows_store_queue = topic('rows-store')

