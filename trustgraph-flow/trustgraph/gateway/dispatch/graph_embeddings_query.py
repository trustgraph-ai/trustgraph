
from ... schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse

from . requestor import ServiceRequestor
from . serialize import serialize_value

class GraphEmbeddingsQueryRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(GraphEmbeddingsQueryRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=GraphEmbeddingsRequest,
            response_schema=GraphEmbeddingsResponse,
            subscription = subscriber,
            consumer_name = consumer,
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

