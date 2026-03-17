
import _pulsar

from .. schema import GraphRagQuery, GraphRagResponse
from .. schema import graph_rag_request_queue, graph_rag_response_queue
from . base import BaseClient

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class GraphRagClient(BaseClient):

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
            input_queue = graph_rag_request_queue

        if output_queue == None:
            output_queue = graph_rag_response_queue
  
        super(GraphRagClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=GraphRagQuery,
            output_schema=GraphRagResponse,
        )

    def request(
            self, query, user="trustgraph", collection="default",
            chunk_callback=None,
            explain_callback=None,
            timeout=500
    ):
        """
        Request a graph RAG query with optional streaming callbacks.

        Args:
            query: The question to ask
            user: User identifier
            collection: Collection identifier
            chunk_callback: Optional callback(text, end_of_stream) for text chunks
            explain_callback: Optional callback(explain_id, explain_graph) for explain notifications
            timeout: Request timeout in seconds

        Returns:
            Complete response text (accumulated from all chunks)
        """
        accumulated_response = []

        def inspect(x):
            # Handle explain notifications
            if x.message_type == 'explain':
                if explain_callback and x.explain_id:
                    explain_callback(x.explain_id, x.explain_graph)
                return False  # Continue receiving

            # Handle text chunks
            if x.message_type == 'chunk':
                if x.response:
                    accumulated_response.append(x.response)
                if chunk_callback:
                    chunk_callback(x.response, x.end_of_stream)

            # Complete when session ends
            if x.end_of_session:
                return True

            return False  # Continue receiving

        self.call(
            user=user, collection=collection, query=query,
            inspect=inspect, timeout=timeout
        )

        return "".join(accumulated_response)

