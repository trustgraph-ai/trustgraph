
from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer

from . topic import topic
from . types import Error, RowSchema

############################################################################

# Prompt services, abstract the prompt generation

class Definition(Record):
    name = String()
    definition = String()

class Topic(Record):
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
    id = String()

    # JSON encoded values
    terms = Map(String())

class PromptResponse(Record):

    # Error case
    error = Error()

    # Just plain text
    text = String()

    # JSON encoded
    object = String()

############################################################################

