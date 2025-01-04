
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double
from . topic import topic
from . types import Error
from . metadata import Metadata

############################################################################

# PDF docs etc.
class Document(Record):
    metadata = Metadata()
    data = Bytes()

document_ingest_queue = topic('document-load')

############################################################################

# Text documents / text from PDF

class TextDocument(Record):
    metadata = Metadata()
    text = Bytes()

text_ingest_queue = topic('text-document-load')

############################################################################

# Chunks of text

class Chunk(Record):
    metadata = Metadata()
    chunk = Bytes()

chunk_ingest_queue = topic('chunk-load')

############################################################################

# Document embeddings are embeddings associated with a chunk

class ChunkEmbeddings(Record):
    chunk = Bytes()
    vectors = Array(Array(Double()))

# This is a 'batching' mechanism for the above data
class DocumentEmbeddings(Record):
    metadata = Metadata()
    chunks = Array(ChunkEmbeddings())

document_embeddings_store_queue = topic('document-embeddings-store')

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
    'doc-embeddings', kind='non-persistent', namespace='response',
)

