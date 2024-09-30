
from pulsar.schema import JsonSchema
from .. schema import EmbeddingsRequest, EmbeddingsResponse
from .. schema import embeddings_request_queue, embeddings_response_queue
from . base import BaseClient

import _pulsar

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class EmbeddingsClient(BaseClient):

    def __init__(
            self, log_level=ERROR,
            input_queue=None,
            output_queue=None,
            subscriber=None,
            pulsar_host="pulsar://pulsar:6650",
    ):

        if input_queue == None:
            input_queue=embeddings_request_queue

        if output_queue == None:
            output_queue=embeddings_response_queue

        super(EmbeddingsClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            input_schema=EmbeddingsRequest,
            output_schema=EmbeddingsResponse,
        )

    def request(self, text, timeout=300):
        return self.call(text=text, timeout=timeout).vectors


