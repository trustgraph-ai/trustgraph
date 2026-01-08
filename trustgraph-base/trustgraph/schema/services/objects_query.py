from dataclasses import dataclass, field
from typing import Optional

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Objects Query Service - executes GraphQL queries against structured data

@dataclass
class GraphQLError:
    message: str = ""
    path: list[str] = field(default_factory=list)       # Path to the field that caused the error
    extensions: dict[str, str] = field(default_factory=dict)   # Additional error metadata

@dataclass
class ObjectsQueryRequest:
    user: str = ""              # Cassandra keyspace (follows pattern from TriplesQueryRequest)
    collection: str = ""        # Data collection identifier (required for partition key)
    query: str = ""             # GraphQL query string
    variables: dict[str, str] = field(default_factory=dict)    # GraphQL variables
    operation_name: Optional[str] = None    # Operation to execute for multi-operation documents

@dataclass
class ObjectsQueryResponse:
    error: Error | None = None              # System-level error (connection, timeout, etc.)
    data: str = ""              # JSON-encoded GraphQL response data
    errors: list[GraphQLError] = field(default_factory=list) # GraphQL field-level errors
    extensions: dict[str, str] = field(default_factory=dict)   # Query metadata (execution time, etc.)

############################################################################
