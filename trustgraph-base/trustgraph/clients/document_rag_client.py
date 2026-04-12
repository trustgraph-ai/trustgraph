

from .. schema import DocumentRagQuery, DocumentRagResponse
from .. schema import document_rag_request_queue, document_rag_response_queue
from . base import BaseClient

# Ugly

class DocumentRagClient(BaseClient):

    def __init__(
            self,
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
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=DocumentRagQuery,
            output_schema=DocumentRagResponse,
        )

    def request(self, query, user="trustgraph", collection="default",
                chunk_callback=None, explain_callback=None, timeout=300):
        """
        Request a document RAG query with optional streaming callbacks.

        Args:
            query: The question to ask
            user: User identifier
            collection: Collection identifier
            chunk_callback: Optional callback(text, end_of_stream) for text chunks
            explain_callback: Optional callback(explain_id, explain_graph, explain_triples) for explain notifications
            timeout: Request timeout in seconds

        Returns:
            Complete response text (accumulated from all chunks)
        """
        accumulated_response = []

        def inspect(x):
            # Handle explain notifications (response is None/empty, explain_id present)
            if x.explain_id and not x.response:
                if explain_callback:
                    explain_callback(x.explain_id, x.explain_graph, x.explain_triples)
                return False  # Continue receiving

            # Handle text chunks
            if x.response:
                accumulated_response.append(x.response)
                if chunk_callback:
                    chunk_callback(x.response, x.end_of_stream)

            # Complete when stream ends
            if x.end_of_stream:
                return True

            return False  # Continue receiving

        self.call(
            query=query, user=user, collection=collection,
            inspect=inspect, timeout=timeout
        )

        return "".join(accumulated_response)

