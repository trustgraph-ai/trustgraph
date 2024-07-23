
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

class Document(Record):
    source = Source()
    data = Bytes()

document_ingest_queue = 'document-load'
text_ingest_queue = 'text-document-load'

class TextDocument(Record):
    source = Source()
    text = Bytes()

chunk_ingest_queue = 'chunk-load'

class Chunk(Record):
    source = Source()
    chunk = Bytes()

class ChunkEmbeddings(Record):
    source = Source()
    vectors = Array(Array(Double()))
    chunk = Bytes()

chunk_embeddings_ingest_queue = 'chunk-embeddings-load'

class GraphEmbeddings(Record):
    source = Source()
    vectors = Array(Array(Double()))
    entity = Value()

class Triple(Record):
    source = Source()
    s = Value()
    p = Value()
    o = Value()

triples_store_queue = 'triples-store'

# chunk_embeddings_store_queue = 'chunk-embeddings-store'
graph_embeddings_store_queue = 'graph-embeddings-store'

text_completion_request_queue = 'text-completion'
text_completion_response_queue = 'text-completion-response'

class TextCompletionRequest(Record):
    prompt = String()

class TextCompletionResponse(Record):
    response = String()

class EmbeddingsRequest(Record):
    text = String()

class EmbeddingsResponse(Record):
    vectors = Array(Array(Double()))

class GraphRagQuery(Record):
    query = String()

class GraphRagResponse(Record):
    response = String()

graph_rag_request_queue = 'graph-rag'
graph_rag_response_queue = 'graph-rag-response'

