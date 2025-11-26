
from pulsar.schema import Record, String, Array, Map, Boolean

from ..core.topic import topic
from ..core.primitives import Error

############################################################################

# Prompt services, abstract the prompt generation

class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()              # User context for the step

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()              # User context for multi-tenancy
    streaming = Boolean()        # NEW: Enable streaming response delivery (default false)

class AgentResponse(Record):
    # Streaming-first design
    chunk_type = String()        # "thought", "action", "observation", "answer", "error"
    content = String()           # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()   # Current chunk type (thought/action/etc.) is complete
    end_of_dialog = Boolean()    # Entire agent dialog is complete

    # Legacy fields (deprecated but kept for backward compatibility)
    answer = String()
    error = Error()
    thought = String()
    observation = String()

############################################################################

