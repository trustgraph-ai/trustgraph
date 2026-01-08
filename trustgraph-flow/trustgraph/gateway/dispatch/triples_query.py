
from ... schema import TriplesQueryRequest, TriplesQueryResponse, Triples
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class TriplesQueryRequestor(ServiceRequestor):
    def __init__(
            self, backend, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(TriplesQueryRequestor, self).__init__(
            backend=backend,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=TriplesQueryRequest,
            response_schema=TriplesQueryResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("triples-query")
        self.response_translator = TranslatorRegistry.get_response_translator("triples-query")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

