
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

