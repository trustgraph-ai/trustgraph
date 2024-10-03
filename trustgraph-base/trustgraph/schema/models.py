
from pulsar.schema import Record, String, Array, Double, Integer

from . topic import topic
from . types import Error

############################################################################

# LLM text completion

class TextCompletionRequest(Record):
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()

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
