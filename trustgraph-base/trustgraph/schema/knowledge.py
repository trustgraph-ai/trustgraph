
from pulsar.schema import Record, Bytes, String, Array, Long, Boolean
from . types import Triple
from . topic import topic
from . types import Error
from . metadata import Metadata
from . documents import Document, TextDocument
from . graph import Triples, GraphEmbeddings

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
    operation = String()

    # list-kg-cores, delete-kg-core, put-kg-core
    user = String()

    # get-kg-core, list-kg-cores, delete-kg-core, put-kg-core
    id = String()

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

