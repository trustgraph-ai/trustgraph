
import _pulsar
import json
import dataclasses

from .. schema import ConfigRequest, ConfigResponse, ConfigKey, ConfigValue
from .. schema import config_request_queue
from .. schema import config_response_queue
from . base import BaseClient

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

@dataclasses.dataclass
class Definition:
    name: str
    definition: str

@dataclasses.dataclass
class Relationship:
    s: str
    p: str
    o: str
    o_entity: str

@dataclasses.dataclass
class Topic:
    name: str
    definition: str

class ConfigClient(BaseClient):

    def __init__(
            self, log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
            listener=None,
            pulsar_api_key=None,
    ):

        if input_queue == None:
            input_queue = config_request_queue

        if output_queue == None:
            output_queue = config_response_queue

        super(ConfigClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=ConfigRequest,
            output_schema=ConfigResponse,
            listener=listener,
        )

    def get(self, keys, timeout=300):

        resp = self.call(
            operation="get",
            keys=[
                ConfigKey(
                    type = k["type"],
                    key = k["key"]
                )
                for k in keys
            ],
            timeout=timeout
        )

        return [
            {
                "type": v.type,
                "key": v.key,
                "value": v.value
            }
            for v in resp.values
        ]

    def list(self, type, timeout=300):

        resp = self.call(
            operation="list",
            type=type,
            timeout=timeout
        )

        return resp.directory

    def getvalues(self, type, timeout=300):

        resp = self.call(
            operation="getvalues",
            type=type,
            timeout=timeout
        )

        return [
            {
                "type": v.type,
                "key": v.key,
                "value": v.value
            }
            for v in resp.values
        ]

    def delete(self, keys, timeout=300):

        resp = self.call(
            operation="delete",
            keys=[
                ConfigKey(
                    type = k["type"],
                    key = k["key"]
                )
                for k in keys
            ],
            timeout=timeout
        )

        return None

    def put(self, values, timeout=300):

        resp = self.call(
            operation="put",
            values=[
                ConfigValue(
                    type = v["type"],
                    key = v["key"],
                    value = v["value"]
                )
                for v in values
            ],
            timeout=timeout
        )

        return None

    def config(self, timeout=300):

        resp = self.call(
            operation="config",
            timeout=timeout
        )

        return resp.config, resp.version

