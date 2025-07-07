
from ... schema import ToolRequest, ToolResponse
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class McpToolRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(McpToolRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=ToolRequest,
            response_schema=ToolResponse,
            subscription = subscriber,
            consumer_name = consumer,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("tool")
        self.response_translator = TranslatorRegistry.get_response_translator("tool")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

