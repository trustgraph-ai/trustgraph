from dataclasses import dataclass, field

from ..core.primitives import Error, Term, Triple
from ..core.topic import queue

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
