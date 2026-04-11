---
layout: default
title: "文档嵌入块 ID"
parent: "Chinese (Beta)"
---

# 文档嵌入块 ID

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

目前，文档嵌入存储将块文本直接存储在向量存储的负载中，这会重复 Garage 中已存在的数据。此规范将块文本存储替换为对 `chunk_id` 的引用。

## 当前状态

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

向量存储负载：
```python
payload={"doc": chunk}  # Duplicates Garage content
```

## 设计

### 模式变更

**ChunkEmbeddings** - 将 chunk 替换为 chunk_id:
```python
@dataclass
class ChunkEmbeddings:
    chunk_id: str = ""
    vectors: list[list[float]] = field(default_factory=list)
```

**DocumentEmbeddingsResponse** - 返回 chunk_ids 而不是 chunks：
```python
@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunk_ids: list[str] = field(default_factory=list)
```

### 向量存储负载

所有存储（Qdrant、Milvus、Pinecone）：
```python
payload={"chunk_id": chunk_id}
```

### 文档 RAG 变更

文档 RAG 处理器从 Garage 中获取块内容：

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

### API/SDK 变更

**DocumentEmbeddingsClient** 返回 chunk_ids:
```python
return resp.chunk_ids  # Changed from resp.chunks
```

**数据格式** (DocumentEmbeddingsResponseTranslator):
```python
result["chunk_ids"] = obj.chunk_ids  # Changed from chunks
```

### CLI 变更

CLI 工具显示 chunk_ids（如果需要，调用者可以单独获取内容）。

## 需要修改的文件

### Schema
`trustgraph-base/trustgraph/schema/knowledge/embeddings.py` - ChunkEmbeddings
`trustgraph-base/trustgraph/schema/services/query.py` - DocumentEmbeddingsResponse

### 消息/翻译器
`trustgraph-base/trustgraph/messaging/translators/embeddings_query.py` - DocumentEmbeddingsResponseTranslator

### 客户端
`trustgraph-base/trustgraph/base/document_embeddings_client.py` - 返回 chunk_ids

### Python SDK/API
`trustgraph-base/trustgraph/api/flow.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/socket_client.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/async_flow.py` - 如果适用
`trustgraph-base/trustgraph/api/bulk_client.py` - 导入/导出文档嵌入
`trustgraph-base/trustgraph/api/async_bulk_client.py` - 导入/导出文档嵌入

### 嵌入服务
`trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py` - 传递 chunk_id

### 存储写入器
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`

### 查询服务
`trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/milvus/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/pinecone/service.py`

### 网关
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_query.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_export.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_import.py`

### 文档 RAG
`trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` - 添加 librarian 客户端
`trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` - 从 Garage 获取

### CLI
`trustgraph-cli/trustgraph/cli/invoke_document_embeddings.py`
`trustgraph-cli/trustgraph/cli/save_doc_embeds.py`
`trustgraph-cli/trustgraph/cli/load_doc_embeds.py`

## 优点

1. 单一数据源 - 仅在 Garage 中存储文本块
2. 减少向量存储空间
3. 通过 chunk_id 实现查询时的数据溯源
