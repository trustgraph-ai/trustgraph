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
    streaming: bool = False

@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False

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
    response: str = ""
    end_of_stream: bool = False
