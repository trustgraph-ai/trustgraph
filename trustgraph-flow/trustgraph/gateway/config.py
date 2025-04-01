
from .. schema import ConfigRequest, ConfigResponse
from .. schema import config_request_queue
from .. schema import config_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class ConfigRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, timeout, auth):

        super(ConfigRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=config_request_queue,
            response_queue=config_response_queue,
            request_schema=ConfigRequest,
            response_schema=ConfigResponse,
            timeout=timeout,
        )

    def to_request(self, body):

        return ConfigRequest(
            operation = body.get("operation", None),
            type = body.get("type", None),
            key = body.get("key", None),
            value = body.get("value", None),
        )

    def from_response(self, message):

        response = {
        }

        if message.version:
            response["version"] = message.version

        if message.value:
            response["value"] = message.value

        if message.directory:
            response["directory"] = message.directory

        if message.values:
            response["values"] = message.values

        if message.config:
            response["config"] = message.config

        return response, True

