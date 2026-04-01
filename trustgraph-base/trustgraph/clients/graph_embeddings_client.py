

from .. schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from .. schema import graph_embeddings_request_queue
from .. schema import graph_embeddings_response_queue
from . base import BaseClient

# Ugly

class GraphEmbeddingsClient(BaseClient):

    def __init__(
            self,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
    ):

        if input_queue == None:
            input_queue = graph_embeddings_request_queue

        if output_queue == None:
            output_queue = graph_embeddings_response_queue
            
        super(GraphEmbeddingsClient, self).__init__(
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=GraphEmbeddingsRequest,
            output_schema=GraphEmbeddingsResponse,
        )

    def request(
            self, vector, user="trustgraph", collection="default",
            limit=10, timeout=300
    ):
        return self.call(
            user=user, collection=collection,
            vector=vector, limit=limit, timeout=timeout
        ).entities

