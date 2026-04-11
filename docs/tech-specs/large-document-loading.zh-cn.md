# 大型文档加载技术规范

## 概述

本规范解决了在将大型文档加载到 TrustGraph 时出现的可扩展性和用户体验问题。 当前架构将文档上传视为单个原子操作，这会在管道的多个阶段导致内存压力，并且不为用户提供任何反馈或恢复选项。

本次实施的目标是以下用例：


1. **大型 PDF 处理**: 在不耗尽内存的情况下，上传和处理数百兆字节的 PDF 文件。

2. **可恢复的上传**: 允许中断的上传从中断的地方继续，而不是重新开始。
   
3. **进度反馈**: 向用户提供有关上传和处理进度的实时可见性。
   
4. **内存高效处理**: 以流式方式处理文档，而无需将整个文件保存在内存中。
   

   ## 目标


**增量上传**: 支持通过 REST 和 WebSocket 进行分块文档上传。
**可恢复传输**: 启用从中断的上传中恢复。
**进度可见性**: 向客户端提供上传/处理进度反馈。
**内存效率**: 消除整个管道中的完整文档缓冲。
**向后兼容性**: 现有的小型文档工作流程保持不变。
**流式处理**: PDF 解码和文本分块操作在流上进行。

## 背景


### 当前架构

文档提交流程如下：

1. **客户端** 通过 REST (`POST /api/v1/librarian`) 或 WebSocket 提交文档。
2. **API 网关** 接收包含 base64 编码的文档内容的完整请求。
3. **LibrarianRequestor** 将请求转换为 Pulsar 消息。
4. **Librarian 服务** 接收消息，将文档解码到内存中。
5. **BlobStore** 将文档上传到 Garage/S3。
6. **Cassandra** 存储包含对象引用的元数据。
7. 为了处理：从 S3 中检索文档，解码，分块——所有都在内存中。

关键文件：
REST/WebSocket 入口：`trustgraph-flow/trustgraph/gateway/service.py`
Librarian 核心：`trustgraph-flow/trustgraph/librarian/librarian.py`
Blob 存储：`trustgraph-flow/trustgraph/librarian/blob_store.py`
Cassandra 表：`trustgraph-flow/trustgraph/tables/library.py`
API 模式：`trustgraph-base/trustgraph/schema/services/library.py`

### 当前限制

当前设计存在几个相互影响的内存和用户体验问题：

1. **原子上传操作**: 整个文档必须在一个请求中传输。
   大型文档需要长时间运行的请求，并且在连接失败时没有进度指示和重试机制。
   

2. **API 设计**: 无论是 REST 还是 WebSocket API，都期望在单个消息中接收完整的文档。
   模式 (`LibrarianRequest`) 包含一个 `content` 字段，其中包含整个 base64 编码的文档。
   

3. **Librarian 内存**: librarian 服务在将文档上传到 S3 之前，将其完全解码到内存中。
   对于一个 500MB 的 PDF 文件，这意味着需要在进程内存中保留 500MB+。
   

4. **PDF 解码器内存**: 当处理开始时，PDF 解码器将整个 PDF 文件加载到内存中以提取文本。
   PyPDF 和类似的库通常需要访问整个文档。
   

5. **分块器内存**: 文本分块器接收完整的提取文本，并在生成块时将其保存在内存中。
   

**内存影响示例** (500MB PDF)：
网关：~700MB (base64 编码开销)
Librarian：~500MB (解码后的字节)
PDF 解码器：~500MB + 提取缓冲区
分块器：提取的文本 (可变，可能高达 100MB+)

对于单个大型文档，峰值内存总和可能超过 2GB。

## 技术设计

### 设计原则

1. **API 接口**: 所有客户端交互都通过 librarian API 进行。客户端
   没有直接访问或了解底层 S3/Garage 存储的权限。

2. **S3 多部分上传**: 使用标准的 S3 多部分上传。
   这在所有兼容 S3 的系统中都得到广泛支持 (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2 等)，确保可移植性。

3. **原子完成**: S3 多部分上传本质上是原子的 - 上传的
   部分在调用 `CompleteMultipartUpload` 之前是不可见的。不需要临时
   文件或重命名操作。

4. **可跟踪的状态**: 上传会话在 Cassandra 中跟踪，从而
   提供对未完成上传的可见性，并启用恢复功能。

### 分块上传流程

