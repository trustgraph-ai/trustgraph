
from ... schema import AgentRequest, AgentResponse

from . requestor import ServiceRequestor

class AgentRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(AgentRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=AgentRequest,
            response_schema=AgentResponse,
            subscription = subscriber,
            consumer_name = consumer,
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

