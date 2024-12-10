
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double

from . types import Error, Value, Triple
from . topic import topic
from . metadata import Metadata

############################################################################

# Graph embeddings are embeddings associated with a graph entity

class GraphEmbeddings(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    entity = Value()

graph_embeddings_store_queue = topic('graph-embeddings-store')

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

graph_embeddings_request_queue = topic(
    'graph-embeddings', kind='non-persistent', namespace='request'
)
graph_embeddings_response_queue = topic(
    'graph-embeddings', kind='non-persistent', namespace='response'
)

############################################################################

# Graph triples

class Triples(Record):
    metadata = Metadata()
    triples = Array(Triple())

triples_store_queue = topic('triples-store')

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

triples_request_queue = topic(
    'triples', kind='non-persistent', namespace='request'
)
triples_response_queue = topic(
    'triples', kind='non-persistent', namespace='response'
)
