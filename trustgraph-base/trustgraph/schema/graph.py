
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double

from . types import Error, Value, Triple
from . topic import topic
from . metadata import Metadata

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

# Graph embeddings are embeddings associated with a graph entity

class EntityEmbeddings(Record):
    entity = Value()
    vectors = Array(Array(Double()))

# This is a 'batching' mechanism for the above data
class GraphEmbeddings(Record):
    metadata = Metadata()
    entities = Array(EntityEmbeddings())

############################################################################

# Graph embeddings query

class GraphEmbeddingsRequest(Record):
    vectors = Array(Array(Double()))
    limit = Integer()
    user = String()
    collection = String()

class GraphEmbeddingsResponse(Record):
    error = Error()
    entities = Array(Value())

############################################################################

# Graph triples

class Triples(Record):
    metadata = Metadata()
    triples = Array(Triple())

############################################################################

# Triples query

class TriplesQueryRequest(Record):
    s = Value()
    p = Value()
    o = Value()
    limit = Integer()
    user = String()
    collection = String()

class TriplesQueryResponse(Record):
    error = Error()
    triples = Array(Triple())

