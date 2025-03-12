
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

class Api:

    def __init__(self, url="http://localhost:8088/"):

        self.url = url

        if not url.endswith("/"):
            self.url += "/"

        self.url += "api/v1/"

    def check_error(self, response):

        if "error" in response:

            try:
                msg = response["error"]["message"]
                tp = response["error"]["message"]
            except:
                raise ApplicationException(
                    "Error, but the error object is broken"
                )

            raise ApplicationException(f"{tp}: {msg}")

    def text_completion(self, system, prompt):

        # The input consists of system and prompt strings
        input = {
            "system": system,
            "prompt": prompt
        }

        url = f"{self.url}text-completion"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=input)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException(f"Expected JSON response")

        self.check_error(resp)

        try:
            return object["response"]
        except:
            raise ProtocolException(f"Response not formatted correctly")

    def agent(self, question):

        # The input consists of a question
        input = {
            "question": question
        }

        url = f"{self.url}agent"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=input)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException(f"Expected JSON response")

        self.check_error(resp)

        try:
            return object["answer"]
        except:
            raise ProtocolException(f"Response not formatted correctly")

    def graph_rag(
            self, question, user="trustgraph", collection="default",
            entity_limit=50, triple_limit=30, subgraph_limit=1000,
    ):

        # The input consists of a question
        input = {
            "query": question,
            "user": user,
            "collection": collection,
            "entity-limit": entity_limit,
            "triple-limit": triple_limit,
            "max-subgraph-limit": subgraph_limit,
        }

        url = f"{self.url}graph-rag"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=input)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException(f"Expected JSON response")

        self.check_error(resp)

        try:
            return object["response"]
        except:
            raise ProtocolException(f"Response not formatted correctly")

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

        url = f"{self.url}document-rag"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=input)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException(f"Expected JSON response")

        self.check_error(resp)

        try:
            return object["response"]
        except:
            raise ProtocolException(f"Response not formatted correctly")

    def embeddings(self, text):

        # The input consists of a text block
        input = {
            "text": text
        }

        url = f"{self.url}embeddings"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=input)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException(f"Expected JSON response")

        self.check_error(resp)

        try:
            return object["vectors"]
        except:
            raise ProtocolException(f"Response not formatted correctly")

    def prompt(self, id, variables):

        # The input consists of system and prompt strings
        input = {
            "id": id,
            "variables": variables
        }

        url = f"{self.url}prompt"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=input)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException("Expected JSON response")

        self.check_error(resp)

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

        url = f"{self.url}triples-query"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=input)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException("Expected JSON response")

        self.check_error(resp)

        if "response" not in object:
            raise ProtocolException("Response not formatted correctly")

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

        return object["response"]

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

        url = f"{self.url}load/document"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=input)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

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

        url = f"{self.url}load/text"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=input)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

