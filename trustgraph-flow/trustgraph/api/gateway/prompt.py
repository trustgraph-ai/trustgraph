
import json

from ... schema import PromptRequest, PromptResponse
from ... schema import prompt_request_queue
from ... schema import prompt_response_queue

from . endpoint import ServiceEndpoint

class PromptEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout, auth):

        super(PromptEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=prompt_request_queue,
            response_queue=prompt_response_queue,
            request_schema=PromptRequest,
            response_schema=PromptResponse,
            endpoint_path="/api/v1/prompt",
            timeout=timeout,
            auth=auth,
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
            }
        else:
            return {
                "text": message.text
            }

