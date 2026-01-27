from dataclasses import dataclass

from ..core.primitives import Error, Term, Triple
from ..core.topic import topic
from ..core.metadata import Metadata

############################################################################

# Lookups

@dataclass
class LookupRequest:
    kind: str = ""
    term: str = ""

@dataclass
class LookupResponse:
    text: str = ""
    error: Error | None = None

############################################################################
