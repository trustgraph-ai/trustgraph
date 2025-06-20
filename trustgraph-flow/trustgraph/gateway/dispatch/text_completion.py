
from ... schema import TextCompletionRequest, TextCompletionResponse
from .... base.messaging import TranslatorRegistry

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

        self.request_translator = TranslatorRegistry.get_request_translator("text-completion")
        self.response_translator = TranslatorRegistry.get_response_translator("text-completion")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

