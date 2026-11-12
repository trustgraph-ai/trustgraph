
from dataclasses import dataclass, field

from .core.primitives import Error
from .core.topic import queue

############################################################################

# NL-to-SPARQL translation service - converts natural language questions
# to SPARQL queries using ontology context and entity resolution.

@dataclass
class ResolvedEntity:
    mention: str = ""
    uri: str = ""
    rdf_type: str = ""
    score: float = 0.0

@dataclass
class QuestionToSparqlRequest:
    question: str = ""
    collection: str = ""
    limit: int = 10

@dataclass
class QuestionToSparqlResponse:
    error: Error | None = None
    sparql: str = ""
    resolved_entities: list[ResolvedEntity] = field(default_factory=list)

############################################################################

# Queue definitions

nl_sparql_request_queue = queue('nl-sparql', cls='request')
nl_sparql_response_queue = queue('nl-sparql', cls='response')

############################################################################

# SPARQL NL Query orchestration service - chains NL-to-SPARQL translation
# with SPARQL execution to answer natural language questions via SPARQL.

@dataclass
class SparqlNLQueryRequest:
    question: str = ""
    collection: str = ""
    limit: int = 10

@dataclass
class SparqlNLQueryResponse:
    error: Error | None = None
    sparql: str = ""
    resolved_entities: list[ResolvedEntity] = field(default_factory=list)
    query_type: str = ""
    variables: list[str] = field(default_factory=list)
    bindings: list[list[str]] = field(default_factory=list)
    ask_result: bool = False

############################################################################

# Queue definitions

sparql_nl_query_request_queue = queue('sparql-nl-query', cls='request')
sparql_nl_query_response_queue = queue('sparql-nl-query', cls='response')
