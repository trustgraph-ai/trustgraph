
from ... schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class GraphEmbeddingsQueryRequestor(ServiceRequestor):
    def __init__(
            self, backend, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(GraphEmbeddingsQueryRequestor, self).__init__(
            backend=backend,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=GraphEmbeddingsRequest,
            response_schema=GraphEmbeddingsResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("graph-embeddings-query")
        self.response_translator = TranslatorRegistry.get_response_translator("graph-embeddings-query")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

