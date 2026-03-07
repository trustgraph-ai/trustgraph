# Document Embeddings Chunk ID

## Overview

Document embeddings storage currently stores chunk text directly in the vector store payload, duplicating data that exists in Garage. This spec replaces chunk text storage with `chunk_id` references.

## Current State

```python
@dataclass
class ChunkEmbeddings:
    chunk: bytes = b""
    vectors: list[list[float]] = field(default_factory=list)
```

Vector store payload:
```python
payload={"doc": chunk}  # Duplicates Garage content
```

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

### Query Flow

1. Search vector store → get matching `chunk_id` values
2. Return chunk_ids to caller
3. Caller fetches content from Garage if needed

## Files to Modify

### Schema
- `trustgraph-base/trustgraph/schema/knowledge/embeddings.py`
- `trustgraph-base/trustgraph/schema/services/query.py`

### Embeddings Service
- `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

### Storage Writers
- `trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
- `trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
- `trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`

### Query Services
- `trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py`
- `trustgraph-flow/trustgraph/query/doc_embeddings/milvus/service.py`
- `trustgraph-flow/trustgraph/query/doc_embeddings/pinecone/service.py`

## Benefits

1. Single source of truth - chunk text only in Garage
2. Reduced vector store storage
3. Enables query-time provenance via chunk_id
