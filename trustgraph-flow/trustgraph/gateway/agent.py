
from .. schema import AgentRequest, AgentResponse
from .. schema import agent_request_queue
from .. schema import agent_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class AgentRequestor(ServiceRequestor):
    def __init__(self, pulsar_host, timeout, auth):

        super(AgentRequestor, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=agent_request_queue,
            response_queue=agent_response_queue,
            request_schema=AgentRequest,
            response_schema=AgentResponse,
            timeout=timeout,
        )

    def to_request(self, body):
        return AgentRequest(
            question=body["question"]
        )

    def from_response(self, message):
        resp = {
        }

        if message.answer:
            resp["answer"] = message.answer

        if message.thought:
            resp["thought"] = message.thought

        if message.observation:
            resp["observation"] = message.observation

        # The 2nd boolean expression indicates whether we're done responding
        return resp, (message.answer is not None)

    
