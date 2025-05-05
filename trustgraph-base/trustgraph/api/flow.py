
import json
import base64

from .. knowledge import hash, Uri, Literal

def to_value(x):
    if x["e"]: return Uri(x["v"])
    return Literal(x["v"])

class Flow:

    def __init__(self, api):
        self.api = api

    def request(self, path=None, request=None):

        if request is None:
            raise RuntimeError("request must be specified")

        if path:
            return self.api.request(f"flow/{path}", request)
        else:
            return self.api.request(f"flow", request)

    def id(self, id="0000"):
        return FlowInstance(api=self, id=id)

    def list_classes(self):

        # The input consists of system and prompt strings
        input = {
            "operation": "list-classes",
        }

        return self.request(request = input)["class-names"]

    def get_class(self, class_name):

        # The input consists of system and prompt strings
        input = {
            "operation": "get-class",
            "class-name": class_name,
        }

        return json.loads(self.request(request = input)["class-definition"])

    def put_class(self, class_name, definition):

        # The input consists of system and prompt strings
        input = {
            "operation": "put-class",
            "class-name": class_name,
            "class-definition": json.dumps(definition),
        }

        self.request(request = input)

    def delete_class(self, class_name):

        # The input consists of system and prompt strings
        input = {
            "operation": "delete-class",
            "class-name": class_name,
        }

        self.request(request = input)

    def list(self):

        # The input consists of system and prompt strings
        input = {
            "operation": "list-flows",
        }

        return self.request(request = input)["flow-ids"]

    def get(self, id):

        # The input consists of system and prompt strings
        input = {
            "operation": "get-flow",
            "flow-id": id,
        }

        return json.loads(self.request(request = input)["flow"])

    def start(self, class_name, id, description):

        # The input consists of system and prompt strings
        input = {
            "operation": "start-flow",
            "flow-id": id,
            "class-name": class_name,
            "description": description,
        }

        self.request(request = input)

    def stop(self, id):

        # The input consists of system and prompt strings
        input = {
            "operation": "stop-flow",
            "flow-id": id,
        }

        self.request(request = input)
        
class FlowInstance:

    def __init__(self, api, id):
        self.api = api
        self.id = id

    def request(self, path, request):

        return self.api.request(path = f"{self.id}/{path}", request = request)

    def text_completion(self, system, prompt):

        # The input consists of system and prompt strings
        input = {
            "system": system,
            "prompt": prompt
        }

        return self.request(
            "service/text-completion",
            input
        )["response"]

    def agent(self, question):

        # The input consists of a question
        input = {
            "question": question
        }

        return self.request(
            "service/agent",
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

        return self.request(
            "service/graph-rag",
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

        return self.request(
            "service/document-rag",
            input
        )["response"]

    def embeddings(self, text):

        # The input consists of a text block
        input = {
            "text": text
        }

        return self.request(
            "service/embeddings",
            input
        )["vectors"]

    def prompt(self, id, variables):

        # The input consists of system and prompt strings
        input = {
            "id": id,
            "variables": variables
        }

        object = self.request(
            "service/prompt",
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

    def triples_query(
            self, s=None, p=None, o=None,
            user=None, collection=None, limit=10000
    ):

        # The input consists of system and prompt strings
        input = {
            "limit": limit
        }

        if user:
            input["user"] = user

        if collection:
            input["collection"] = collection

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

        object = self.request(
            "service/triples",
            input
        )

        return [
            Triple(
                s=to_value(t["s"]),
                p=to_value(t["p"]),
                o=to_value(t["o"])
            )
            for t in object["response"]
        ]

    def load_document(
            self, document, id=None, metadata=None, user=None,
            collection=None,
    ):

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

        if user:
            input["user"] = user

        if collection:
            input["collection"] = collection

        return self.request(
            "service/document-load",
            input
        )

    def load_text(
            self, text, id=None, metadata=None, charset="utf-8",
            user=None, collection=None,
    ):

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

        if user:
            input["user"] = user

        if collection:
            input["collection"] = collection

        return self.request(
            "service/text-load",
            input
        )

