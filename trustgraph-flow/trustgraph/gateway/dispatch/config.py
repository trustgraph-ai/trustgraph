
from ... schema import ConfigRequest, ConfigResponse, ConfigKey, ConfigValue
from ... schema import config_request_queue
from ... schema import config_response_queue

from . requestor import ServiceRequestor

class ConfigRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, timeout):

        super(ConfigRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=config_request_queue,
            response_queue=config_response_queue,
            request_schema=ConfigRequest,
            response_schema=ConfigResponse,
            timeout=timeout,
        )

    def to_request(self, body):

        if "keys" in body:
            keys = [
                ConfigKey(
                    type = k["type"],
                    key = k["key"],
                )
                for k in body["keys"]
            ]
        else:
            keys = None

        if "values" in body:
            values = [
                ConfigValue(
                    type = v["type"],
                    key = v["key"],
                    value = v["value"],
                )
                for v in body["values"]
            ]
        else:
            values = None

        return ConfigRequest(
            operation = body.get("operation", None),
            keys = keys,
            type = body.get("type", None),
            values = values
        )

    def from_response(self, message):

        response = { }

        if message.version is not None:
            response["version"] = message.version

        if message.values is not None:
            response["values"] = [
                {
                    "type": v.type,
                    "key": v.key,
                    "value": v.value,
                }
                for v in message.values
            ]

        if message.directory is not None:
            response["directory"] = message.directory

        if message.config is not None:
            response["config"] = message.config

        return response, True

