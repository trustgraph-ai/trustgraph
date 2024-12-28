
from .. schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from .. schema import graph_embeddings_request_queue
from .. schema import graph_embeddings_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor
from . serialize import serialize_value

class GraphEmbeddingsQueryRequestor(ServiceRequestor):
    def __init__(self, pulsar_host, timeout, auth):

        super(GraphEmbeddingsQueryRequestor, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=graph_embeddings_request_queue,
            response_queue=graph_embeddings_response_queue,
            request_schema=GraphEmbeddingsRequest,
            response_schema=GraphEmbeddingsResponse,
            timeout=timeout,
        )

    def to_request(self, body):

        limit = int(body.get("limit", 20))

        return GraphEmbeddingsRequest(
            vectors = body["vectors"],
            limit = limit,
            user = body.get("user", "trustgraph"),
            collection = body.get("collection", "default"),
        )

    def from_response(self, message):

        return {
            "entities": [
                serialize_value(ent) for ent in message.entities
            ]
        }, True

