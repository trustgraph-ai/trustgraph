
from ... schema import EmbeddingsRequest, EmbeddingsResponse

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

    def to_request(self, body):
        return EmbeddingsRequest(
            text=body["text"]
        )

    def from_response(self, message):
        return { "vectors": message.vectors }, True

