from dataclasses import dataclass, field
from ..core.primitives import Triple, Error
from ..core.topic import queue
from ..core.metadata import Metadata
from .document import Document, TextDocument
from .graph import Triples
from .embeddings import GraphEmbeddings, DocumentEmbeddings

# get-kg-core
#   -> (???)
#   <- ()
#   <- (error)

# delete-kg-core
#   -> (???)
#   <- ()
#   <- (error)

# list-kg-cores
#   -> ()
#   <- ()
#   <- (error)

@dataclass
class LibraryMetadata:
    id: str = ""
    kind: str = ""
    title: str = ""
    parent_id: str = ""
    document_type: str = ""
    comments: str = ""
    tags: list[str] = field(default_factory=list)

@dataclass
class LibraryBlob:
    id: str = ""
    data: bytes = b""

@dataclass
class KnowledgeRequest:
    # get-kg-core, delete-kg-core, list-kg-cores, put-kg-core
    # load-kg-core, unload-kg-core
    operation: str = ""

    # get-kg-core, list-kg-cores, delete-kg-core, put-kg-core,
    # load-kg-core, unload-kg-core
    id: str = ""

    # load-kg-core
    flow: str = ""

    # load-kg-core
    collection: str = ""

    # put-kg-core
    triples: Triples | None = None
    graph_embeddings: GraphEmbeddings | None = None

    # put-de-core
    document_embeddings: DocumentEmbeddings | None = None

    # put-kg-core (source material)
    library_metadata: LibraryMetadata | None = None
    library_blob: LibraryBlob | None = None

@dataclass
class KnowledgeResponse:
    error: Error | None = None
    ids: list[str] | None = None
    eos: bool = False     # Indicates end of knowledge core stream
    triples: Triples | None = None
    graph_embeddings: GraphEmbeddings | None = None
    document_embeddings: DocumentEmbeddings | None = None
    library_metadata: LibraryMetadata | None = None
    library_blob: LibraryBlob | None = None

knowledge_request_queue = queue('knowledge', cls='request')
knowledge_response_queue = queue('knowledge', cls='response')
