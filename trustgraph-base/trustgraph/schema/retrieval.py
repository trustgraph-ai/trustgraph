
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double
from . topic import topic
from . types import Error, Value

############################################################################

# Graph RAG text retrieval

class GraphRagQuery(Record):
    query = String()
    user = String()
    collection = String()
    entity_limit = Integer()
    triple_limit = Integer()
    max_subgraph_size = Integer()
    max_path_length = Integer()

class GraphRagResponse(Record):
    error = Error()
    response = String()

graph_rag_request_queue = topic(
    'graph-rag', kind='non-persistent', namespace='request'
)
graph_rag_response_queue = topic(
    'graph-rag', kind='non-persistent', namespace='response'
)

############################################################################

# Document RAG text retrieval

class DocumentRagQuery(Record):
    query = String()
    user = String()
    collection = String()
    doc_limit = Integer()

class DocumentRagResponse(Record):
    error = Error()
    response = String()

document_rag_request_queue = topic(
    'doc-rag', kind='non-persistent', namespace='request'
)
document_rag_response_queue = topic(
    'doc-rag', kind='non-persistent', namespace='response'
)
