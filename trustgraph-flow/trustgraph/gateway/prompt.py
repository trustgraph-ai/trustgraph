
import json

from .. schema import PromptRequest, PromptResponse

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class PromptRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout, auth,
            consumer, subscriber,
    ):

        super(PromptRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=PromptRequest,
            response_schema=PromptResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

    def to_request(self, body):
        return PromptRequest(
            id=body["id"],
            terms={
                k: json.dumps(v)
                for k, v in body["variables"].items()
            }
        )

    def from_response(self, message):
        if message.object:
            return {
                "object": message.object
            }, True
        else:
            return {
                "text": message.text
            }, True

