from dataclasses import dataclass, field

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Structured Query Service - executes GraphQL queries

@dataclass
class StructuredQueryRequest:
    question: str = ""
    user: str = ""        # Cassandra keyspace identifier
    collection: str = ""  # Data collection identifier

@dataclass
class StructuredQueryResponse:
    error: Error | None = None
    data: str = ""  # JSON-encoded GraphQL response data
    errors: list[str] = field(default_factory=list)  # GraphQL errors if any

############################################################################

