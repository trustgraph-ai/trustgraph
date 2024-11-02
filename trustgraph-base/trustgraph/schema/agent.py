
from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer

from . topic import topic
from . types import Error, RowSchema

############################################################################

# Prompt services, abstract the prompt generation

class AgentStep(Record):
    thought = String()
    action = String()
    action_input = String()
    observation = String()

class AgentRequest(Record):
    question = String()
    plan = String()
    history = Array(AgentStep())

class AgentResponse(Record):
    answer = String()
    error = String()
    thought = String()

agent_request_queue = topic(
    'agent', kind='non-persistent', namespace='request'
)
agent_response_queue = topic(
    'agent', kind='non-persistent', namespace='response'
)

############################################################################

