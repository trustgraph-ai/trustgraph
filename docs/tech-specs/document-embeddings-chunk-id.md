# Document Embeddings Chunk ID

## Overview

Document embeddings storage currently stores chunk text directly in the vector store payload, duplicating data that exists in Garage. This spec replaces chunk text storage with `chunk_id` references.

## Current State

```python
@dataclass
class ChunkEmbeddings:
    chunk: bytes = b""
    vectors: list[list[float]] = field(default_factory=list)

@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunks: list[str] = field(default_factory=list)
```

Vector store payload:
```python
payload={"doc": chunk}  # Duplicates Garage content
```

Document RAG flow:
1. Query embeddings → get chunk text
2. Pass chunk text directly to prompt

## Design

### Schema Changes

**ChunkEmbeddings** - replace chunk with chunk_id:
```python
@dataclass
class ChunkEmbeddings:
    chunk_id: str = ""
    vectors: list[list[float]] = field(default_factory=list)
```

**DocumentEmbeddingsResponse** - return chunk_ids instead of chunks:
```python
@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunk_ids: list[str] = field(default_factory=list)
```

### Vector Store Payload

All stores (Qdrant, Milvus, Pinecone):
```python
payload={"chunk_id": chunk_id}
```

### Document RAG Changes

The document RAG processor must fetch chunk content from Garage:

```python
# In document_rag.py get_docs():
async def get_docs(self, query):
    vectors = await self.get_vector(query)

    # Get chunk_ids from embeddings store
    chunk_ids = await self.rag.doc_embeddings_client.query(
        vectors, limit=self.doc_limit,
        user=self.user, collection=self.collection,
    )

    # Fetch chunk content from Garage
    docs = []
    for chunk_id in chunk_ids:
        content = await self.rag.librarian_client.get_document_content(
            chunk_id, self.user
        )
        docs.append(content)

    return docs
```

### Client Changes

**DocumentEmbeddingsClient** - return chunk_ids:
```python
async def query(self, vectors, limit=20, user="trustgraph",
                collection="default", timeout=30):
    resp = await self.request(...)
    if resp.error:
        raise RuntimeError(resp.error.message)
    return resp.chunk_ids  # Changed from resp.chunks
```

## Files to Modify

### Schema
- `trustgraph-base/trustgraph/schema/knowledge/embeddings.py` - ChunkEmbeddings
- `trustgraph-base/trustgraph/schema/services/query.py` - DocumentEmbeddingsResponse

### Client
- `trustgraph-base/trustgraph/base/document_embeddings_client.py` - return chunk_ids

### Embeddings Service
- `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py` - pass chunk_id

### Storage Writers
- `trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
- `trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
- `trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`

### Query Services
- `trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py`
- `trustgraph-flow/trustgraph/query/doc_embeddings/milvus/service.py`
- `trustgraph-flow/trustgraph/query/doc_embeddings/pinecone/service.py`

### Document RAG
- `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` - add librarian client
- `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` - fetch from Garage

## Benefits

1. Single source of truth - chunk text only in Garage
2. Reduced vector store storage
3. Enables query-time provenance via chunk_id
