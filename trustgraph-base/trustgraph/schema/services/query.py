from pulsar.schema import Record, String, Integer, Array, Double

from ..core.primitives import Error, Value, Triple
from ..core.topic import topic

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

# Graph triples query

class TriplesQueryRequest(Record):
    user = String()
    collection = String()
    s = Value()
    p = Value()
    o = Value()
    limit = Integer()

class TriplesQueryResponse(Record):
    error = Error()
    triples = Array(Triple())

############################################################################

# Doc embeddings query

class DocumentEmbeddingsRequest(Record):
    vectors = Array(Array(Double()))
    limit = Integer()
    user = String()
    collection = String()

class DocumentEmbeddingsResponse(Record):
    error = Error()
    chunks = Array(String())