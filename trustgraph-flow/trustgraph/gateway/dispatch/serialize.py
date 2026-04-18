
import base64

from ... schema import Term, Triple, DocumentMetadata, ProcessingMetadata
from ... messaging.translators.primitives import TermTranslator, TripleTranslator

# Singleton translator instances
_term_translator = TermTranslator()
_triple_translator = TripleTranslator()


def to_value(x):
    """Convert dict to Term. Delegates to TermTranslator."""
    return _term_translator.decode(x)


def to_subgraph(x):
    """Convert list of dicts to list of Triples. Delegates to TripleTranslator."""
    return [_triple_translator.decode(t) for t in x]


def serialize_value(v):
    """Convert Term to dict. Delegates to TermTranslator."""
    return _term_translator.encode(v)


def serialize_triple(t):
    """Convert Triple to dict. Delegates to TripleTranslator."""
    return _triple_translator.encode(t)


def serialize_subgraph(sg):
    """Convert list of Triples to list of dicts."""
    return [serialize_triple(t) for t in sg]

def serialize_triples(message):
    return {
        "metadata": {
            "id": message.metadata.id,
            "root": message.metadata.root,
            "collection": message.metadata.collection,
        },
        "triples": serialize_subgraph(message.triples),
    }


def serialize_graph_embeddings(message):
    return {
        "metadata": {
            "id": message.metadata.id,
            "root": message.metadata.root,
            "collection": message.metadata.collection,
        },
        "entities": [
            {
                "vector": entity.vector,
                "entity": serialize_value(entity.entity),
            }
            for entity in message.entities
        ],
    }


def serialize_entity_contexts(message):
    return {
        "metadata": {
            "id": message.metadata.id,
            "root": message.metadata.root,
            "collection": message.metadata.collection,
        },
        "entities": [
            {
                "context": entity.context,
                "entity": serialize_value(entity.entity),
            }
            for entity in message.entities
        ],
    }


def serialize_document_embeddings(message):
    return {
        "metadata": {
            "id": message.metadata.id,
            "root": message.metadata.root,
            "collection": message.metadata.collection,
        },
        "chunks": [
            {
                "vector": chunk.vector,
                "chunk_id": chunk.chunk_id,
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

    if message.workspace:
        ret["workspace"] = message.workspace

    if message.tags is not None:
        ret["tags"] = message.tags

    return ret

def serialize_processing_metadata(message):

    ret = {}

    if message.id:
        ret["id"] = message.id

    if message.id:
        ret["document-id"] = message.document_id

    if message.time:
        ret["time"] = message.time

    if message.flow:
        ret["flow"] = message.flow

    if message.workspace:
        ret["workspace"] = message.workspace

    if message.collection:
        ret["collection"] = message.collection

    if message.tags is not None:
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
        workspace = x.get("workspace", None),
        tags = x.get("tags", None),
    )

def to_processing_metadata(x):

    return ProcessingMetadata(
        id = x.get("id", None),
        document_id = x.get("document-id", None),
        time = x.get("time", None),
        flow = x.get("flow", None),
        workspace = x.get("workspace", None),
        collection = x.get("collection", None),
        tags = x.get("tags", None),
    )

def to_criteria(x):
    return [
        Critera(v["key"], v["value"], v["operator"])
        for v in x
    ]

