from ... schema import CollectionManagementRequest, CollectionManagementResponse
from ... schema import collection_request_queue, collection_response_queue
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class CollectionManagementRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, consumer, subscriber, timeout=120):

        super(CollectionManagementRequestor, self).__init__(
            pulsar_client=pulsar_client,
            consumer_name = consumer,
            subscription = subscriber,
            request_queue=collection_request_queue,
            response_queue=collection_response_queue,
            request_schema=CollectionManagementRequest,
            response_schema=CollectionManagementResponse,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("collection-management")
        self.response_translator = TranslatorRegistry.get_response_translator("collection-management")

    def to_request(self, body):
        print("REQUEST", body, flush=True)
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        print("RESPONSE", message, flush=True)
        return self.response_translator.from_response_with_completion(message)
