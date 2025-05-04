
import base64

from ... schema import Value, Triple, DocumentMetadata, ProcessingMetadata

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

def serialize_document_metadata(message):

    ret = {}

    if message.id:
        ret["id"] = message.id

    if message.time:
        ret["time"] = message.time

    if message.kind:
        ret["kind"] = message.kind

    if message.title:
        ret["title"] = message.title

    if message.comments:
        ret["comments"] = message.comments

    if message.metadata:
        ret["metadata"] = serialize_subgraph(message.metadata)

    if message.kind:
        ret["user"] = message.user

    if message.tags:
        ret["tags"] = message.tags

    return ret

def serialize_processing_metadata(message):

    ret = {}

    if message.id:
        ret["id"] = message.id

    if message.id:
        ret["document_id"] = message.document_id

    if message.time:
        ret["time"] = message.time

    if message.kind:
        ret["flow"] = message.flow

    if message.user:
        ret["user"] = message.user

    if message.collection:
        ret["collection"] = message.collection

    if message.tags:
        ret["tags"] = message.tags

    return ret

def to_document_metadata(x):

    return DocumentMetadata(
        id = x.get("id", None),
        time = x.get("time", None),
        kind = x.get("kind", None),
        title = x.get("title", None),
        comments = x.get("comments", None),
        metadata = to_subgraph(x["metadata"]),
        user = x.get("user", None),
        tags = x.get("tags", None),
    )

def to_processing_metadata(x):

    return ProcessingMetadata(
        id = x.get("id", None),
        document_id = x.get("document_id", None),
        time = x.get("time", None),
        flow = x.get("flow", None),
        user = x.get("user", None),
        collection = x.get("collection", None),
        tags = x.get("tags", None),
    )

def to_criteria(x):
    return [
        Critera(v["key"], v["value"], v["operator"])
        for v in x
    ]

