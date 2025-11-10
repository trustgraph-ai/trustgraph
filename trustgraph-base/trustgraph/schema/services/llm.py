
from pulsar.schema import Record, String, Array, Double, Integer

from ..core.topic import topic
from ..core.primitives import Error

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
    model = String(required=False, default="")  # Optional model name to use for this request

class EmbeddingsResponse(Record):
    error = Error()
    vectors = Array(Array(Double()))

############################################################################

# Tool request/response

class ToolRequest(Record):
    name = String()

    # Parameters are JSON encoded
    parameters = String()

class ToolResponse(Record):
    error = Error()

    # Plain text aka "unstructured"
    text = String()

    # JSON-encoded object aka "structured"
    object = String()

