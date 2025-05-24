
import datetime
import time
import base64

from . types import DocumentMetadata, ProcessingMetadata, Triple
from .. knowledge import hash, Uri, Literal
from . exceptions import *

def to_value(x):
    if x["e"]: return Uri(x["v"])
    return Literal(x["v"])

class Library:

    def __init__(self, api):
        self.api = api

    def request(self, request):
        return self.api.request(f"librarian", request)

    def add_document(
            self, document, id, metadata, user, title, comments,
            kind="text/plain", tags=[], 
    ):

        if id is None:

            if metadata is not None:

                # Situation makes no sense.  What can the metadata possibly
                # mean if the caller doesn't know the document ID.
                # Metadata should relate to the document by ID
                raise RuntimeError("Can't specify metadata without id")

            id = hash(document)

        if not title: title = ""
        if not comments: comments = ""

        triples = []

        def emit(t):
            triples.append(t)

        if metadata:
            if isinstance(metadata, list):
                triples = [
                    {
                        "s": { "v": t.s, "e": isinstance(t.s, Uri) },
                        "p": { "v": t.p, "e": isinstance(t.p, Uri) },
                        "o": { "v": t.o, "e": isinstance(t.o, Uri) }
                    }
                    for t in metadata
                ]
            elif hasattr(metadata, "emit"):
                metadata.emit(
                    lambda t: triples.append({
                        "s": { "v": t["s"], "e": isinstance(t["s"], Uri) },
                        "p": { "v": t["p"], "e": isinstance(t["p"], Uri) },
                        "o": { "v": t["o"], "e": isinstance(t["o"], Uri) }
                    })
                )
            else:
                raise RuntimeError("metadata should be a list of Triples or have an emit method")

        input = {
            "operation": "add-document",
            "document-metadata": {
                "id": id,
                "time": int(time.time()),
                "kind": kind,
                "title": title,
                "comments": comments,
                "metadata": triples,
                "user": user,
                "tags": tags
            },
            "content": base64.b64encode(document).decode("utf-8"),
        }

        return self.request(input)

    def get_documents(self, user):

        input = {
            "operation": "list-documents",
            "user": user,
        }

        object = self.request(input)

        try:
            return [
                DocumentMetadata(
                    id = v["id"],
                    time = datetime.datetime.fromtimestamp(v["time"]),
                    kind = v["kind"],
                    title = v["title"],
                    comments = v.get("comments", ""),
                    metadata = [
                        Triple(
                            s = to_value(w["s"]),
                            p = to_value(w["p"]),
                            o = to_value(w["o"])
                        )
                        for w in v["metadata"]
                    ],
                    user = v["user"],
                    tags = v["tags"]
                )
                for v in object["document-metadatas"]
            ]
        except Exception as e:
            print(e)
            raise ProtocolException(f"Response not formatted correctly")

    def get_document(self, user, id):

        input = {
            "operation": "get-document",
            "user": user,
            "document-id": id,
        }

        object = self.request(input)
        doc = object["document-metadata"]

        try:
            DocumentMetadata(
                id = doc["id"],
                time = datetime.datetime.fromtimestamp(doc["time"]),
                kind = doc["kind"],
                title = doc["title"],
                comments = doc.get("comments", ""),
                metadata = [
                    Triple(
                        s = to_value(w["s"]),
                        p = to_value(w["p"]),
                        o = to_value(w["o"])
                    )
                    for w in doc["metadata"]
                ],
                user = doc["user"],
                tags = doc["tags"]
            )
        except Exception as e:
            print(e)
            raise ProtocolException(f"Response not formatted correctly")

    def update_document(self, user, id, metadata):

        input = {
            "operation": "update-document",
            "document-metadata": {
                "user": user,
                "document-id": id,
                "time": metadata.time,
                "title": metadata.title,
                "comments": metadata.comments,
                "metadata": [
                    {
                        "s": { "v": t["s"], "e": isinstance(t["s"], Uri) },
                        "p": { "v": t["p"], "e": isinstance(t["p"], Uri) },
                        "o": { "v": t["o"], "e": isinstance(t["o"], Uri) }
                    }
                    for t in metadata.metadata
                ],
                "tags": metadata.tags,
            }
        }

        object = self.request(input)
        doc = object["document-metadata"]

        try:
            DocumentMetadata(
                id = doc["id"],
                time = datetime.datetime.fromtimestamp(doc["time"]),
                kind = doc["kind"],
                title = doc["title"],
                comments = doc.get("comments", ""),
                metadata = [
                    Triple(
                        s = to_value(w["s"]),
                        p = to_value(w["p"]),
                        o = to_value(w["o"])
                    )
                    for w in doc["metadata"]
                ],
                user = doc["user"],
                tags = doc["tags"]
            )
        except Exception as e:
            print(e)
            raise ProtocolException(f"Response not formatted correctly")

    def remove_document(self, user, id):

        input = {
            "operation": "remove-document",
            "user": user,
            "document-id": id,
        }

        object = self.request(input)

        return {}

    def start_processing(
            self, id, document_id, flow="default",
            user="trustgraph", collection="default", tags=[],
    ):

        input = {
            "operation": "add-processing",
            "processing-metadata": {
                "id": id,
                "document-id": document_id,
                "time": int(time.time()),
                "flow": flow,
                "user": user,
                "collection": collection,
                "tags": tags,
            }
        }

        object = self.request(input)

        return {}

    def stop_processing(
            self, id, user="trustgraph", 
    ):

        input = {
            "operation": "remove-processing",
            "processing-id": id,
            "user": user,
        }

        object = self.request(input)

        return {}

    def get_processings(self, user="trustgraph"):

        input = {
            "operation": "list-processing",
            "user": user,
        }

        object = self.request(input)

        try:
            return [
                ProcessingMetadata(
                    id = v["id"],
                    document_id = v["document-id"],
                    time = datetime.datetime.fromtimestamp(v["time"]),
                    flow = v["flow"],
                    user = v["user"],
                    collection = v["collection"],
                    tags = v["tags"],
                )
                for v in object["processing-metadatas"]
            ]
        except Exception as e:
            print(e)
            raise ProtocolException(f"Response not formatted correctly")

