
from pulsar.schema import Record, Bytes, String, Array, Long, Boolean
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

class KnowledgeRequest(Record):

    # get-kg-core, delete-kg-core, list-kg-cores, put-kg-core
    # load-kg-core, unload-kg-core
    operation = String()

    # list-kg-cores, delete-kg-core, put-kg-core
    user = String()

    # get-kg-core, list-kg-cores, delete-kg-core, put-kg-core,
    # load-kg-core, unload-kg-core
    id = String()

    # load-kg-core
    flow = String()

    # load-kg-core
    collection = String()

    # put-kg-core
    triples = Triples()
    graph_embeddings = GraphEmbeddings()

class KnowledgeResponse(Record):
    error = Error()
    ids = Array(String())
    eos = Boolean()     # Indicates end of knowledge core stream
    triples = Triples()
    graph_embeddings = GraphEmbeddings()

knowledge_request_queue = topic(
    'knowledge', kind='non-persistent', namespace='request'
)
knowledge_response_queue = topic(
    'knowledge', kind='non-persistent', namespace='response',
)

