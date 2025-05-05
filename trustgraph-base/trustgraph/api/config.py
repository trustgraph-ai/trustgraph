
from . exceptions import *
from . types import ConfigValue

class Config:

    def __init__(self, api):
        self.api = api

    def request(self, request):
        return self.api.request("config", request)

    def get(self, keys):

        # The input consists of system and prompt strings
        input = {
            "operation": "get",
            "keys": [
                { "type": k.type, "key": k.key }
                for k in keys
            ]
        }

        object = self.request(input)

        try:
            return [
                ConfigValue(
                    type = v["type"],
                    key = v["key"],
                    value = v["value"]
                )
                for v in object["values"]
            ]
        except Exception as e:
            print(e)
            raise ProtocolException("Response not formatted correctly")

    def put(self, values):

        # The input consists of system and prompt strings
        input = {
            "operation": "put",
            "values": [
                { "type": v.type, "key": v.key, "value": v.value }
                for v in values
            ]
        }

        self.request(input)

    def list(self, type):

        # The input consists of system and prompt strings
        input = {
            "operation": "list",
            "type": type,
        }

        return self.request(input)["directory"]

    def get_values(self, type):

        # The input consists of system and prompt strings
        input = {
            "operation": "getvalues",
            "type": type,
        }

        object = self.request(input)["directory"]

        try:
            return [
                ConfigValue(
                    type = v["type"],
                    key = v["key"],
                    value = v["value"]
                )
                for v in object["values"]
            ]
        except:
            raise ProtocolException(f"Response not formatted correctly")

    def all(self):

        # The input consists of system and prompt strings
        input = {
            "operation": "config"
        }

        object = self.request(input)

        try:
            return object["config"], object["version"]
        except:
            raise ProtocolException(f"Response not formatted correctly")

