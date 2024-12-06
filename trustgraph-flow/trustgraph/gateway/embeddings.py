
from .. schema import EmbeddingsRequest, EmbeddingsResponse
from .. schema import embeddings_request_queue
from .. schema import embeddings_response_queue

from . endpoint import ServiceEndpoint

class EmbeddingsEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout, auth):

        super(EmbeddingsEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=embeddings_request_queue,
            response_queue=embeddings_response_queue,
            request_schema=EmbeddingsRequest,
            response_schema=EmbeddingsResponse,
            endpoint_path="/api/v1/embeddings",
            timeout=timeout,
            auth=auth,
        )

    def to_request(self, body):
        return EmbeddingsRequest(
            text=body["text"]
        )

    def from_response(self, message):
        return { "vectors": message.vectors }
