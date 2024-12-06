
from .. schema import EmbeddingsRequest, EmbeddingsResponse
from .. schema import embeddings_request_queue
from .. schema import embeddings_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class EmbeddingsRequestor(ServiceRequestor):
    def __init__(self, pulsar_host, timeout, auth):

        super(EmbeddingsRequestor, self).__init__(
            pulsar_host=pulsar_host,
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
        return { "vectors": message.vectors }

class EmbeddingsEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout, auth):

        super(EmbeddingsEndpoint, self).__init__(
            endpoint_path="/api/v1/embeddings",
            auth=auth,
            requestor = EmbeddingsRequestor(
                pulsar_host=pulsar_host, timeout=timeout, auth=auth
            )
        )

