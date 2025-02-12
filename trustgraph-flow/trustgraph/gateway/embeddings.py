
from .. schema import EmbeddingsRequest, EmbeddingsResponse
from .. schema import embeddings_request_queue
from .. schema import embeddings_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class EmbeddingsRequestor(ServiceRequestor):
    def __init__(self, pulsar_host, timeout, auth, pulsar_api_key=None):

        super(EmbeddingsRequestor, self).__init__(
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            request_queue=embeddings_request_queue,
            response_queue=embeddings_response_queue,
            request_schema=EmbeddingsRequest,
            response_schema=EmbeddingsResponse,
            timeout=timeout,
        )

    def to_request(self, body):
        return EmbeddingsRequest(
            text=body["text"]
        )

    def from_response(self, message):
        return { "vectors": message.vectors }, True

