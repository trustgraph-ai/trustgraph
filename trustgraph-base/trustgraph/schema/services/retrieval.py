from dataclasses import dataclass
from ..core.topic import topic
from ..core.primitives import Error, Term

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
    explain_id: str | None = None     # Single explain URI (announced as created)
    explain_graph: str | None = None  # Named graph where explain was stored (e.g., urn:graph:retrieval)
    message_type: str = ""            # "chunk" or "explain"
    end_of_session: bool = False      # Entire session complete

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
    explain_id: str | None = None     # Single explain URI (announced as created)
    explain_graph: str | None = None  # Named graph where explain was stored (e.g., urn:graph:retrieval)
    message_type: str = ""            # "chunk" or "explain"
    end_of_session: bool = False      # Entire session complete
