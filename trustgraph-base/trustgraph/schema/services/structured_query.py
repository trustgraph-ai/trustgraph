from pulsar.schema import Record, String, Map, Array

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Structured Query Service - executes GraphQL queries

class StructuredQueryRequest(Record):
    question = String()

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # JSON-encoded GraphQL response data
    errors = Array(String())  # GraphQL errors if any

############################################################################
