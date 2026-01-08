from dataclasses import dataclass, field
from .primitives import Triple

@dataclass
class Metadata:
    # Source identifier
    id: str = ""

    # Subgraph
    metadata: list[Triple] = field(default_factory=list)

    # Collection management
    user: str = ""
    collection: str = ""
