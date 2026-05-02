
from ... schema import IamRequest, IamResponse
from ... schema import iam_request_queue, iam_response_queue
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor


class IamRequestor(ServiceRequestor):
    def __init__(self, backend, consumer, subscriber, timeout=120,
                 request_queue=None, response_queue=None):

        if request_queue is None:
            request_queue = iam_request_queue
        if response_queue is None:
            response_queue = iam_response_queue

        super().__init__(
            backend=backend,
            consumer_name=consumer,
            subscription=subscriber,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=IamRequest,
            response_schema=IamResponse,
            timeout=timeout,
        )

        self.request_translator = (
            TranslatorRegistry.get_request_translator("iam")
        )
        self.response_translator = (
            TranslatorRegistry.get_response_translator("iam")
        )

    def to_request(self, body):
        return self.request_translator.decode(body)

    def from_response(self, message):
        return self.response_translator.encode_with_completion(message)
