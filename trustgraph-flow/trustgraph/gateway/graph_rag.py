
from .. schema import GraphRagQuery, GraphRagResponse
from .. schema import graph_rag_request_queue
from .. schema import graph_rag_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class GraphRagRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, timeout, auth):

        super(GraphRagRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=graph_rag_request_queue,
            response_queue=graph_rag_response_queue,
            request_schema=GraphRagQuery,
            response_schema=GraphRagResponse,
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
        )

    def from_response(self, message):
        return { "response": message.response }, True

