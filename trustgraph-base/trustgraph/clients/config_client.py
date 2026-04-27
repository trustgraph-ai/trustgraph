
import json
import dataclasses

from .. schema import ConfigRequest, ConfigResponse, ConfigKey, ConfigValue
from .. schema import config_request_queue
from .. schema import config_response_queue
from . base import BaseClient

# Ugly

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
            self,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            workspace="default",
            **pubsub_config,
    ):

        if input_queue == None:
            input_queue = config_request_queue

        if output_queue == None:
            output_queue = config_response_queue

        super(ConfigClient, self).__init__(
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            input_schema=ConfigRequest,
            output_schema=ConfigResponse,
            **pubsub_config,
        )

        self.workspace = workspace

    def get(self, keys, timeout=300):

        resp = self.call(
            operation="get",
            workspace=self.workspace,
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
            workspace=self.workspace,
            type=type,
            timeout=timeout
        )

        return resp.directory

    def getvalues(self, type, timeout=300):

        resp = self.call(
            operation="getvalues",
            workspace=self.workspace,
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

    def getvalues_all_ws(self, type, timeout=300):
        """Fetch all values of a given type across all workspaces.
        Returns a list of dicts including a 'workspace' field."""

        resp = self.call(
            operation="getvalues-all-ws",
            type=type,
            timeout=timeout
        )

        return [
            {
                "workspace": v.workspace,
                "type": v.type,
                "key": v.key,
                "value": v.value,
            }
            for v in resp.values
        ]

    def delete(self, keys, timeout=300):

        resp = self.call(
            operation="delete",
            workspace=self.workspace,
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
            workspace=self.workspace,
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
            workspace=self.workspace,
            timeout=timeout
        )

        return resp.config, resp.version

