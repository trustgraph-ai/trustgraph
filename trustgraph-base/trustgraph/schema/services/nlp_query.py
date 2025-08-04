from pulsar.schema import Record, String, Array, Map, Integer, Double

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# NLP to Structured Query Service - converts natural language to GraphQL

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # Optional context for query generation

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # Generated GraphQL query
    variables = Map(String())  # GraphQL variables if any
    detected_schemas = Array(String())  # Which schemas the query targets
    confidence = Double()

############################################################################