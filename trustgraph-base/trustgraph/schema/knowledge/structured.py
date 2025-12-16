from dataclasses import dataclass, field

from ..core.metadata import Metadata
from ..core.topic import topic

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