```
Client                    Librarian API                   S3/Garage
  │                            │                              │
  │── begin-upload ───────────►│                              │
  │   (metadata, size)         │── CreateMultipartUpload ────►│
  │                            │◄── s3_upload_id ─────────────│
  │◄── upload_id ──────────────│   (store session in          │
  │                            │    Cassandra)                │
  │                            │                              │
  │── upload-chunk ───────────►│                              │
  │   (upload_id, index, data) │── UploadPart ───────────────►│
  │                            │◄── etag ─────────────────────│
  │◄── ack + progress ─────────│   (store etag in session)    │
  │         ⋮                  │         ⋮                    │
  │   (repeat for all chunks)  │                              │
  │                            │                              │
  │── complete-upload ────────►│                              │
  │   (upload_id)              │── CompleteMultipartUpload ──►│
  │                            │   (parts coalesced by S3)    │
  │                            │── store doc metadata ───────►│ Cassandra
  │◄── document_id ────────────│   (delete session)           │
```

客户端从不直接与 S3 交互。 库（librarian）在内部将我们的分块上传 API 转换为 S3 的多部分操作。

### Librarian API 操作
### 图书管理员API操作

#### `begin-upload`

初始化一个分块上传会话。

请求：
```json
{
  "operation": "begin-upload",
  "document-metadata": {
    "id": "doc-123",
    "kind": "application/pdf",
    "title": "Large Document",
    "user": "user-id",
    "tags": ["tag1", "tag2"]
  },
  "total-size": 524288000,
  "chunk-size": 5242880
}
```

响应：
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

馆员：
1. 生成一个唯一的 `upload_id` 和 `object_id` (用于对象存储的 UUID)
2. 调用 S3 `CreateMultipartUpload`，接收 `s3_upload_id`
3. 在 Cassandra 中创建会话记录
4. 将 `upload_id` 返回给客户端

#### `upload-chunk`

上传单个分块。

请求：
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

响应：
```json
{
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "chunks-received": 1,
  "total-chunks": 100,
  "bytes-received": 5242880,
  "total-bytes": 524288000
}
```

馆员：
1. 通过 `upload_id` 查找会话。
2. 验证所有权（用户必须与会话创建者匹配）。
3. 使用块数据调用 S3 `UploadPart`，接收 `etag`。
4. 使用块索引和 etag 更新会话记录。
5. 将进度返回给客户端。

失败的块可以重试 - 只需要再次发送相同的 `chunk-index`。

#### `complete-upload`

完成上传并创建文档。

请求：
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

响应：
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

馆员：
1. 查找会话，验证是否接收到所有分块。
2. 使用 part etags 调用 S3 `CompleteMultipartUpload` (S3 内部合并分块，馆员无需消耗内存)。
   3. 在 Cassandra 中创建文档记录，包含元数据和对象引用。
4. 删除上传会话记录。
5. 将文档 ID 返回给客户端。


#### `abort-upload`

取消正在进行的上传。

请求：
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

馆员：
1. 调用 S3 `AbortMultipartUpload` 清理部分数据。
2. 从 Cassandra 中删除会话记录。

#### `get-upload-status`

查询上传状态（用于断点续传功能）。

请求：
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

响应：
```json
{
  "upload-id": "upload-abc-123",
  "state": "in-progress",
  "chunks-received": [0, 1, 2, 5, 6],
  "missing-chunks": [3, 4, 7, 8],
  "total-chunks": 100,
  "bytes-received": 36700160,
  "total-bytes": 524288000
}
```

#### `list-uploads`

获取用户未完成上传的列表。

请求：
```json
{
  "operation": "list-uploads"
}
```

响应：
```json
{
  "uploads": [
    {
      "upload-id": "upload-abc-123",
      "document-metadata": { "title": "Large Document", ... },
      "progress": { "chunks-received": 43, "total-chunks": 100 },
      "created-at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### 上传会话存储

在 Cassandra 中跟踪正在进行的上传：

```sql
CREATE TABLE upload_session (
    upload_id text PRIMARY KEY,
    user text,
    document_id text,
    document_metadata text,      -- JSON: title, kind, tags, comments, etc.
    s3_upload_id text,           -- internal, for S3 operations
    object_id uuid,              -- target blob ID
    total_size bigint,
    chunk_size int,
    total_chunks int,
    chunks_received map<int, text>,  -- chunk_index → etag
    created_at timestamp,
    updated_at timestamp
) WITH default_time_to_live = 86400;  -- 24 hour TTL

