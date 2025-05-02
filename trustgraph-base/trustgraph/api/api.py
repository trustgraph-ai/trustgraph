
import requests
import json
import dataclasses
import base64

from trustgraph.knowledge import hash, Uri, Literal

class ProtocolException(Exception):
    pass

class ApplicationException(Exception):
    pass

@dataclasses.dataclass
class Triple:
    s : str
    p : str
    o : str

@dataclasses.dataclass
class ConfigKey:
    type : str
    key : str

@dataclasses.dataclass
class ConfigValue:
    type : str
    key : str
    value : str

def check_error(response):

    if "error" in response:

        try:
            msg = response["error"]["message"]
            tp = response["error"]["type"]
        except:
            raise ApplicationException(
                "Error, but the error object is broken"
            )

        raise ApplicationException(f"{tp}: {msg}")

class Api:

    def __init__(self, url="http://localhost:8088/"):

        self.url = url

        if not url.endswith("/"):
            self.url += "/"

        self.url += "api/v1/"

    def flow(self, flow="0000"):
        return Flow(api=self, flow=flow)

    def request(self, path, request):

        url = f"{self.url}{path}"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=request)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException(f"Expected JSON response")

        check_error(object)

        return object

    def config_all(self):

        # The input consists of system and prompt strings
        input = {
            "operation": "config"
        }

        object = self.request("config", input)

        try:
            return object["config"], object["version"]
        except:
            raise ProtocolException(f"Response not formatted correctly")

    def config_get(self, keys):

        # The input consists of system and prompt strings
        input = {
            "operation": "get",
            "keys": [
                { "type": k.type, "key": k.key }
                for k in keys
            ]
        }

        object = self.request("config", input)

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

    def config_put(self, values):

        # The input consists of system and prompt strings
        input = {
            "operation": "put",
            "values": [
                { "type": v.type, "key": v.key, "value": v.value }
                for v in values
            ]
        }

        self.request("config", input)

    def config_list(self, type):

        # The input consists of system and prompt strings
        input = {
            "operation": "list",
            "type": type,
        }

        return self.request("config", input)["directory"]

    def config_getvalues(self, type):

        # The input consists of system and prompt strings
        input = {
            "operation": "getvalues",
            "type": type,
        }

        object = self.request("config", input)["directory"]

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

    def flow_list_classes(self):

        # The input consists of system and prompt strings
        input = {
            "operation": "list-classes",
        }

        return self.request("flow", input)["class-names"]

    def flow_get_class(self, class_name):

        # The input consists of system and prompt strings
        input = {
            "operation": "get-class",
            "class-name": class_name,
        }

        return json.loads(self.request("flow", input)["class-definition"])

    def flow_put_class(self, class_name, definition):

        # The input consists of system and prompt strings
        input = {
            "operation": "put-class",
            "class-name": class_name,
            "class-definition": json.dumps(definition),
        }

        self.request("flow", input)

    def flow_delete_class(self, class_name):

        # The input consists of system and prompt strings
        input = {
            "operation": "delete-class",
            "class-name": class_name,
        }

        self.request("flow", input)

    def flow_list(self):

        # The input consists of system and prompt strings
        input = {
            "operation": "list-flows",
        }

        return self.request("flow", input)["flow-ids"]

    def flow_get(self, id):

        # The input consists of system and prompt strings
        input = {
            "operation": "get-flow",
            "flow-id": id,
        }

        return json.loads(self.request("flow", input)["flow"])

    def flow_start(self, class_name, id, description):

        # The input consists of system and prompt strings
        input = {
            "operation": "start-flow",
            "flow-id": id,
            "class-name": class_name,
            "description": description,
        }

        self.request("flow", input)

    def flow_stop(self, id):

        # The input consists of system and prompt strings
        input = {
            "operation": "stop-flow",
            "flow-id": id,
        }

        self.request("flow", input)

