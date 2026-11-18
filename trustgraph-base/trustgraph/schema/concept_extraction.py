
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Concept extraction request/response

@dataclass
class ConceptExtractionRequest:
    query: str = ""

@dataclass
class ConceptExtractionResponse:
    error: Error | None = None
    concepts: list[str] = field(default_factory=list)

concept_extraction_request_queue = queue('concept-extraction', cls='request')
concept_extraction_response_queue = queue('concept-extraction', cls='response')

############################################################################