CREATE INDEX upload_session_user ON upload_session (user);
```

**TTL 行为：**
如果未完成，会话将在 24 小时后过期。
当 Cassandra TTL 过期时，会话记录将被删除。
孤立的 S3 分片由 S3 生命周期策略清理（在桶上配置）。

### 故障处理和原子性

**分块上传失败：**
客户端重试失败的分块（使用相同的 `upload_id` 和 `chunk-index`）。
S3 `UploadPart` 对于相同的分片编号是幂等的。
会话跟踪哪些分块已成功。

**客户端在上传过程中断连接：**
会话仍然存在于 Cassandra 中，记录了已接收的分块。
客户端可以调用 `get-upload-status` 以查看缺少的内容。
通过仅上传缺失的分块来恢复，然后调用 `complete-upload`。

**完整上传失败：**
S3 `CompleteMultipartUpload` 是原子性的 - 要么完全成功，要么完全失败。
如果失败，分片仍然存在，客户端可以重试 `complete-upload`。
永远不会出现部分文档。

**会话过期：**
Cassandra TTL 在 24 小时后删除会话记录。
S3 桶生命周期策略清理不完整的多部分上传。
不需要手动清理。

### S3 多部分原子性

S3 多部分上传提供了内置的原子性：

1. **分片不可见：** 上传的分片不能作为对象访问。
   它们仅作为不完整的多部分上传的分片存在。

2. **原子完成：** `CompleteMultipartUpload` 要么成功（对象
   以原子方式出现），要么失败（未创建对象）。 没有部分状态。

3. **无需重命名：** 最终对象键在
   `CreateMultipartUpload` 时指定。 分片直接合并到该键。

4. **服务器端合并：** S3 内部合并分片。 库管理员
   永远不会读取分片 - 无论文档大小如何，都没有内存开销。

### BlobStore 扩展

**文件：** `trustgraph-flow/trustgraph/librarian/blob_store.py`

添加多部分上传方法：

```python
class BlobStore:
    # Existing methods...

    def create_multipart_upload(self, object_id: UUID, kind: str) -> str:
        """Initialize multipart upload, return s3_upload_id."""
        # minio client: create_multipart_upload()

    def upload_part(
        self, object_id: UUID, s3_upload_id: str,
        part_number: int, data: bytes
    ) -> str:
        """Upload a single part, return etag."""
        # minio client: upload_part()
        # Note: S3 part numbers are 1-indexed

    def complete_multipart_upload(
        self, object_id: UUID, s3_upload_id: str,
        parts: List[Tuple[int, str]]  # [(part_number, etag), ...]
    ) -> None:
        """Finalize multipart upload."""
        # minio client: complete_multipart_upload()

    def abort_multipart_upload(
        self, object_id: UUID, s3_upload_id: str
    ) -> None:
        """Cancel multipart upload, clean up parts."""
        # minio client: abort_multipart_upload()
```

### 分块大小的考量

**S3 最小值**: 每个分块 5MB (除了最后一个分块)
**S3 最大值**: 每个上传 10,000 个分块
**实际默认值**: 5MB 分块
  500MB 文档 = 100 个分块
  5GB 文档 = 1,000 个分块
**进度粒度**: 较小的分块 = 更精细的进度更新
**网络效率**: 较大的分块 = 更少的网络请求

分块大小可以在一定范围内由客户端配置 (5MB - 100MB)。

### 文档处理：流式检索

上传流程旨在高效地将文档存储到存储系统中。处理流程旨在提取和分块文档，而无需将整个文档加载到内存中。



#### 设计原则：标识符，而非内容

目前，当触发处理时，文档内容通过 Pulsar 消息传递。这会将整个文档加载到内存中。 应该这样做：


Pulsar 消息仅携带 **文档标识符**
处理程序直接从 librarian 获取文档内容
获取过程是 **流式传输到临时文件**
文档特定的解析 (PDF、文本等) 使用文件，而不是内存缓冲区

这使得 librarian 不依赖于文档结构。 PDF 解析、文本
提取和其他特定于格式的逻辑保留在各自的解码器中。

#### 处理流程

```
Pulsar              PDF Decoder                Librarian              S3
  │                      │                          │                  │
  │── doc-id ───────────►│                          │                  │
  │  (processing msg)    │                          │                  │
  │                      │                          │                  │
  │                      │── stream-document ──────►│                  │
  │                      │   (doc-id)               │── GetObject ────►│
  │                      │                          │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (write to temp file)   │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (append to temp file)  │                  │
  │                      │         ⋮                │         ⋮        │
  │                      │◄── EOF ──────────────────│                  │
  │                      │                          │                  │
  │                      │   ┌──────────────────────────┐              │
  │                      │   │ temp file on disk        │              │
  │                      │   │ (memory stays bounded)   │              │
  │                      │   └────────────┬─────────────┘              │
  │                      │                │                            │
  │                      │   PDF library opens file                    │
  │                      │   extract page 1 text ──►  chunker          │
  │                      │   extract page 2 text ──►  chunker          │
  │                      │         ⋮                                   │
  │                      │   close file                                │
  │                      │   delete temp file                          │
