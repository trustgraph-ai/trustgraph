
from ... schema import FlowRequest, FlowResponse
from ... schema import flow_request_queue
from ... schema import flow_response_queue
from .... base.messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class FlowRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, consumer, subscriber, timeout=120):

        super(FlowRequestor, self).__init__(
            pulsar_client=pulsar_client,
            consumer_name = consumer,
            subscription = subscriber,
            request_queue=flow_request_queue,
            response_queue=flow_response_queue,
            request_schema=FlowRequest,
            response_schema=FlowResponse,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("flow")
        self.response_translator = TranslatorRegistry.get_response_translator("flow")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

