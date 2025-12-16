from dataclasses import dataclass, field

from ..core.metadata import Metadata
from ..core.primitives import RowSchema
from ..core.topic import topic

############################################################################

# Stores rows of information

@dataclass
class Rows:
    metadata: Metadata | None = None
    row_schema: RowSchema | None = None
    rows: list[dict[str, str]] = field(default_factory=list)

############################################################################
