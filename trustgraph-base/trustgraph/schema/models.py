
from pulsar.schema import Record, String, Array, Double, Integer

from . topic import topic
from . types import Error

############################################################################

# LLM text completion

class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()

############################################################################

# Embeddings

class EmbeddingsRequest(Record):
    text = String()

class EmbeddingsResponse(Record):
    error = Error()
    vectors = Array(Array(Double()))

