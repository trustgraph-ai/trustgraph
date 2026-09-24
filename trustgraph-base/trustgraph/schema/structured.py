
from dataclasses import dataclass, field
from typing import Optional

from .core.metadata import Metadata
from .core.primitives import Error, RowSchema

############################################################################

# Extracted object from text processing

@dataclass
class ExtractedObject:
    metadata: Metadata | None = None
    schema_name: str = ""  # Which schema this object belongs to
    values: list[dict[str, str]] = field(default_factory=list)  # Array of objects, each object is field name -> value
    confidence: float = 0.0
    source_span: str = ""  # Text span where object was found

############################################################################

# Stores rows of information

@dataclass
class Rows:
    metadata: Metadata | None = None
    row_schema: RowSchema | None = None
    rows: list[dict[str, str]] = field(default_factory=list)

############################################################################

# Structured data submission for fire-and-forget processing

@dataclass
class StructuredDataSubmission:
    metadata: Metadata | None = None
    format: str = ""  # "json", "csv", "xml"
    schema_name: str = ""  # Reference to schema in config
    data: bytes = b""  # Raw data to ingest
    options: dict[str, str] = field(default_factory=dict)  # Format-specific options

############################################################################

# Structured data diagnosis services

@dataclass
class StructuredDataDiagnosisRequest:
    operation: str = ""  # "detect-type", "generate-descriptor", "diagnose", or "schema-selection"
    sample: str = ""     # Data sample to analyze (text content)
    type: str = ""       # Data type (csv, json, xml) - optional, required for generate-descriptor
    schema_name: str = "" # Target schema name for descriptor generation - optional

    # JSON encoded options (e.g., delimiter for CSV)
    options: dict[str, str] = field(default_factory=dict)

@dataclass
class StructuredDataDiagnosisResponse:
    error: Error | None = None

    operation: str = ""         # The operation that was performed
    detected_type: str = ""     # Detected data type (for detect-type/diagnose) - optional
    confidence: float = 0.0     # Confidence score for type detection - optional

    # JSON encoded descriptor (for generate-descriptor/diagnose) - optional
    descriptor: str = ""

    # JSON encoded additional metadata (e.g., field count, sample records)
    metadata: dict[str, str] = field(default_factory=dict)

    # Array of matching schema IDs (for schema-selection operation) - optional
    schema_matches: list[str] = field(default_factory=list)

############################################################################

# Rows Query Service - executes GraphQL queries against structured data

@dataclass
class GraphQLError:
    message: str = ""
    path: list[str] = field(default_factory=list)       # Path to the field that caused the error
    extensions: dict[str, str] = field(default_factory=dict)   # Additional error metadata

@dataclass
class RowsQueryRequest:
    collection: str = ""        # Data collection identifier (required for partition key)
    query: str = ""             # GraphQL query string
    variables: dict[str, str] = field(default_factory=dict)    # GraphQL variables
    operation_name: Optional[str] = None    # Operation to execute for multi-operation documents

@dataclass
class RowsQueryResponse:
    error: Error | None = None              # System-level error (connection, timeout, etc.)
    data: str = ""              # JSON-encoded GraphQL response data
    errors: list[GraphQLError] = field(default_factory=list) # GraphQL field-level errors
    extensions: dict[str, str] = field(default_factory=dict)   # Query metadata (execution time, etc.)

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

# Structured Query Service - executes GraphQL queries

@dataclass
class StructuredQueryRequest:
    question: str = ""
    collection: str = ""  # Data collection identifier

@dataclass
class StructuredQueryResponse:
    error: Error | None = None
    data: str = ""  # JSON-encoded GraphQL response data
    errors: list[str] = field(default_factory=list)  # GraphQL errors if any

############################################################################
