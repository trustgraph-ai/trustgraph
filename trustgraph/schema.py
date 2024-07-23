
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double

from enum import Enum

############################################################################

class Value(Record):
    value = String()
    is_uri = Boolean()
    type = String()

class Source(Record):
    source = String()
    id = String()
    title = String()

############################################################################

# PDF docs etc.
class Document(Record):
    source = Source()
    data = Bytes()

document_ingest_queue = 'document-load'

############################################################################

# Text documents / text from PDF

class TextDocument(Record):
    source = Source()
    text = Bytes()

text_ingest_queue = 'text-document-load'

############################################################################

# Chunks of text

class Chunk(Record):
    source = Source()
    chunk = Bytes()

chunk_ingest_queue = 'chunk-load'

############################################################################

# Chunk embeddings are an embeddings associated with a text chunk

class ChunkEmbeddings(Record):
    source = Source()
    vectors = Array(Array(Double()))
    chunk = Bytes()

chunk_embeddings_ingest_queue = 'chunk-embeddings-load'

############################################################################

# Graph embeddings are embeddings associated with a graph entity

class GraphEmbeddings(Record):
    source = Source()
    vectors = Array(Array(Double()))
    entity = Value()

graph_embeddings_store_queue = 'graph-embeddings-store'

############################################################################

# Graph triples

class Triple(Record):
    source = Source()
    s = Value()
    p = Value()
    o = Value()

triples_store_queue = 'triples-store'

############################################################################

# chunk_embeddings_store_queue = 'chunk-embeddings-store'

############################################################################

# LLM text completion

class TextCompletionRequest(Record):
    prompt = String()

class TextCompletionResponse(Record):
    response = String()

text_completion_request_queue = 'text-completion'
text_completion_response_queue = 'text-completion-response'

############################################################################

# Embeddings

class EmbeddingsRequest(Record):
    text = String()

class EmbeddingsResponse(Record):
    vectors = Array(Array(Double()))

embeddings_request_queue = 'embeddings'
embeddings_response_queue = 'embeddings-response'

############################################################################

# Graph RAG text retrieval

class GraphRagQuery(Record):
    query = String()

class GraphRagResponse(Record):
    response = String()

graph_rag_request_queue = 'graph-rag'
graph_rag_response_queue = 'graph-rag-response'

############################################################################

