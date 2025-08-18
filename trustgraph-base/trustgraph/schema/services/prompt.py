from pulsar.schema import Record, String, Map

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Prompt services, abstract the prompt generation

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