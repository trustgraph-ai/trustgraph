
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double

from . documents import Source
from . types import Error, Value
from . topic import topic

############################################################################

# Graph embeddings are embeddings associated with a graph entity

class GraphEmbeddings(Record):
    source = Source()
    vectors = Array(Array(Double()))
    entity = Value()

graph_embeddings_store_queue = topic('graph-embeddings-store')

############################################################################

# Graph embeddings query

class GraphEmbeddingsRequest(Record):
    vectors = Array(Array(Double()))
    limit = Integer()

class GraphEmbeddingsResponse(Record):
    error = Error()
    entities = Array(Value())

graph_embeddings_request_queue = topic(
    'graph-embeddings', kind='non-persistent', namespace='request'
)
graph_embeddings_response_queue = topic(
    'graph-embeddings-response', kind='non-persistent', namespace='response', 
)

############################################################################

# Graph triples

class Triple(Record):
    source = Source()
    s = Value()
    p = Value()
    o = Value()

triples_store_queue = topic('triples-store')

############################################################################

# Triples query

class TriplesQueryRequest(Record):
    s = Value()
    p = Value()
    o = Value()
    limit = Integer()

class TriplesQueryResponse(Record):
    error = Error()
    triples = Array(Triple())

triples_request_queue = topic(
    'triples', kind='non-persistent', namespace='request'
)
triples_response_queue = topic(
    'triples-response', kind='non-persistent', namespace='response',
)
