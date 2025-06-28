
from ... schema import EmbeddingsRequest, EmbeddingsResponse
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class EmbeddingsRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(EmbeddingsRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=EmbeddingsRequest,
            response_schema=EmbeddingsResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("embeddings")
        self.response_translator = TranslatorRegistry.get_response_translator("embeddings")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

