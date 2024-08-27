
from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer

from . topic import topic
from . types import Error, RowSchema

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
# kg-prompt:
#   query, triples -> answer
# document-prompt:
#   query, documents -> answer
# extract-rows
#   schema, chunk -> rows

class PromptRequest(Record):
    kind = String()
    chunk = String()
    query = String()
    kg = Array(Fact())
    documents = Array(Bytes())
    row_schema = RowSchema()

class PromptResponse(Record):
    error = Error()
    answer = String()
    definitions = Array(Definition())
    relationships = Array(Relationship())
    rows = Array(Map(String()))

prompt_request_queue = topic(
    'prompt', kind='non-persistent', namespace='request'
)
prompt_response_queue = topic(
    'prompt-response', kind='non-persistent', namespace='response'
)

############################################################################

