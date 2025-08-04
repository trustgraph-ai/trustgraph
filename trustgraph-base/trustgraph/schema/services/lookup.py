
from pulsar.schema import Record, String

from ..core.primitives import Error, Value, Triple
from ..core.topic import topic
from ..core.metadata import Metadata

############################################################################

# Lookups

class LookupRequest(Record):
    kind = String()
    term = String()

class LookupResponse(Record):
    text = String()
    error = Error()

############################################################################

