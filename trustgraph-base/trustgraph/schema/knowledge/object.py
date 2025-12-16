from dataclasses import dataclass, field

from ..core.metadata import Metadata
from ..core.topic import topic

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

