from ... schema import ExtractionRequest, ExtractionResponse
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class ExtractionRequestor(ServiceRequestor):
    def __init__(
            self, backend, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(ExtractionRequestor, self).__init__(
            backend=backend,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=ExtractionRequest,
            response_schema=ExtractionResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("extraction")
        self.response_translator = TranslatorRegistry.get_response_translator("extraction")

    def to_request(self, body):
        return self.request_translator.decode(body)

    def from_response(self, message):
        return self.response_translator.encode_with_completion(message)
