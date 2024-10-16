
from pulsar.schema import Record, String, Array
from . types import Triple

class Metadata(Record):

    # Source identifier
    id = String()

    # Subgraph
    source = Array(Triple())

    # Collection management
    user = String()
    collection = String()

