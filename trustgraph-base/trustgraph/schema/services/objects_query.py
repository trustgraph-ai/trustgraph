from pulsar.schema import Record, String, Map, Array

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Objects Query Service - executes GraphQL queries against structured data

class GraphQLError(Record):
    message = String()
    path = Array(String())       # Path to the field that caused the error
    extensions = Map(String())   # Additional error metadata

class ObjectsQueryRequest(Record):
    user = String()              # Cassandra keyspace (follows pattern from TriplesQueryRequest)
    collection = String()        # Data collection identifier (required for partition key)
    query = String()             # GraphQL query string
    variables = Map(String())    # GraphQL variables
    operation_name = String()    # Operation to execute for multi-operation documents

class ObjectsQueryResponse(Record):
    error = Error()              # System-level error (connection, timeout, etc.)
    data = String()              # JSON-encoded GraphQL response data
    errors = Array(GraphQLError()) # GraphQL field-level errors
    extensions = Map(String())   # Query metadata (execution time, etc.)

############################################################################