
from pulsar.schema import JsonSchema
from .. schema import EmbeddingsRequest, EmbeddingsResponse
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
            pulsar_api_key=None,
    ):

        super(EmbeddingsClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=EmbeddingsRequest,
            output_schema=EmbeddingsResponse,
        )

    def request(self, text, timeout=300):
        return self.call(text=text, timeout=timeout).vectors

