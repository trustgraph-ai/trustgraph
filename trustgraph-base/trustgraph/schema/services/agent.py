
from pulsar.schema import Record, String, Array, Map

from ..core.topic import topic
from ..core.primitives import Error

############################################################################

# Prompt services, abstract the prompt generation

class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()

############################################################################

