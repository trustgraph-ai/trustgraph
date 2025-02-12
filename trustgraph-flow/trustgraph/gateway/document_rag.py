
from .. schema import DocumentRagQuery, DocumentRagResponse
from .. schema import document_rag_request_queue
from .. schema import document_rag_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class DocumentRagRequestor(ServiceRequestor):
    def __init__(self, pulsar_host, timeout, auth, pulsar_api_key=None):

        super(DocumentRagRequestor, self).__init__(
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            request_queue=document_rag_request_queue,
            response_queue=document_rag_response_queue,
            request_schema=DocumentRagQuery,
            response_schema=DocumentRagResponse,
            timeout=timeout,
        )

    def to_request(self, body):
        return DocumentRagQuery(
            query=body["query"],
            user=body.get("user", "trustgraph"),
            collection=body.get("collection", "default"),
        )

    def from_response(self, message):
        return { "response": message.response }, True

