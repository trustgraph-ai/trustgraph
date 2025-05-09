
from ... schema import GraphRagQuery, GraphRagResponse

from . requestor import ServiceRequestor

class GraphRagRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(GraphRagRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=GraphRagQuery,
            response_schema=GraphRagResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

    def to_request(self, body):
        return GraphRagQuery(
            query=body["query"],
            user=body.get("user", "trustgraph"),
            collection=body.get("collection", "default"),
            entity_limit=int(body.get("entity-limit", 50)),
            triple_limit=int(body.get("triple-limit", 30)),
            max_subgraph_size=int(body.get("max-subgraph-size", 1000)),
            max_path_length=int(body.get("max-path-length", 2)),
        )

    def from_response(self, message):
        return { "response": message.response }, True

