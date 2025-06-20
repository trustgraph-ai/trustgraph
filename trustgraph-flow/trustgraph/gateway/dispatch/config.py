
from ... schema import ConfigRequest, ConfigResponse, ConfigKey, ConfigValue
from ... schema import config_request_queue
from ... schema import config_response_queue
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

class ConfigRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, consumer, subscriber, timeout=120):

        super(ConfigRequestor, self).__init__(
            pulsar_client=pulsar_client,
            consumer_name = consumer,
            subscription = subscriber,
            request_queue=config_request_queue,
            response_queue=config_response_queue,
            request_schema=ConfigRequest,
            response_schema=ConfigResponse,
            timeout=timeout,
        )

        self.request_translator = TranslatorRegistry.get_request_translator("config")
        self.response_translator = TranslatorRegistry.get_response_translator("config")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

