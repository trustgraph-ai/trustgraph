
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double

from enum import Enum

def topic(topic, kind='persistent', tenant='tg', namespace='flow'):
    return f"{kind}://{tenant}/{namespace}/{topic}"

############################################################################

class Error(Record):
    type = String()
    message = String()

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

# Graph embeddings are embeddings associated with a graph entity

class GraphEmbeddings(Record):
    source = Source()
    vectors = Array(Array(Double()))
    entity = Value()

graph_embeddings_store_queue = topic('graph-embeddings-store')

############################################################################

# Graph embeddings query

class GraphEmbeddingsRequest(Record):
    vectors = Array(Array(Double()))
    limit = Integer()

class GraphEmbeddingsResponse(Record):
    error = Error()
    entities = Array(Value())

graph_embeddings_request_queue = topic(
    'graph-embeddings', kind='non-persistent', namespace='request'
)
graph_embeddings_response_queue = topic(
    'graph-embeddings-response', kind='non-persistent', namespace='response', 
)

############################################################################

# Graph triples

class Triple(Record):
    source = Source()
    s = Value()
    p = Value()
    o = Value()

triples_store_queue = topic('triples-store')

############################################################################

# Triples query

class TriplesQueryRequest(Record):
    s = Value()
    p = Value()
    o = Value()
    limit = Integer()

class TriplesQueryResponse(Record):
    error = Error()
    triples = Array(Triple())

triples_request_queue = topic(
    'triples', kind='non-persistent', namespace='request'
)
triples_response_queue = topic(
    'triples-response', kind='non-persistent', namespace='response',
)

############################################################################

# chunk_embeddings_store_queue = topic('chunk-embeddings-store')

############################################################################

# LLM text completion

class TextCompletionRequest(Record):
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()

text_completion_request_queue = topic(
    'text-completion', kind='non-persistent', namespace='request'
)
text_completion_response_queue = topic(
    'text-completion-response', kind='non-persistent', namespace='response', 
)

############################################################################

# Embeddings

class EmbeddingsRequest(Record):
    text = String()

class EmbeddingsResponse(Record):
    error = Error()
    vectors = Array(Array(Double()))

embeddings_request_queue = topic(
    'embeddings', kind='non-persistent', namespace='request'
)
embeddings_response_queue = topic(
    'embeddings-response', kind='non-persistent', namespace='response'
)

############################################################################

# Graph RAG text retrieval

class GraphRagQuery(Record):
    query = String()

class GraphRagResponse(Record):
    error = Error()
    response = String()

graph_rag_request_queue = topic(
    'graph-rag', kind='non-persistent', namespace='request'
)
graph_rag_response_queue = topic(
    'graph-rag-response', kind='non-persistent', namespace='response'
)

############################################################################

# Prompt services, abstract the prompt generation

class Definition(Record):
    name = String()
    definition = String()

class Relationship(Record):
    s = String()
    p = String()
    o = String()
    o_entity = Boolean()

class Fact(Record):
    s = String()
    p = String()
    o = String()

# extract-definitions:
#   chunk -> definitions
# extract-relationships:
#   chunk -> relationships
# prompt-rag:
#   query, triples -> answer

class PromptRequest(Record):
    kind = String()
    chunk = String()
    query = String()
    kg = Array(Fact())

class PromptResponse(Record):
    error = Error()
    answer = String()
    definitions = Array(Definition())
    relationships = Array(Relationship())

prompt_request_queue = topic(
    'prompt', kind='non-persistent', namespace='request'
)
prompt_response_queue = topic(
    'prompt-response', kind='non-persistent', namespace='response'
)

############################################################################

