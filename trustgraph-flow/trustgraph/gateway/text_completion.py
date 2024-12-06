
from .. schema import TextCompletionRequest, TextCompletionResponse
from .. schema import text_completion_request_queue
from .. schema import text_completion_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class TextCompletionRequestor(ServiceRequestor):
    def __init__(self, pulsar_host, timeout, auth):

        super(TextCompletionRequestor, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=text_completion_request_queue,
            response_queue=text_completion_response_queue,
            request_schema=TextCompletionRequest,
            response_schema=TextCompletionResponse,
            timeout=timeout,
        )

    def to_request(self, body):
        return TextCompletionRequest(
            system=body["system"],
            prompt=body["prompt"]
        )

    def from_response(self, message):
        return { "response": message.response }, True

