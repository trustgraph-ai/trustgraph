
from dataclasses import dataclass, field
from typing import Optional

from .core.primitives import Error, Term, Triple
from .user_context import UserContext

############################################################################

# Graph RAG text retrieval

@dataclass
class TraversalStep:
    types: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    graphs: list[str] = field(default_factory=list)

@dataclass
class GraphRagQuery:
    query: str = ""
    collection: str = ""
    entity_limit: int = 0
    triple_limit: int = 0
    max_subgraph_size: int = 0
    max_path_length: int = 0
    edge_score_limit: int = 0
    edge_limit: int = 0
    max_reranker_input: int = 0
    streaming: bool = False
    parent_uri: str = ""
    user_context: UserContext | None = None
    grounding_seeds: list[str] = field(default_factory=list)
    graph_seeds: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    traversal_instructions: list[TraversalStep] = field(default_factory=list)
    graph: str | None = None

@dataclass
class Source:
    uri: str = ""     # Source document URI
    title: str = ""   # Document title (empty when the document has none)

@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False       # LLM response stream complete
    explain_id: str | None = None     # Root URI for this explain step
    explain_graph: str | None = None  # Named graph (e.g., urn:graph:retrieval)
    explain_triples: list[Triple] = field(default_factory=list)  # Provenance triples for this step
    message_type: str = ""            # "chunk" or "explain"
    end_of_session: bool = False      # Entire session complete
    in_token: int | None = None
    out_token: int | None = None
    model: str | None = None
    sources: list[Source] = field(default_factory=list)  # Source documents, on the final message

############################################################################

# Document RAG text retrieval

@dataclass
class DocumentRagQuery:
    query: str = ""
    collection: str = ""
    doc_limit: int = 0        # docs selected into the synthesis prompt
    fetch_limit: int = 0      # candidate pool fetched from the vector store
                              # before reranking (0 = derive from doc_limit;
                              # values below doc_limit are raised to it)
    streaming: bool = False

@dataclass
class DocumentRagResponse:
    error: Error | None = None
    response: str | None = ""
    end_of_stream: bool = False       # LLM response stream complete
    explain_id: str | None = None     # Root URI for this explain step
    explain_graph: str | None = None  # Named graph (e.g., urn:graph:retrieval)
    explain_triples: list[Triple] = field(default_factory=list)  # Provenance triples for this step
    message_type: str = ""            # "chunk" or "explain"
    end_of_session: bool = False      # Entire session complete
    in_token: int | None = None
    out_token: int | None = None
    model: str | None = None

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
