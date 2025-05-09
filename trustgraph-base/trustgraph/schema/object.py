
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array
from pulsar.schema import Double, Map

from . metadata import Metadata
from . types import Value, RowSchema
from . topic import topic

############################################################################

# Object embeddings are embeddings associated with the primary key of an
# object

class ObjectEmbeddings(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    name = String()
    key_name = String()
    id = String()

############################################################################

# Stores rows of information

class Rows(Record):
    metadata = Metadata()
    row_schema = RowSchema()
    rows = Array(Map(String()))



