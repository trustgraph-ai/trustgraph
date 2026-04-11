from dataclasses import dataclass, field
from ..core.primitives import Error, Term, Triple

############################################################################

# Graph RAG text retrieval

@dataclass
class GraphRagQuery:
    query: str = ""
    user: str = ""
    collection: str = ""
    entity_limit: int = 0
    triple_limit: int = 0
    max_subgraph_size: int = 0
    max_path_length: int = 0
    edge_score_limit: int = 0
    edge_limit: int = 0
    streaming: bool = False
    parent_uri: str = ""

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

############################################################################

# Document RAG text retrieval

@dataclass
class DocumentRagQuery:
    query: str = ""
    user: str = ""
    collection: str = ""
    doc_limit: int = 0
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
