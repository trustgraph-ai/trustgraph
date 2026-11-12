
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Ontology service - manages ontology parsing, embedding, and subset
# selection.  Single request/response queue with an operation field.

@dataclass
class OntologyInfo:
    ontology_id: str = ""
    state: str = ""  # "loading", "ready", or "error"
    classes_total: int = 0
    properties_total: int = 0
    elements_embedded: int = 0
    error_message: str = ""

@dataclass
class OntologyRequest:
    operation: str = ""  # "subset" or "list"

    # For "subset" operation
    text: str = ""
    top_k: int = 10
    similarity_threshold: float = 0.3

@dataclass
class OntologyResponse:
    error: Error | None = None
    operation: str = ""

    # For "subset" operation
    ontology_id: str = ""
    classes: dict[str, str] = field(default_factory=dict)
    object_properties: dict[str, str] = field(default_factory=dict)
    datatype_properties: dict[str, str] = field(default_factory=dict)
    namespace: str = ""

    # For "list" operation
    ontologies: list[OntologyInfo] = field(default_factory=list)

############################################################################

# Queue definitions

ontology_request_queue = queue('ontology', cls='request')
ontology_response_queue = queue('ontology', cls='response')
