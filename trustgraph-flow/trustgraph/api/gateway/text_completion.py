
from ... schema import TextCompletionRequest, TextCompletionResponse
from ... schema import text_completion_request_queue
from ... schema import text_completion_response_queue

from . endpoint import ServiceEndpoint

class TextCompletionEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout):

        super(TextCompletionEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=text_completion_request_queue,
            response_queue=text_completion_response_queue,
            request_schema=TextCompletionRequest,
            response_schema=TextCompletionResponse,
            endpoint_path="/api/v1/text-completion",
            timeout=timeout,
        )

    def to_request(self, body):
        return TextCompletionRequest(
            system=body["system"],
            prompt=body["prompt"]
        )

    def from_response(self, message):
        return { "response": message.response }
