from ... schema import StructuredQueryRequest, StructuredQueryResponse
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class StructuredQueryRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(StructuredQueryRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=StructuredQueryRequest,
            response_schema=StructuredQueryResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("structured-query")
        self.response_translator = TranslatorRegistry.get_response_translator("structured-query")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)