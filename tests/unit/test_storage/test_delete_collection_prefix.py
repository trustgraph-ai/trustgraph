"""
delete_collection must only drop the vector collections of the named
workspace/collection, not those of another collection whose name merely
starts with it (collection "my" vs "my_collection").
"""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.storage.doc_embeddings.qdrant.write import Processor as DocQdrant
from trustgraph.storage.graph_embeddings.qdrant.write import Processor as GraphQdrant
from trustgraph.direct.milvus_doc_embeddings import DocVectors
from trustgraph.direct.milvus_graph_embeddings import EntityVectors

try:
    from trustgraph.storage.doc_embeddings.pinecone.write import Processor as DocPinecone
    from trustgraph.storage.graph_embeddings.pinecone.write import Processor as GraphPinecone
    HAS_PINECONE = True
except (ImportError, ModuleNotFoundError):
    DocPinecone = GraphPinecone = None
    HAS_PINECONE = False


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,mod,letter", [
    (DocQdrant, "trustgraph.storage.doc_embeddings.qdrant.write", "d"),
    (GraphQdrant, "trustgraph.storage.graph_embeddings.qdrant.write", "t"),
])
async def test_qdrant_delete_collection_keeps_longer_names(cls, mod, letter):
    with patch(f"{mod}.QdrantClient") as qc:
        client = qc.return_value
        proc = cls(taskgroup=AsyncMock(), id="test")
    names = [
        f"{letter}_ws_my_384", f"{letter}_ws_my_768",
        f"{letter}_ws_my_collection_384",
    ]
    client.get_collections.return_value = SimpleNamespace(
        collections=[SimpleNamespace(name=n) for n in names]
    )

    await proc.delete_collection("ws", "my")

    dropped = sorted(c.args[0] for c in client.delete_collection.call_args_list)
    assert dropped == [f"{letter}_ws_my_384", f"{letter}_ws_my_768"]


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_PINECONE, reason="Pinecone SDK not compatible")
@pytest.mark.parametrize("cls,mod,letter", [
    (DocPinecone, "trustgraph.storage.doc_embeddings.pinecone.write", "d"),
    (GraphPinecone, "trustgraph.storage.graph_embeddings.pinecone.write", "t"),
])
async def test_pinecone_delete_collection_keeps_longer_names(cls, mod, letter):
    with patch(f"{mod}.Pinecone") as pc:
        client = pc.return_value
        proc = cls(taskgroup=AsyncMock(), id="test", api_key="k")
    names = [
        f"{letter}-ws-my-384", f"{letter}-ws-my-768",
        f"{letter}-ws-my-collection-384",
    ]
    client.list_indexes.return_value = [SimpleNamespace(name=n) for n in names]

    await proc.delete_collection("ws", "my")

    dropped = sorted(c.args[0] for c in client.delete_index.call_args_list)
    assert dropped == [f"{letter}-ws-my-384", f"{letter}-ws-my-768"]


@pytest.mark.parametrize("cls,mod,prefix", [
    (DocVectors, "trustgraph.direct.milvus_doc_embeddings", "doc"),
    (EntityVectors, "trustgraph.direct.milvus_graph_embeddings", "entity"),
])
def test_milvus_delete_and_exists_ignore_longer_names(cls, mod, prefix):
    with patch(f"{mod}.MilvusClient") as mc:
        client = mc.return_value
        vecs = cls(uri="http://test:19530", prefix=prefix)

    client.list_collections.return_value = [
        f"{prefix}_ws_my_384", f"{prefix}_ws_my_collection_384",
    ]
    vecs.delete_collection("ws", "my")
    dropped = [c.args[0] for c in client.drop_collection.call_args_list]
    assert dropped == [f"{prefix}_ws_my_384"]

    client.list_collections.return_value = [f"{prefix}_ws_my_collection_384"]
    assert vecs.collection_exists("ws", "my") is False
    assert vecs.collection_exists("ws", "my_collection") is True
