
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double
from ..core.topic import topic
from ..core.primitives import Error, Value

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
    streaming = Boolean()

class GraphRagResponse(Record):
    error = Error()
    response = String()
    chunk = String()
    end_of_stream = Boolean()

############################################################################

# Document RAG text retrieval

class DocumentRagQuery(Record):
    query = String()
    user = String()
    collection = String()
    doc_limit = Integer()
    streaming = Boolean()

class DocumentRagResponse(Record):
    error = Error()
    response = String()
    chunk = String()
    end_of_stream = Boolean()

