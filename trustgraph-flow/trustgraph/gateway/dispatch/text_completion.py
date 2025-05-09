
from ... schema import TextCompletionRequest, TextCompletionResponse

from . requestor import ServiceRequestor

class TextCompletionRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(TextCompletionRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=TextCompletionRequest,
            response_schema=TextCompletionResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

    def to_request(self, body):
        return TextCompletionRequest(
            system=body["system"],
            prompt=body["prompt"]
        )

    def from_response(self, message):
        return { "response": message.response }, True

