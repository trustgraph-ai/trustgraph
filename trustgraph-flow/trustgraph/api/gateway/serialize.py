from ... schema import Value, Triple

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
        "vectors": message.vectors,
        "entity": message.entity,
    }

