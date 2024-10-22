
from pulsar.schema import Record, String, Array
from . types import Triple

class Metadata(Record):

    # Source identifier
    id = String()

    # Subgraph
    metadata = Array(Triple())

    # Collection management
    user = String()
    collection = String()

