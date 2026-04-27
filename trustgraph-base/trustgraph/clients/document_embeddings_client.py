

from .. schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse
from .. schema import document_embeddings_request_queue
from .. schema import document_embeddings_response_queue
from . base import BaseClient

# Ugly

class DocumentEmbeddingsClient(BaseClient):

    def __init__(
            self,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
    ):

        if input_queue == None:
            input_queue = document_embeddings_request_queue

        if output_queue == None:
            output_queue = document_embeddings_response_queue
            
        super(DocumentEmbeddingsClient, self).__init__(
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=DocumentEmbeddingsRequest,
            output_schema=DocumentEmbeddingsResponse,
        )

    def request(
            self, vector, collection="default",
            limit=10, timeout=300
    ):
        return self.call(
            collection=collection,
            vector=vector, limit=limit, timeout=timeout
        ).chunks

