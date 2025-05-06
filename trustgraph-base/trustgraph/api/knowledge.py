
import json
import base64

from .. knowledge import hash, Uri, Literal
from . types import Triple

def to_value(x):
    if x["e"]: return Uri(x["v"])
    return Literal(x["v"])

class Knowledge:

    def __init__(self, api):
        self.api = api

    def request(self, request):

        return self.api.request(f"knowledge", request)

    def list_kg_cores(self, user="trustgraph"):

        # The input consists of system and prompt strings
        input = {
            "operation": "list-kg-cores",
            "user": user,
        }

        return self.request(request = input)["ids"]

    def delete_kg_core(self, id, user="trustgraph"):

        # The input consists of system and prompt strings
        input = {
            "operation": "delete-kg-core",
            "user": user,
            "id": id,
        }

        self.request(request = input)

