
from ... schema import DocumentRagQuery, DocumentRagResponse

from . requestor import ServiceRequestor

class DocumentRagRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(DocumentRagRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=DocumentRagQuery,
            response_schema=DocumentRagResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

    def to_request(self, body):
        return DocumentRagQuery(
            query=body["query"],
            user=body.get("user", "trustgraph"),
            collection=body.get("collection", "default"),
            doc_limit=int(body.get("doc-limit", 20)),
        )

    def from_response(self, message):
        return { "response": message.response }, True

