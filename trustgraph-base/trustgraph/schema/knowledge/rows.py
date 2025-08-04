from pulsar.schema import Record, Array, Map, String

from ..core.metadata import Metadata
from ..core.primitives import RowSchema
from ..core.topic import topic

############################################################################

# Stores rows of information

class Rows(Record):
    metadata = Metadata()
    row_schema = RowSchema()
    rows = Array(Map(String()))

############################################################################