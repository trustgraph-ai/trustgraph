---
layout: default
title: "数据提取流程"
parent: "Chinese (Beta)"
---

# 数据提取流程

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

本文档描述了数据如何通过 TrustGraph 提取流程进行流动，从文档提交到存储在知识库中。

## 概述

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌────────────────────┐
│ Librarian│────▶│ PDF Decoder │────▶│ Chunker │────▶│ Knowledge          │
│          │     │ (PDF only)  │     │         │     │ Extraction         │
│          │────────────────────────▶│         │     │                    │
└──────────┘     └─────────────┘     └─────────┘     └────────────────────┘
                                          │                    │
                                          │                    ├──▶ Triples
                                          │                    ├──▶ Entity Contexts
                                          │                    └──▶ Rows
                                          │
                                          └──▶ Document Embeddings
```

## 内容存储

### 对象存储 (S3/Minio)

文档内容存储在兼容 S3 的对象存储中：
路径格式：`doc/{object_id}`，其中 object_id 是一个 UUID
所有文档类型都存储在此处：源文档、页面、分块

### 元数据存储 (Cassandra)

文档元数据存储在 Cassandra 中，包括：
文档 ID、标题、类型 (MIME 类型)
`object_id` 引用对象存储
`parent_id` 用于子文档 (页面、分块)
`document_type`： "source", "page", "chunk", "answer"

### 内联与流式传输阈值

内容传输使用基于大小的策略：
**< 2MB**: 内容以内联方式包含在消息中 (base64 编码)
**≥ 2MB**: 仅发送 `document_id`；处理器通过 librarian API 获取

## 阶段 1：文档提交 (Librarian)

### 入口点

文档通过 librarian 的 `add-document` 操作进入系统：
1. 内容上传到对象存储
2. 在 Cassandra 中创建元数据记录
3. 返回文档 ID

### 触发提取

`add-processing` 操作触发提取：
指定 `document_id`、`flow` (pipeline ID)、`collection` (目标存储)
Librarian 的 `load_document()` 获取内容并发布到 flow 输入队列

### 模式：Document

```
Document
├── metadata: Metadata
│   ├── id: str              # Document identifier
│   ├── user: str            # Tenant/user ID
│   ├── collection: str      # Target collection
│   └── metadata: list[Triple]  # (largely unused, historical)
├── data: bytes              # PDF content (base64, if inline)
└── document_id: str         # Librarian reference (if streaming)
```

**路由 (Routing)**: 基于 `kind` 字段：
`application/pdf` → `document-load` 队列 → PDF 解码器
`text/plain` → `text-load` 队列 → 分块器

## 第二阶段：PDF 解码器

将 PDF 文档转换为文本页面。

### 流程

1. 获取内容（内联 `data` 或通过 `document_id` 从管理员处获取）
2. 使用 PyPDF 提取页面
3. 对于每个页面：
   另存为管理员中的子文档（`{doc_id}/p{page_num}`）
   发出来源三元组（页面源自文档）
   转发到分块器

### 模式：TextDocument

```
TextDocument
├── metadata: Metadata
│   ├── id: str              # Page URI (e.g., https://trustgraph.ai/doc/xxx/p1)
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── text: bytes              # Page text content (if inline)
└── document_id: str         # Librarian reference (e.g., "doc123/p1")
```

## 第三阶段：分块器

将文本分割成配置大小的块。

### 参数（可配置）

`chunk_size`：目标块大小（以字符为单位）（默认：2000）
`chunk_overlap`：块之间的重叠量（默认：100）

### 流程

1. 获取文本内容（内联或通过 librarian）
2. 使用递归字符分割器进行分割
3. 对于每个块：
   另存为 librarian 中的子文档（`{parent_id}/c{index}`）
   发出来源三元组（块源自页面/文档）
   转发到提取处理器

### 模式：Chunk

```
Chunk
├── metadata: Metadata
│   ├── id: str              # Chunk URI
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── chunk: bytes             # Chunk text content
└── document_id: str         # Librarian chunk ID (e.g., "doc123/p1/c3")
```

### 文档ID层级结构

子文档在其ID中编码了其来源信息：
来源：`doc123`
页面：`doc123/p5`
页面中的块：`doc123/p5/c2`
文本中的块：`doc123/c2`

## 第4阶段：知识提取

可用多种提取模式，由流程配置选择。

### 模式A：基本GraphRAG

两个并行处理器：

**kg-extract-definitions**
输入：块
输出：三元组（实体定义），实体上下文
提取内容：实体标签，定义

**kg-extract-relationships**
输入：块
输出：三元组（关系），实体上下文
提取内容：主语-谓语-宾语关系

### 模式B：基于本体论的 (kg-extract-ontology)

输入：块
输出：三元组，实体上下文
使用配置的本体论来指导提取

### 模式C：基于代理的 (kg-extract-agent)

输入：块
输出：三元组，实体上下文
使用代理框架进行提取

### 模式D：行提取 (kg-extract-rows)

输入：块
输出：行（结构化数据，不是三元组）
使用模式定义来提取结构化记录

### 模式：三元组

```
Triples
├── metadata: Metadata
│   ├── id: str
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]  # (set to [] by extractors)
└── triples: list[Triple]
    └── Triple
        ├── s: Term              # Subject
        ├── p: Term              # Predicate
        ├── o: Term              # Object
        └── g: str | None        # Named graph
