from pulsar.schema import Record, String, Bytes, Map

from ..core.metadata import Metadata
from ..core.topic import topic

############################################################################

# Structured data submission for fire-and-forget processing

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # Reference to schema in config
    data = Bytes()  # Raw data to ingest
    options = Map(String())  # Format-specific options

############################################################################