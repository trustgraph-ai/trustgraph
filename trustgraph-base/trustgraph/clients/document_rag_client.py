
import _pulsar

from .. schema import DocumentRagQuery, DocumentRagResponse
from .. schema import document_rag_request_queue, document_rag_response_queue
from . base import BaseClient

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class DocumentRagClient(BaseClient):

    def __init__(
            self,
            log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
    ):

        if input_queue == None:
            input_queue = document_rag_request_queue

        if output_queue == None:
            output_queue = document_rag_response_queue
  
        super(DocumentRagClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=DocumentRagQuery,
            output_schema=DocumentRagResponse,
        )

    def request(self, query, timeout=300):

        return self.call(
            query=query, timeout=timeout
        ).response