```

### Schema: EntityContexts

```
EntityContexts
├── metadata: Metadata
└── entities: list[EntityContext]
    └── EntityContext
        ├── entity: Term         # Entity identifier (IRI)
        ├── context: str         # Textual description for embedding
        └── chunk_id: str        # Source chunk ID (provenance)
```

### Schema: Rows

```
Rows
├── metadata: Metadata
├── row_schema: RowSchema
│   ├── name: str
│   ├── description: str
│   └── fields: list[Field]
└── rows: list[dict[str, str]]   # Extracted records
```

## 第 5 阶段：嵌入式表示生成

### 图嵌入

将实体上下文转换为向量嵌入。

**流程：**
1. 接收 EntityContexts (实体上下文)
2. 使用上下文文本调用嵌入服务
3. 输出 GraphEmbeddings (实体 → 向量映射)

**模式：GraphEmbeddings**

```
GraphEmbeddings
├── metadata: Metadata
└── entities: list[EntityEmbeddings]
    └── EntityEmbeddings
        ├── entity: Term         # Entity identifier
        ├── vector: list[float]  # Embedding vector
        └── chunk_id: str        # Source chunk (provenance)
```

### 文档嵌入

将文本块直接转换为向量嵌入。

**流程：**
1. 接收文本块
2. 使用文本块调用嵌入服务
3. 输出文档嵌入

**模式：文档嵌入**

```
DocumentEmbeddings
├── metadata: Metadata
└── chunks: list[ChunkEmbeddings]
    └── ChunkEmbeddings
        ├── chunk_id: str        # Chunk identifier
        └── vector: list[float]  # Embedding vector
```

### 行嵌入 (Row Embeddings)

将行索引字段转换为向量嵌入。

**流程：**
1. 接收行 (Receive Rows)
2. 嵌入配置的索引字段 (Embed configured index fields)
3. 输出到行向量存储 (Output to row vector store)

## 第 6 阶段：存储 (Stage 6: Storage)

### 三元组存储 (Triple Store)

接收：三元组 (Receives: Triples)
存储：Cassandra (以实体为中心的表) (Storage: Cassandra (entity-centric tables))
命名图将核心知识与来源信息分开： (Named graphs separate core knowledge from provenance:)
  `""` (默认): 核心知识事实 (default): Core knowledge facts
  `urn:graph:source`: 提取来源 (Extraction provenance)
  `urn:graph:retrieval`: 查询时的可解释性 (Query-time explainability)

### 向量存储 (图嵌入) (Vector Store (Graph Embeddings))

接收：图嵌入 (Receives: GraphEmbeddings)
存储：Qdrant、Milvus 或 Pinecone (Storage: Qdrant, Milvus, or Pinecone)
索引：实体 IRI (Indexed by: entity IRI)
元数据：用于来源信息的 chunk_id (Metadata: chunk_id for provenance)

### 向量存储 (文档嵌入) (Vector Store (Document Embeddings))

接收：文档嵌入 (Receives: DocumentEmbeddings)
存储：Qdrant、Milvus 或 Pinecone (Storage: Qdrant, Milvus, or Pinecone)
索引：chunk_id (Indexed by: chunk_id)

### 行存储 (Row Store)

接收：行 (Receives: Rows)
存储：Cassandra (Storage: Cassandra)
基于模式的表结构 (Schema-driven table structure)

### 行向量存储 (Row Vector Store)

接收：行嵌入
存储：向量数据库
索引依据：行索引字段

## 元数据字段分析

### 正在使用的字段

| 字段 | 用途 |
|-------|-------|
| `metadata.id` | 文档/块标识符，日志记录，来源 |
| `metadata.user` | 多租户，存储路由 |
| `metadata.collection` | 目标集合选择 |
| `document_id` | 馆员引用，来源链接 |
| `chunk_id` | 通过流水线进行来源跟踪 |

<<<<<<< HEAD
### 潜在的冗余字段

| 字段 | 状态 |
|-------|--------|
| `metadata.metadata` | 由所有提取器设置为 `[]`；文档级别的元数据现在由馆员在提交时处理 |
=======
### 已移除的字段

| 字段 | 状态 |
|-------|--------|
| `metadata.metadata` | 从 `Metadata` 类中移除。文档级别的元数据三元组现在由馆员直接发送到三元存储，而不是通过提取流水线。 |
>>>>>>> e3bcbf73 (The metadata field (list of triples) in the pipeline Metadata class)

### 字节字段模式

所有内容字段（`data`，`text`，`chunk`）都是 `bytes`，但立即被所有处理器解码为 UTF-8 字符串。没有处理器使用原始字节。

## 流配置

流在外部定义，并通过配置服务提供给馆员。每个流都指定：

输入队列（`text-load`，`document-load`）
处理器链
参数（块大小，提取方法等）

示例流模式：
`pdf-graphrag`：PDF → 解码器 → 分块器 → 定义 + 关系 → 嵌入
`text-graphrag`：文本 → 分块器 → 定义 + 关系 → 嵌入
`pdf-ontology`：PDF → 解码器 → 分块器 → 本体提取 → 嵌入
`text-rows`：文本 → 分块器 → 行提取 → 行存储
