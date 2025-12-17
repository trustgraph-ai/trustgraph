from dataclasses import dataclass, field

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# NLP to Structured Query Service - converts natural language to GraphQL

@dataclass
class QuestionToStructuredQueryRequest:
    question: str = ""
    max_results: int = 0

@dataclass
class QuestionToStructuredQueryResponse:
    error: Error | None = None
    graphql_query: str = ""  # Generated GraphQL query
    variables: dict[str, str] = field(default_factory=dict)  # GraphQL variables if any
    detected_schemas: list[str] = field(default_factory=list)  # Which schemas the query targets
    confidence: float = 0.0

############################################################################

