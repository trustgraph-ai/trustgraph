
from ... schema import AgentRequest, AgentResponse
from ... schema import agent_request_queue
from ... schema import agent_response_queue

from . endpoint import MultiResponseServiceEndpoint

class AgentEndpoint(MultiResponseServiceEndpoint):
    def __init__(self, pulsar_host, timeout, auth):

        super(AgentEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=agent_request_queue,
            response_queue=agent_response_queue,
            request_schema=AgentRequest,
            response_schema=AgentResponse,
            endpoint_path="/api/v1/agent",
            timeout=timeout,
            auth=auth,
        )

    def to_request(self, body):
        return AgentRequest(
            question=body["question"]
        )

    def from_response(self, message):
        if message.answer:
            return { "answer": message.answer }, True
        else:
            return {}, False
