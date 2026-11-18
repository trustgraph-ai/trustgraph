
from ... schema import PolicyEngineRequest, PolicyEngineResponse
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class PolicyEngineRequestor(ServiceRequestor):
    def __init__(
            self, backend, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(PolicyEngineRequestor, self).__init__(
            backend=backend,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=PolicyEngineRequest,
            response_schema=PolicyEngineResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("policy")
        self.response_translator = TranslatorRegistry.get_response_translator("policy")

    def to_request(self, body):
        return self.request_translator.decode(body)

    def from_response(self, message):
        return self.response_translator.encode_with_completion(message)
