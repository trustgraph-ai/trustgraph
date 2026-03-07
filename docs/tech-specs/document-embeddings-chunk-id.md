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

The document RAG processor fetches chunk content from Garage:

```python
# Get chunk_ids from embeddings store
chunk_ids = await self.rag.doc_embeddings_client.query(...)

# Fetch chunk content from Garage
docs = []
for chunk_id in chunk_ids:
    content = await self.rag.librarian_client.get_document_content(
        chunk_id, self.user
    )
    docs.append(content)
```

### API/SDK Changes

**DocumentEmbeddingsClient** returns chunk_ids:
```python
return resp.chunk_ids  # Changed from resp.chunks
```

**Wire format** (DocumentEmbeddingsResponseTranslator):
```python
result["chunk_ids"] = obj.chunk_ids  # Changed from chunks
```

### CLI Changes

CLI tool displays chunk_ids (callers can fetch content separately if needed).

## Files to Modify

### Schema
- `trustgraph-base/trustgraph/schema/knowledge/embeddings.py` - ChunkEmbeddings
- `trustgraph-base/trustgraph/schema/services/query.py` - DocumentEmbeddingsResponse

### Messaging/Translators
- `trustgraph-base/trustgraph/messaging/translators/embeddings_query.py` - DocumentEmbeddingsResponseTranslator

### Client
- `trustgraph-base/trustgraph/base/document_embeddings_client.py` - return chunk_ids

### Python SDK/API
- `trustgraph-base/trustgraph/api/flow.py` - document_embeddings_query
- `trustgraph-base/trustgraph/api/socket_client.py` - document_embeddings_query
- `trustgraph-base/trustgraph/api/async_flow.py` - if applicable
- `trustgraph-base/trustgraph/api/bulk_client.py` - import/export document embeddings
- `trustgraph-base/trustgraph/api/async_bulk_client.py` - import/export document embeddings

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

### Gateway
- `trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_query.py`
- `trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_export.py`
- `trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_import.py`

### Document RAG
- `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` - add librarian client
- `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` - fetch from Garage

### CLI
- `trustgraph-cli/trustgraph/cli/invoke_document_embeddings.py`
- `trustgraph-cli/trustgraph/cli/save_doc_embeds.py`
- `trustgraph-cli/trustgraph/cli/load_doc_embeds.py`

## Benefits

1. Single source of truth - chunk text only in Garage
2. Reduced vector store storage
3. Enables query-time provenance via chunk_id
