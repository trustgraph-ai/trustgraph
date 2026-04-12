from ... schema import SparqlQueryRequest, SparqlQueryResponse
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class SparqlQueryRequestor(ServiceRequestor):
    def __init__(
            self, backend, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(SparqlQueryRequestor, self).__init__(
            backend=backend,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=SparqlQueryRequest,
            response_schema=SparqlQueryResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("sparql-query")
        self.response_translator = TranslatorRegistry.get_response_translator("sparql-query")

    def to_request(self, body):
        return self.request_translator.decode(body)

    def from_response(self, message):
        return self.response_translator.encode_with_completion(message)
