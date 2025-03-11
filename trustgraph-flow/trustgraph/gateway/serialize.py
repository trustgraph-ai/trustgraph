
import base64

from .. schema import Value, Triple, DocumentPackage, DocumentInfo

def to_value(x):
    return Value(value=x["v"], is_uri=x["e"])

def to_subgraph(x):
    return [
        Triple(
            s=to_value(t["s"]),
            p=to_value(t["p"]),
            o=to_value(t["o"])
        )
        for t in x
    ]

def serialize_value(v):
    return {
        "v": v.value,
        "e": v.is_uri,
    }

def serialize_triple(t):
    return {
        "s": serialize_value(t.s),
        "p": serialize_value(t.p),
        "o": serialize_value(t.o)
    }

def serialize_subgraph(sg):
    return [
        serialize_triple(t)
        for t in sg
    ]

def serialize_triples(message):
    return {
        "metadata": {
            "id": message.metadata.id,
            "metadata": serialize_subgraph(message.metadata.metadata),
            "user": message.metadata.user,
            "collection": message.metadata.collection,
        },
        "triples": serialize_subgraph(message.triples),
    }
    
def serialize_graph_embeddings(message):
    return {
        "metadata": {
            "id": message.metadata.id,
            "metadata": serialize_subgraph(message.metadata.metadata),
            "user": message.metadata.user,
            "collection": message.metadata.collection,
        },
        "entities": [
            {
                "vectors": entity.vectors,
                "entity": serialize_value(entity.entity),
            }
            for entity in message.entities
        ],
    }

def serialize_document_embeddings(message):
    return {
        "metadata": {
            "id": message.metadata.id,
            "metadata": serialize_subgraph(message.metadata.metadata),
            "user": message.metadata.user,
            "collection": message.metadata.collection,
        },
        "chunks": [
            {
                "vectors": chunk.vectors,
                "chunk": chunk.chunk.decode("utf-8"),
            }
            for chunk in message.chunks
        ],
    }

def serialize_document_package(message):

    ret = {}

    if message.id:
        ret["id"] = message.id

    if message.metadata:
        ret["metadata"] = serialize_subgraph(message.metdata)

    if message.document:
        blob = base64.b64encode(
            message.document.encode("utf-8")
        ).decode("utf-8")
        ret["document"] = blob

    if message.kind:
        ret["kind"] = message.kind

    if message.user:
        ret["user"] = message.user

    if message.collection:
        ret["collection"] = message.collection

    return ret

def serialize_document_info(message):

    ret = {}

    if message.id:
        ret["id"] = message.id

    if message.kind:
        ret["kind"] = message.kind

    if message.user:
        ret["user"] = message.user

    if message.collection:
        ret["collection"] = message.collection

    if message.title:
        ret["title"] = message.title

    if message.comments:
        ret["comments"] = message.comments

    if message.time:
        ret["time"] = message.time

    if message.metadata:
        ret["metadata"] = serialize_subgraph(message.metadata)

    return ret

def to_document_package(x):

    return DocumentPackage(
        id = x.get("id", None),
        kind = x.get("kind", None),
        user = x.get("user", None),
        collection = x.get("collection", None),
        title = x.get("title", None),
        comments = x.get("comments", None),
        time = x.get("time", None),
        document = x.get("document", None),
        metadata = to_subgraph(x["metadata"]),
    )

def to_document_info(x):

    return DocumentInfo(
        id = x.get("id", None),
        kind = x.get("kind", None),
        user = x.get("user", None),
        collection = x.get("collection", None),
        title = x.get("title", None),
        comments = x.get("comments", None),
        time = x.get("time", None),
        metadata = to_subgraph(x["metadata"]),
    )

def to_criteria(x):
    return [
        Critera(v["key"], v["value"], v["operator"])
        for v in x
    ]