class Flow:

    def __init__(self, api, flow):
        self.api = api
        self.flow = flow

    def text_completion(self, system, prompt):

        # The input consists of system and prompt strings
        input = {
            "system": system,
            "prompt": prompt
        }

        return self.api.request(
            f"flow/{self.flow}/service/text-completion",
            input
        )["response"]

    def agent(self, question):

        # The input consists of a question
        input = {
            "question": question
        }

        return self.api.request(
            f"flow/{self.flow}/service/agent",
            input
        )["answer"]

    def graph_rag(
            self, question, user="trustgraph", collection="default",
            entity_limit=50, triple_limit=30, max_subgraph_size=150,
            max_path_length=2,
    ):

        # The input consists of a question
        input = {
            "query": question,
            "user": user,
            "collection": collection,
            "entity-limit": entity_limit,
            "triple-limit": triple_limit,
            "max-subgraph-size": max_subgraph_size,
            "max-path-length": max_path_length,
        }

        return self.api.request(
            f"flow/{self.flow}/service/graph-rag",
            input
        )["response"]

    def document_rag(
            self, question, user="trustgraph", collection="default",
            doc_limit=10,
    ):

        # The input consists of a question
        input = {
            "query": question,
            "user": user,
            "collection": collection,
            "doc-limit": doc_limit,
        }

        return self.api.request(
            f"flow/{self.flow}/service/document-rag",
            input
        )["response"]

    def embeddings(self, text):

        # The input consists of a text block
        input = {
            "text": text
        }

        return self.api.request(
            f"flow/{self.flow}/service/embeddings",
            input
        )["vectors"]

    def prompt(self, id, variables):

        # The input consists of system and prompt strings
        input = {
            "id": id,
            "variables": variables
        }

        object = self.api.request(
            f"flow/{self.flow}/service/prompt",
            input
        )

        if "text" in object:
            return object["text"]

        if "object" in object:
            try:
                return json.loads(object["object"])
            except Exception as e:
                raise ProtocolException(
                    "Returned object not well-formed JSON"
                )

        raise ProtocolException("Response not formatted correctly")

    def triples_query(self, s=None, p=None, o=None, limit=10000):

        # The input consists of system and prompt strings
        input = {
            "limit": limit
        }

        if s:
            if not isinstance(s, Uri):
                raise RuntimeError("s must be Uri")
            input["s"] = { "v": str(s), "e": isinstance(s, Uri), }
            
        if p:
            if not isinstance(p, Uri):
                raise RuntimeError("p must be Uri")
            input["p"] = { "v": str(p), "e": isinstance(p, Uri), }

        if o:
            if not isinstance(o, Uri) and not isinstance(o, Literal):
                raise RuntimeError("o must be Uri or Literal")
            input["o"] = { "v": str(o), "e": isinstance(o, Uri), }

        object = self.api.request(
            f"flow/{self.flow}/service/triples",
            input
        )

        def to_value(x):
            if x["e"]: return Uri(x["v"])
            return Literal(x["v"])
            
        return [
            Triple(
                s=to_value(t["s"]),
                p=to_value(t["p"]),
                o=to_value(t["o"])
            )
            for t in object["response"]
        ]

    def load_document(self, document, id=None, metadata=None):

        if id is None:

            if metadata is not None:

                # Situation makes no sense.  What can the metadata possibly
                # mean if the caller doesn't know the document ID.
                # Metadata should relate to the document by ID
                raise RuntimeError("Can't specify metadata without id")

            id = hash(document)

        triples = []

        def emit(t):
            triples.append(t)

        if metadata:
            metadata.emit(
                lambda t: triples.append({
                    "s": { "v": t["s"], "e": isinstance(t["s"], Uri) },
                    "p": { "v": t["p"], "e": isinstance(t["p"], Uri) },
                    "o": { "v": t["o"], "e": isinstance(t["o"], Uri) }
                })
            )

        input = {
            "id": id,
            "metadata": triples,
            "data": base64.b64encode(document).decode("utf-8"),
        }

        return self.api.request(
            f"flow/{self.flow}/service/document-load",
            input
        )

    def load_text(self, text, id=None, metadata=None, charset="utf-8"):

        if id is None:

            if metadata is not None:

                # Situation makes no sense.  What can the metadata possibly
                # mean if the caller doesn't know the document ID.
                # Metadata should relate to the document by ID
                raise RuntimeError("Can't specify metadata without id")

            id = hash(text)

        triples = []

        if metadata:
            metadata.emit(
                lambda t: triples.append({
                    "s": { "v": t["s"], "e": isinstance(t["s"], Uri) },
                    "p": { "v": t["p"], "e": isinstance(t["p"], Uri) },
                    "o": { "v": t["o"], "e": isinstance(t["o"], Uri) }
                })
            )

        input = {
            "id": id,
            "metadata": triples,
            "charset": charset,
            "text": base64.b64encode(text).decode("utf-8"),
        }

        return self.api.request(
            f"flow/{self.flow}/service/text-load",
            input
        )

