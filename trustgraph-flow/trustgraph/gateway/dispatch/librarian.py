
import base64

from ... schema import LibrarianRequest, LibrarianResponse
from ... schema import librarian_request_queue
from ... schema import librarian_response_queue
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class LibrarianRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, consumer, subscriber, timeout=120,
                 request_queue=None, response_queue=None):

        if request_queue is None:
            request_queue = librarian_request_queue
        if response_queue is None:
            response_queue = librarian_response_queue

        super(LibrarianRequestor, self).__init__(
            pulsar_client=pulsar_client,
            consumer_name = consumer,
            subscription = subscriber,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=LibrarianRequest,
            response_schema=LibrarianResponse,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("librarian")
        self.response_translator = TranslatorRegistry.get_response_translator("librarian")

    def to_request(self, body):
        # Handle base64 content processing
        if "content" in body:
            # Content gets base64 decoded & encoded again to ensure valid base64
            content = base64.b64decode(body["content"].encode("utf-8"))
            content = base64.b64encode(content).decode("utf-8")
            body = body.copy()
            body["content"] = content
        
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