```

#### 图书管理员流式 API

添加一个流式文档检索操作：

**`stream-document`**

请求：
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

响应：流式传输的二进制数据块（不是单个响应）。

对于 REST API，这会返回一个带有 `Transfer-Encoding: chunked` 的流式响应。

对于内部服务之间的调用（处理器到图书管理员），可能如下：
通过预签名 URL 进行直接 S3 流式传输（如果内部网络允许）。
通过服务协议进行分块响应。
一个专用的流式传输端点。

关键要求：数据以块的形式流动，永远不会完全缓存在图书管理员中。

#### PDF 解码器更改

**当前实现**（占用大量内存）：

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**新实现** (临时文件，增量式)：

```python
def decode_pdf_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield extracted text page by page."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream document to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Open PDF from file (not memory)
        reader = PdfReader(tmp.name)

        # Yield pages incrementally
        for page in reader.pages:
            yield page.extract_text()

        # tmp file auto-deleted on context exit
```

内存配置：
临时文件在磁盘上：大小为 PDF 文件的大小（磁盘很便宜）
内存中：一次加载一页的文本
峰值内存：受限，与文档大小无关

#### 文本文档解码器更改

对于纯文本文档，更加简单 - 不需要临时文件：

```python
def decode_text_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield text in chunks as it streams from storage."""

    buffer = ""
    for chunk in librarian_client.stream_document(doc_id):
        buffer += chunk.decode('utf-8')

        # Yield complete lines/paragraphs as they arrive
        while '\n\n' in buffer:
            paragraph, buffer = buffer.split('\n\n', 1)
            yield paragraph + '\n\n'

    # Yield remaining buffer
    if buffer:
        yield buffer
```

文本文件可以直接流式传输，无需临时文件，因为它们的结构是线性的。


#### 流式分块集成

分块器接收文本的迭代器（页面或段落），并逐步生成块：


```python
class StreamingChunker:
    def __init__(self, chunk_size: int, overlap: int):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process(self, text_stream: Iterator[str]) -> Iterator[str]:
        """Yield chunks as text arrives."""
        buffer = ""

        for text_segment in text_stream:
            buffer += text_segment

            while len(buffer) >= self.chunk_size:
                chunk = buffer[:self.chunk_size]
                yield chunk
                # Keep overlap for context continuity
                buffer = buffer[self.chunk_size - self.overlap:]

        # Yield remaining buffer as final chunk
        if buffer.strip():
            yield buffer
```

#### 端到端处理流程

```python
async def process_document(doc_id: str, librarian_client, embedder):
    """Process document with bounded memory."""

    # Get document metadata to determine type
    metadata = await librarian_client.get_document_metadata(doc_id)

    # Select decoder based on document type
    if metadata.kind == 'application/pdf':
        text_stream = decode_pdf_streaming(doc_id, librarian_client)
    elif metadata.kind == 'text/plain':
        text_stream = decode_text_streaming(doc_id, librarian_client)
    else:
        raise UnsupportedDocumentType(metadata.kind)

    # Chunk incrementally
    chunker = StreamingChunker(chunk_size=1000, overlap=100)

    # Process each chunk as it's produced
    for chunk in chunker.process(text_stream):
        # Generate embeddings, store in vector DB, etc.
        embedding = await embedder.embed(chunk)
        await store_chunk(doc_id, chunk, embedding)
```

在任何时候，完整的文档或完整的提取文本都不会保存在内存中。

#### 临时文件注意事项

**位置：** 使用系统临时目录（`/tmp` 或等效目录）。对于
容器化部署，请确保临时目录有足够的空间，并且位于快速存储上（如果可能，不要使用网络挂载）。


**清理：** 使用上下文管理器（`with tempfile...`）以确保即使在出现异常时也能进行清理。


**并发处理：** 每个处理任务都有自己的临时文件。
并行文档处理之间不会发生冲突。

**磁盘空间：** 临时文件是短暂存在的（处理过程中的持续时间）。
对于一个 500MB 的 PDF 文件，在处理过程中需要 500MB 的临时空间。如果磁盘空间受限，可以在上传时强制执行大小限制。


### 统一处理接口：子文档

PDF 提取和文本文档处理需要输入到相同的下游流程（分块 → 嵌入 → 存储）。为了实现这一点，并使用一致的“按 ID 检索”接口，提取的文本块被存储回 librarian，作为子文档。




#### 使用子文档的处理流程

```
PDF Document                                         Text Document
     │                                                     │
     ▼                                                     │
pdf-extractor                                              │
     │                                                     │
     │ (stream PDF from librarian)                         │
     │ (extract page 1 text)                               │
     │ (store as child doc → librarian)                    │
     │ (extract page 2 text)                               │
     │ (store as child doc → librarian)                    │
     │         ⋮                                           │
     ▼                                                     ▼
[child-doc-id, child-doc-id, ...]                    [doc-id]
     │                                                     │
     └─────────────────────┬───────────────────────────────┘
                           ▼
                       chunker
                           │
                           │ (receives document ID)
                           │ (streams content from librarian)
                           │ (chunks incrementally)
                           ▼
                    [chunks → embedding → storage]
```

分块器具有一个统一的接口：
接收文档 ID（通过 Pulsar）
从 Librarian 流式传输内容
将其分块

它不知道也不关心该 ID 指的是：
用户上传的文本文档
从 PDF 页面提取的文本块
任何未来的文档类型

#### 子文档元数据

扩展文档模式以跟踪父/子关系：

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**文档类型：**

| `document_type` | 描述 |
|-----------------|-------------|
| `source` | 用户上传的文档（PDF、文本等） |
| `extracted` | 源自源文档（例如，PDF 页面文本） |

**元数据字段：**

| 字段 | 源文档 | 提取的子文档 |
|-------|-----------------|-----------------|
| `id` | 用户提供或生成 | 生成（例如，`{parent-id}-page-{n}`） |
| `parent_id` | `NULL` | 父文档 ID |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`，等等 | `text/plain` |
| `title` | 用户提供 | 生成（例如，“Report.pdf 的第 3 页”） |
| `user` | 经过身份验证的用户 | 与父文档相同 |

#### 子文档的 Librarian API

**创建子文档**（内部，由 pdf-extractor 使用）：

```json
{
  "operation": "add-child-document",
  "parent-id": "doc-123",
  "document-metadata": {
    "id": "doc-123-page-1",
    "kind": "text/plain",
    "title": "Page 1"
  },
  "content": "<base64-encoded-text>"
}
```

对于较小的提取文本（典型页面文本通常小于 100KB），单次上传是可以接受的。对于非常大的文本提取，可以使用分块上传。



**列出子文档（用于调试/管理）：**

```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

响应：
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### 用户可见的行为

**`list-documents` 默认行为：**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

只有顶层（源）文档才会出现在用户的文档列表中。
子文档默认会被过滤掉。

**可选的包含子文档标志**（用于管理员/调试）：

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

#### 级联删除

当父级文档被删除时，所有子级必须被删除：

```python
def delete_document(doc_id: str):
    # Find all children
    children = query("SELECT id, object_id FROM document WHERE parent_id = ?", doc_id)

    # Delete child blobs from S3
    for child in children:
        blob_store.delete(child.object_id)

    # Delete child metadata from Cassandra
    execute("DELETE FROM document WHERE parent_id = ?", doc_id)

    # Delete parent blob and metadata
    parent = get_document(doc_id)
    blob_store.delete(parent.object_id)
    execute("DELETE FROM document WHERE id = ? AND user = ?", doc_id, user)
```

#### 存储注意事项

提取的文本块会重复内容：
原始 PDF 文件存储在 Garage 中
每个页面的提取文本也存储在 Garage 中

这种权衡方案可以实现：
**统一的分块接口**: 分块器始终通过 ID 获取数据
**恢复/重试**: 可以在分块阶段重新启动，而无需重新提取 PDF
**调试**: 可以检查提取的文本
**职责分离**: PDF 提取器和分块器是独立的服务

对于一个 500MB 的 PDF 文件，其中包含 200 页，平均每页 5KB 的文本：
PDF 存储：500MB
提取的文本存储：约 1MB
额外开销：可以忽略不计

#### PDF 提取器输出

PDF 提取器在处理文档后：

1. 从 librarian 流式传输 PDF 到临时文件
2. 逐页提取文本
3. 对于每一页，将提取的文本作为子文档通过 librarian 存储
4. 将子文档 ID 发送到分块器队列

```python
async def extract_pdf(doc_id: str, librarian_client, output_queue):
    """Extract PDF pages and store as child documents."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream PDF to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Extract pages
        reader = PdfReader(tmp.name)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()

            # Store as child document
            child_id = f"{doc_id}-page-{page_num}"
            await librarian_client.add_child_document(
                parent_id=doc_id,
                document_id=child_id,
                kind="text/plain",
                title=f"Page {page_num}",
                content=text.encode('utf-8')
            )

            # Send to chunker queue
            await output_queue.send(child_id)
