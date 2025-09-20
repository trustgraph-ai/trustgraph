from pulsar.schema import Record, String, Map, Double, Array
from ..core.primitives import Error

############################################################################

# Structured data diagnosis services

class StructuredDataDiagnosisRequest(Record):
    operation = String()  # "detect-type", "generate-descriptor", "diagnose", or "schema-selection"
    sample = String()     # Data sample to analyze (text content)
    type = String()       # Data type (csv, json, xml) - optional, required for generate-descriptor
    schema_name = String() # Target schema name for descriptor generation - optional

    # JSON encoded options (e.g., delimiter for CSV)
    options = Map(String())

class StructuredDataDiagnosisResponse(Record):
    error = Error()

    operation = String()         # The operation that was performed
    detected_type = String()     # Detected data type (for detect-type/diagnose) - optional
    confidence = Double()        # Confidence score for type detection - optional

    # JSON encoded descriptor (for generate-descriptor/diagnose) - optional
    descriptor = String()

    # JSON encoded additional metadata (e.g., field count, sample records)
    metadata = Map(String())

    # Array of matching schema IDs (for schema-selection operation) - optional
    schema_matches = Array(String())

############################################################################