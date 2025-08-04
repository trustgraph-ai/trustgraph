from pulsar.schema import Record, String, Array

from ..core.primitives import Value, Triple
from ..core.metadata import Metadata
from ..core.topic import topic

############################################################################

# Entity context are an entity associated with textual context

class EntityContext(Record):
    entity = Value()
    context = String()

# This is a 'batching' mechanism for the above data
class EntityContexts(Record):
    metadata = Metadata()
    entities = Array(EntityContext())

############################################################################

# Graph triples

class Triples(Record):
    metadata = Metadata()
    triples = Array(Triple())

############################################################################