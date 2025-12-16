from dataclasses import dataclass, field
from ..core.primitives import Error

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

