
from pulsar.schema import Record, String

from . types import Error, Value, Triple
from . topic import topic
from . metadata import Metadata

############################################################################

# Lookups

class LookupRequest(Record):
    kind = String()
    term = String()

class LookupResponse(Record):
    text = String()
    error = Error()

############################################################################

