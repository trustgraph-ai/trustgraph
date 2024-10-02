
import _pulsar

from .. schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from .. schema import graph_embeddings_request_queue
from .. schema import graph_embeddings_response_queue
from . base import BaseClient

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class GraphEmbeddingsClient(BaseClient):

    def __init__(
            self, log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
    ):

        if input_queue == None:
            input_queue = graph_embeddings_request_queue

        if output_queue == None:
            output_queue = graph_embeddings_response_queue
            
        super(GraphEmbeddingsClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            input_schema=GraphEmbeddingsRequest,
            output_schema=GraphEmbeddingsResponse,
        )

    def request(
            self, vectors, user="trustgraph", collection="default",
            limit=10, timeout=300
    ):
        return self.call(
            user=user, collection=collection,
            vectors=vectors, limit=limit, timeout=timeout
        ).entities

