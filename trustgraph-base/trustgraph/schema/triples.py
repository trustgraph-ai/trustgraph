
from dataclasses import dataclass, field

from .core.primitives import Term, Triple, Error
from .core.metadata import Metadata
from .core.topic import queue
from .user_context import UserContext

############################################################################

# Entity context are an entity associated with textual context

@dataclass
class EntityContext:
    entity: Term | None = None
    context: str = ""
    # Provenance: which chunk this entity context was derived from
    chunk_id: str = ""
    rdf_type: list[str] = field(default_factory=list)
    attributes: dict[str, str | list[str]] = field(default_factory=dict)

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

# Graph triples query

@dataclass
class TriplesQueryRequest:
    collection: str = ""
    operation: str = ""      # "" = query (default), "version-bump", etc.
    s: Term | None = None
    p: Term | None = None
    o: Term | None = None
    g: str | None = None  # Query filter: None=all graphs, ""=default graph, "urn:..."=specific
    limit: int = 0
    streaming: bool = False  # Enable streaming mode (multiple batched responses)
    batch_size: int = 20     # Triples per batch in streaming mode
    named_graph: str = ""    # For version operations
    version: str = ""        # For version-label, revert, point-in-time queries
    name: str = ""           # For version-label (symbolic name)
    v1: int = 0              # For diff (first version)
    v2: int = 0              # For diff (second version)
    triples: list[Triple] = field(default_factory=list)  # For delete (explicit)
    user_context: UserContext | None = None

@dataclass
class VersionEntry:
    version: int = 0
    created_at: str = ""
    names: list[str] = field(default_factory=list)
    description: str = ""

@dataclass
class TriplesQueryResponse:
    error: Error | None = None
    triples: list[Triple] = field(default_factory=list)
    is_final: bool = True    # False for intermediate batches in streaming mode
    version: int = 0         # Returned by version operations
    version_map: dict[str, int] = field(default_factory=dict)
    version_log: list[VersionEntry] = field(default_factory=list)
    added: list[Triple] = field(default_factory=list)    # For diff results
    removed: list[Triple] = field(default_factory=list)  # For diff results

############################################################################

# SPARQL query

@dataclass
class SparqlBinding:
    """A single row of SPARQL SELECT results.
    Values are ordered to match the variables list in SparqlQueryResponse.
    """
    values: list[Term | None] = field(default_factory=list)

@dataclass
class SparqlQueryRequest:
    collection: str = ""
    query: str = ""           # SPARQL query string
    limit: int = 10000        # Safety limit on results
    streaming: bool = False   # Enable streaming mode
    batch_size: int = 20      # Bindings per batch in streaming mode
    user_context: UserContext | None = None

@dataclass
class SparqlQueryResponse:
    error: Error | None = None
    query_type: str = ""      # "select", "ask", "construct", "describe"

    # For SELECT queries
    variables: list[str] = field(default_factory=list)
    bindings: list[SparqlBinding] = field(default_factory=list)

    # For ASK queries
    ask_result: bool = False

    # For CONSTRUCT/DESCRIBE queries
    triples: list[Triple] = field(default_factory=list)

    is_final: bool = True     # False for intermediate batches in streaming

sparql_query_request_queue = queue('sparql-query', cls='request')
sparql_query_response_queue = queue('sparql-query', cls='response')

############################################################################
