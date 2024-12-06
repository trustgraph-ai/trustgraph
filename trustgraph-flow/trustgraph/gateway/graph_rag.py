
from ... schema import GraphRagQuery, GraphRagResponse
from ... schema import graph_rag_request_queue
from ... schema import graph_rag_response_queue

from . endpoint import ServiceEndpoint

class GraphRagEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout, auth):

        super(GraphRagEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=graph_rag_request_queue,
            response_queue=graph_rag_response_queue,
            request_schema=GraphRagQuery,
            response_schema=GraphRagResponse,
            endpoint_path="/api/v1/graph-rag",
            timeout=timeout,
            auth=auth,
        )

    def to_request(self, body):
        return GraphRagQuery(
            query=body["query"],
            user=body.get("user", "trustgraph"),
            collection=body.get("collection", "default"),
        )

    def from_response(self, message):
        return { "response": message.response }

