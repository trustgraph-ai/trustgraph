from dataclasses import dataclass, field
from ..core.primitives import Triple, Error
from ..core.topic import topic
from ..core.metadata import Metadata
from .document import Document, TextDocument
from .graph import Triples
from .embeddings import GraphEmbeddings

# get-kg-core
#   -> (???)
#   <- ()
#   <- (error)

# delete-kg-core
#   -> (???)
#   <- ()
#   <- (error)

# list-kg-cores
#   -> (user)
#   <- ()
#   <- (error)

@dataclass
class KnowledgeRequest:
    # get-kg-core, delete-kg-core, list-kg-cores, put-kg-core
    # load-kg-core, unload-kg-core
    operation: str = ""

    # list-kg-cores, delete-kg-core, put-kg-core
    user: str = ""

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

@dataclass
class KnowledgeResponse:
    error: Error | None = None
    ids: list[str] = field(default_factory=list)
    eos: bool = False     # Indicates end of knowledge core stream
    triples: Triples | None = None
    graph_embeddings: GraphEmbeddings | None = None

knowledge_request_queue = topic(
    'knowledge', qos='q0', namespace='request'
)
knowledge_response_queue = topic(
    'knowledge', qos='q0', namespace='response',
)
