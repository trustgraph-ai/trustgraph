
from pulsar.schema import Record, String, Array, Double, Integer, Boolean

from ..core.topic import topic
from ..core.primitives import Error

############################################################################

# LLM text completion

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # Default false for backward compatibility

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # Indicates final message in stream

############################################################################

# Embeddings

class EmbeddingsRequest(Record):
    text = String()

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

