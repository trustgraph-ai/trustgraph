
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double
from . topic import topic
from . types import Error
from . metadata import Metadata

############################################################################

# PDF docs etc.
class Document(Record):
    metadata = Metadata()
    data = Bytes()

############################################################################

# Text documents / text from PDF

class TextDocument(Record):
    metadata = Metadata()
    text = Bytes()

############################################################################

# Chunks of text

class Chunk(Record):
    metadata = Metadata()
    chunk = Bytes()

############################################################################

# Document embeddings are embeddings associated with a chunk

class ChunkEmbeddings(Record):
    chunk = Bytes()
    vectors = Array(Array(Double()))

# This is a 'batching' mechanism for the above data
class DocumentEmbeddings(Record):
    metadata = Metadata()
    chunks = Array(ChunkEmbeddings())

############################################################################

# Doc embeddings query

class DocumentEmbeddingsRequest(Record):
    vectors = Array(Array(Double()))
    limit = Integer()
    user = String()
    collection = String()

class DocumentEmbeddingsResponse(Record):
    error = Error()
    documents = Array(Bytes())