```

分块器接收这些子 ID，并以与处理用户上传的文本文档完全相同的方式处理它们。
如何处理用户上传的文本文档。

### 客户端更新

#### Python SDK

Python SDK (`trustgraph-base/trustgraph/api/library.py`) 应该能够透明地处理分块上传。公共接口保持不变：
分块上传。公共接口保持不变：

```python
# Existing interface - no change for users
library.add_document(
    id="doc-123",
    title="Large Report",
    kind="application/pdf",
    content=large_pdf_bytes,  # Can be hundreds of MB
    tags=["reports"]
)
```

内部，SDK 会检测文档大小并切换策略：

```python
class Library:
    CHUNKED_UPLOAD_THRESHOLD = 2 * 1024 * 1024  # 2MB

    def add_document(self, id, title, kind, content, tags=None, ...):
        if len(content) < self.CHUNKED_UPLOAD_THRESHOLD:
            # Small document: single operation (existing behavior)
            return self._add_document_single(id, title, kind, content, tags)
        else:
            # Large document: chunked upload
            return self._add_document_chunked(id, title, kind, content, tags)

    def _add_document_chunked(self, id, title, kind, content, tags):
        # 1. begin-upload
        session = self._begin_upload(
            document_metadata={...},
            total_size=len(content),
            chunk_size=5 * 1024 * 1024
        )

        # 2. upload-chunk for each chunk
        for i, chunk in enumerate(self._chunk_bytes(content, session.chunk_size)):
            self._upload_chunk(session.upload_id, i, chunk)

        # 3. complete-upload
        return self._complete_upload(session.upload_id)
