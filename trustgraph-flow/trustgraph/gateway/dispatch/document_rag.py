
from ... schema import DocumentRagQuery, DocumentRagResponse
from ... messaging import TranslatorRegistry

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

        self.request_translator = TranslatorRegistry.get_request_translator("document-rag")
        self.response_translator = TranslatorRegistry.get_response_translator("document-rag")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

