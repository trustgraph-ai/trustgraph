from dataclasses import dataclass, field

from ..core.primitives import Value, Triple
from ..core.metadata import Metadata
from ..core.topic import topic

############################################################################

# Entity context are an entity associated with textual context

@dataclass
class EntityContext:
    entity: Value | None = None
    context: str = ""

# This is a 'batching' mechanism for the above data
@dataclass
class EntityContexts:
    metadata: Metadata | None = None
    entities: list[EntityContext] = field(default_factory=list)

############################################################################

# Graph triples

@dataclass
class Triples:
    metadata: Metadata | None = None
    triples: list[Triple] = field(default_factory=list)

############################################################################