```

**进度回调** (可选的增强功能)：

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

这允许用户界面显示上传进度，而无需更改基本 API。

#### 命令行工具

**`tg-add-library-document`** 保持不变：

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

可以添加可选的进度显示：

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**已移除的旧工具：**

`tg-load-pdf` - 已过时，请使用 `tg-add-library-document`
`tg-load-text` - 已过时，请使用 `tg-add-library-document`

**管理员/调试命令**（可选，优先级较低）：

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

这些可能只是现有命令上的标志，而不是单独的工具。

#### API 规范更新

OpenAPI 规范 (`specs/api/paths/librarian.yaml`) 需要更新以下内容：

**新操作：**

`begin-upload` - 初始化分块上传会话
`upload-chunk` - 上传单个分块
`complete-upload` - 完成上传
`abort-upload` - 取消上传
`get-upload-status` - 查询上传进度
`list-uploads` - 列出用户未完成的上传
`stream-document` - 流式文档检索
`add-child-document` - 存储提取的文本（内部）
`list-children` - 列出子文档（管理员）

**修改后的操作：**

`list-documents` - 添加 `include-children` 参数

**新的模式：**

`ChunkedUploadBeginRequest`
`ChunkedUploadBeginResponse`
`ChunkedUploadChunkRequest`
`ChunkedUploadChunkResponse`
`UploadSession`
`UploadProgress`

**WebSocket 规范更新** (`specs/websocket/`)：

镜像 REST 操作以供 WebSocket 客户端使用，从而实现上传过程的实时
进度更新。

#### 用户体验注意事项

API 规范的更新可以实现前端改进：

**上传进度 UI：**
显示已上传分块的进度条
剩余预估时间
暂停/恢复功能

**错误恢复：**
中断的上传可以选择“恢复上传”
重新连接时，显示挂起的上传列表

**大型文件处理：**
客户端文件大小检测
大型文件的自动分块上传
长时间上传时提供清晰的反馈

这些用户体验改进需要前端工作，并由更新后的 API 规范提供指导。
