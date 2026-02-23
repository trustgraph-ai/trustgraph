
import _pulsar

from .. schema import RowEmbeddingsRequest, RowEmbeddingsResponse
from .. schema import row_embeddings_request_queue
from .. schema import row_embeddings_response_queue
from . base import BaseClient

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class RowEmbeddingsClient(BaseClient):

    def __init__(
            self, log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
    ):

        if input_queue == None:
            input_queue = row_embeddings_request_queue

        if output_queue == None:
            output_queue = row_embeddings_response_queue

        super(RowEmbeddingsClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=RowEmbeddingsRequest,
            output_schema=RowEmbeddingsResponse,
        )

    def request(
            self, vectors, schema_name, user="trustgraph", collection="default",
            index_name=None, limit=10, timeout=300
    ):
        kwargs = dict(
            user=user, collection=collection,
            vectors=vectors, schema_name=schema_name,
            limit=limit, timeout=timeout
        )
        if index_name:
            kwargs["index_name"] = index_name

        response = self.call(**kwargs)

        if response.error:
            raise RuntimeError(f"{response.error.type}: {response.error.message}")

        return response.matches
