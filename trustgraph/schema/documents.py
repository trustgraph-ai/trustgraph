
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double
from . topic import topic
from . types import Error

class Source(Record):
    source = String()
    id = String()
    title = String()

############################################################################

# PDF docs etc.
class Document(Record):
    source = Source()
    data = Bytes()

document_ingest_queue = topic('document-load')

############################################################################

# Text documents / text from PDF

class TextDocument(Record):
    source = Source()
    text = Bytes()

text_ingest_queue = topic('text-document-load')

############################################################################

# Chunks of text

class Chunk(Record):
    source = Source()
    chunk = Bytes()

chunk_ingest_queue = topic('chunk-load')

############################################################################

# Chunk embeddings are an embeddings associated with a text chunk

class ChunkEmbeddings(Record):
    source = Source()
    vectors = Array(Array(Double()))
    chunk = Bytes()

chunk_embeddings_ingest_queue = topic('chunk-embeddings-load')

############################################################################

# Doc embeddings query

class DocumentEmbeddingsRequest(Record):
    vectors = Array(Array(Double()))
    limit = Integer()

class DocumentEmbeddingsResponse(Record):
    error = Error()
    documents = Array(Bytes())

document_embeddings_request_queue = topic(
    'doc-embeddings', kind='non-persistent', namespace='request'
)
document_embeddings_response_queue = topic(
    'doc-embeddings-response', kind='non-persistent', namespace='response', 
)
