from ... schema import CollectionManagementRequest, CollectionManagementResponse
from ... schema import collection_request_queue, collection_response_queue
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class CollectionManagementRequestor(ServiceRequestor):
    def __init__(self, backend, consumer, subscriber, timeout=120,
                 request_queue=None, response_queue=None):

        if request_queue is None:
            request_queue = collection_request_queue
        if response_queue is None:
            response_queue = collection_response_queue

        super(CollectionManagementRequestor, self).__init__(
            backend=backend,
            consumer_name = consumer,
            subscription = subscriber,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=CollectionManagementRequest,
            response_schema=CollectionManagementResponse,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("collection-management")
        self.response_translator = TranslatorRegistry.get_response_translator("collection-management")

    def to_request(self, body):
        return self.request_translator.decode(body)

    def from_response(self, message):
        return self.response_translator.encode_with_completion(message)
