
import pulsar
import _pulsar
from pulsar.schema import JsonSchema
from .. schema import GraphRagQuery, GraphRagResponse
from .. schema import graph_rag_request_queue, graph_rag_response_queue
from . base import BaseClient

import hashlib
import uuid
import time

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class GraphRagClient:

    def __init__(
            self,
            log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
    ):

        if input_queue == None:
            input_queue = graph_rag_request_queue

        if output_queue == None:
            output_queue = graph_rag_request_queue
  
        super(EmbeddingsClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            input_schema=GraphRagQuery,
            output_schema=GraphRagResponse,
        )

    def request(self, query, timeout=500):

        return self.call(
            query=query, timeout=timeout
        ).entities

