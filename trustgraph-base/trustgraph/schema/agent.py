
from pulsar.schema import Record, String, Array, Map

from . topic import topic
from . types import Error

############################################################################

# Prompt services, abstract the prompt generation

class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()

class AgentRequest(Record):
    question = String()
    plan = String()
    state = String()
    history = Array(AgentStep())

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()

agent_request_queue = topic(
    'agent', kind='non-persistent', namespace='request'
)
agent_response_queue = topic(
    'agent', kind='non-persistent', namespace='response'
)

############################################################################

