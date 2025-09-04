from pulsar.schema import Record, String, Array, Map, Integer, Double

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# NLP to Structured Query Service - converts natural language to GraphQL

class QuestionToStructuredQueryRequest(Record):
    question = String()
    max_results = Integer()

class QuestionToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # Generated GraphQL query
    variables = Map(String())  # GraphQL variables if any
    detected_schemas = Array(String())  # Which schemas the query targets
    confidence = Double()

############################################################################
