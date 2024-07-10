
from pulsar.schema import Record, Bytes, String, Boolean, Integer, Array, Double

from enum import Enum

#class Command(Enum):
#    reindex = 1

#class IndexCommand(Record):
#    command = Command

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

class TextDocument(Record):
    source = Source()
    text = Bytes()

class Chunk(Record):
    source = Source()
    chunk = Bytes()

class VectorsChunk(Record):
    source = Source()
    vectors = Array(Array(Double()))
    chunk = Bytes()

class VectorsAssociation(Record):
    source = Source()
    vectors = Array(Array(Double()))
    entity = Value()

class Triple(Record):
    source = Source()
    s = Value()
    p = Value()
    o = Value()

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

