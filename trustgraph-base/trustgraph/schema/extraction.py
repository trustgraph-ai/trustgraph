
from dataclasses import dataclass, field

from .core.primitives import Error, Triple
from .core.topic import queue
from .triples import EntityContext

############################################################################

# Extraction service (request/response interface)
# Shared schema for definitions, relationships, and ontology extraction.

@dataclass
class ExtractionRequest:
    text: str = ""               # Text to extract from
    document_id: str = ""        # Source chunk document ID (for provenance)

@dataclass
class ExtractionResponse:
    error: Error | None = None
    kind: str = ""               # "triples", "entity-contexts", "provenance"
    triples: list[Triple] = field(default_factory=list)
    entity_contexts: list[EntityContext] = field(default_factory=list)
    end_of_stream: bool = False
