# Large Document Loading Technical Specification

## Overview

This specification addresses scalability and user experience issues when loading
large documents into TrustGraph. The current architecture treats document upload
as a single atomic operation, causing memory pressure at multiple points in the
pipeline and providing no feedback or recovery options to users.

This implementation targets the following use cases:

1. **Large PDF Processing**: Upload and process multi-hundred-megabyte PDF files
   without exhausting memory
2. **Resumable Uploads**: Allow interrupted uploads to continue from where they
   left off rather than restarting
3. **Progress Feedback**: Provide users with real-time visibility into upload
   and processing progress
4. **Memory-Efficient Processing**: Process documents in a streaming fashion
   without holding entire files in memory

## Goals

- **Incremental Upload**: Support chunked document upload via REST and WebSocket
- **Resumable Transfers**: Enable recovery from interrupted uploads
- **Progress Visibility**: Provide upload/processing progress feedback to clients
- **Memory Efficiency**: Eliminate full-document buffering throughout the pipeline
- **Backward Compatibility**: Existing small-document workflows continue unchanged
- **Streaming Processing**: PDF decoding and text chunking operate on streams

## Background

### Current Architecture

Document submission flows through the following path:

1. **Client** submits document via REST (`POST /api/v1/librarian`) or WebSocket
2. **API Gateway** receives complete request with base64-encoded document content
3. **LibrarianRequestor** translates request to Pulsar message
4. **Librarian Service** receives message, decodes document into memory
5. **BlobStore** uploads document to Garage/S3
6. **Cassandra** stores metadata with object reference
7. For processing: document retrieved from S3, decoded, chunked—all in memory

Key files:
- REST/WebSocket entry: `trustgraph-flow/trustgraph/gateway/service.py`
- Librarian core: `trustgraph-flow/trustgraph/librarian/librarian.py`
- Blob storage: `trustgraph-flow/trustgraph/librarian/blob_store.py`
- Cassandra tables: `trustgraph-flow/trustgraph/tables/library.py`
- API schema: `trustgraph-base/trustgraph/schema/services/library.py`

### Current Limitations

The current design has several compounding memory and UX issues:

1. **Atomic Upload Operation**: The entire document must be transmitted in a
   single request. Large documents require long-running requests with no
   progress indication and no retry mechanism if the connection fails.

2. **API Design**: Both REST and WebSocket APIs expect the complete document
   in a single message. The schema (`LibrarianRequest`) has a single `content`
   field containing the entire base64-encoded document.

3. **Librarian Memory**: The librarian service decodes the entire document
   into memory before uploading to S3. For a 500MB PDF, this means holding
   500MB+ in process memory.

4. **PDF Decoder Memory**: When processing begins, the PDF decoder loads the
   entire PDF into memory to extract text. PyPDF and similar libraries
   typically require full document access.

5. **Chunker Memory**: The text chunker receives the complete extracted text
   and holds it in memory while producing chunks.

**Memory Impact Example** (500MB PDF):
- Gateway: ~700MB (base64 encoding overhead)
- Librarian: ~500MB (decoded bytes)
- PDF Decoder: ~500MB + extraction buffers
- Chunker: extracted text (variable, potentially 100MB+)

Total peak memory can exceed 2GB for a single large document.

## Technical Design

### Design Principles

1. **API Facade**: All client interaction goes through the librarian API. Clients
   have no direct access to or knowledge of the underlying S3/Garage storage.

2. **S3 Multipart Upload**: Use standard S3 multipart upload under the hood.
   This is widely supported across S3-compatible systems (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2, etc.) ensuring portability.

3. **Atomic Completion**: S3 multipart uploads are inherently atomic - uploaded
   parts are invisible until `CompleteMultipartUpload` is called. No temporary
   files or rename operations needed.

4. **Trackable State**: Upload sessions tracked in Cassandra, providing
   visibility into incomplete uploads and enabling resume capability.

### Chunked Upload Flow

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

The client never interacts with S3 directly. The librarian translates between
our chunked upload API and S3 multipart operations internally.

### Librarian API Operations

#### `begin-upload`

Initialize a chunked upload session.

Request:
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

Response:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

The librarian:
1. Generates a unique `upload_id` and `object_id` (UUID for blob storage)
2. Calls S3 `CreateMultipartUpload`, receives `s3_upload_id`
3. Creates session record in Cassandra
4. Returns `upload_id` to client

#### `upload-chunk`

Upload a single chunk.

Request:
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

Response:
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

The librarian:
1. Looks up session by `upload_id`
2. Validates ownership (user must match session creator)
3. Calls S3 `UploadPart` with chunk data, receives `etag`
4. Updates session record with chunk index and etag
5. Returns progress to client

Failed chunks can be retried - just send the same `chunk-index` again.

#### `complete-upload`

Finalize the upload and create the document.

Request:
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

Response:
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

The librarian:
1. Looks up session, verifies all chunks received
2. Calls S3 `CompleteMultipartUpload` with part etags (S3 coalesces parts
   internally - zero memory cost to librarian)
3. Creates document record in Cassandra with metadata and object reference
4. Deletes upload session record
5. Returns document ID to client

#### `abort-upload`

Cancel an in-progress upload.

Request:
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

The librarian:
1. Calls S3 `AbortMultipartUpload` to clean up parts
2. Deletes session record from Cassandra

#### `get-upload-status`

Query status of an upload (for resume capability).

Request:
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

Response:
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

List incomplete uploads for a user.

Request:
```json
{
  "operation": "list-uploads"
}
```

Response:
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

### Upload Session Storage

Track in-progress uploads in Cassandra:

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

**TTL Behavior:**
- Sessions expire after 24 hours if not completed
- When Cassandra TTL expires, the session record is deleted
- Orphaned S3 parts are cleaned up by S3 lifecycle policy (configure on bucket)

### Failure Handling and Atomicity

**Chunk upload failure:**
- Client retries the failed chunk (same `upload_id` and `chunk-index`)
- S3 `UploadPart` is idempotent for the same part number
- Session tracks which chunks succeeded

**Client disconnect mid-upload:**
- Session remains in Cassandra with received chunks recorded
- Client can call `get-upload-status` to see what's missing
- Resume by uploading only missing chunks, then `complete-upload`

**Complete-upload failure:**
- S3 `CompleteMultipartUpload` is atomic - either succeeds fully or fails
- On failure, parts remain and client can retry `complete-upload`
- No partial document is ever visible

**Session expiry:**
- Cassandra TTL deletes session record after 24 hours
- S3 bucket lifecycle policy cleans up incomplete multipart uploads
- No manual cleanup required

### S3 Multipart Atomicity

S3 multipart uploads provide built-in atomicity:

1. **Parts are invisible**: Uploaded parts cannot be accessed as objects.
   They exist only as parts of an incomplete multipart upload.

2. **Atomic completion**: `CompleteMultipartUpload` either succeeds (object
   appears atomically) or fails (no object created). No partial state.

3. **No rename needed**: The final object key is specified at
   `CreateMultipartUpload` time. Parts are coalesced directly to that key.

4. **Server-side coalesce**: S3 combines parts internally. The librarian
   never reads parts back - zero memory overhead regardless of document size.

### BlobStore Extensions

**File:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

Add multipart upload methods:

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

### Chunk Size Considerations

- **S3 minimum**: 5MB per part (except last part)
- **S3 maximum**: 10,000 parts per upload
- **Practical default**: 5MB chunks
  - 500MB document = 100 chunks
  - 5GB document = 1,000 chunks
- **Progress granularity**: Smaller chunks = finer progress updates
- **Network efficiency**: Larger chunks = fewer round trips

Chunk size could be client-configurable within bounds (5MB - 100MB).

### Document Processing: Streaming Retrieval

The upload flow addresses getting documents into storage efficiently. The
processing flow addresses extracting and chunking documents without loading
them entirely into memory.

#### Design Principle: Identifier, Not Content

Currently, when processing is triggered, document content flows through Pulsar
messages. This loads entire documents into memory. Instead:

- Pulsar messages carry only the **document identifier**
- Processors fetch document content directly from librarian
- Fetching happens as a **stream to temporary file**
- Document-specific parsing (PDF, text, etc.) works with files, not memory buffers

This keeps the librarian document-structure-agnostic. PDF parsing, text
extraction, and other format-specific logic stays in the respective decoders.

#### Processing Flow

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

#### Librarian Stream API

Add a streaming document retrieval operation:

**`stream-document`**

Request:
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

Response: Streamed binary chunks (not a single response).

For REST API, this returns a streaming response with `Transfer-Encoding: chunked`.

For internal service-to-service calls (processor to librarian), this could be:
- Direct S3 streaming via presigned URL (if internal network allows)
- Chunked responses over the service protocol
- A dedicated streaming endpoint

The key requirement: data flows in chunks, never fully buffered in librarian.

#### PDF Decoder Changes

**Current implementation** (memory-intensive):

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**New implementation** (temp file, incremental):

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

Memory profile:
- Temp file on disk: size of PDF (disk is cheap)
- In memory: one page's text at a time
- Peak memory: bounded, independent of document size

#### Text Document Decoder Changes

For plain text documents, even simpler - no temp file needed:

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

Text documents can stream directly without temp file since they're
linearly structured.

#### Streaming Chunker Integration

The chunker receives an iterator of text (pages or paragraphs) and produces
chunks incrementally:

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

#### End-to-End Processing Pipeline

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

At no point is the full document or full extracted text held in memory.

#### Temp File Considerations

**Location**: Use system temp directory (`/tmp` or equivalent). For
containerized deployments, ensure temp directory has sufficient space
and is on fast storage (not network-mounted if possible).

**Cleanup**: Use context managers (`with tempfile...`) to ensure cleanup
even on exceptions.

**Concurrent processing**: Each processing job gets its own temp file.
No conflicts between parallel document processing.

**Disk space**: Temp files are short-lived (duration of processing). For
a 500MB PDF, need 500MB temp space during processing. Size limit could
be enforced at upload time if disk space is constrained.

### Unified Processing Interface: Child Documents

PDF extraction and text document processing need to feed into the same
downstream pipeline (chunker → embeddings → storage). To achieve this with
a consistent "fetch by ID" interface, extracted text blobs are stored back
to librarian as child documents.

#### Processing Flow with Child Documents

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

The chunker has one uniform interface:
- Receive a document ID (via Pulsar)
- Stream content from librarian
- Chunk it

It doesn't know or care whether the ID refers to:
- A user-uploaded text document
- An extracted text blob from a PDF page
- Any future document type

#### Child Document Metadata

Extend the document schema to track parent/child relationships:

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**Document types:**

| `document_type` | Description |
|-----------------|-------------|
| `source` | User-uploaded document (PDF, text, etc.) |
| `extracted` | Derived from a source document (e.g., PDF page text) |

**Metadata fields:**

| Field | Source Document | Extracted Child |
|-------|-----------------|-----------------|
| `id` | user-provided or generated | generated (e.g., `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | parent document ID |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`, etc. | `text/plain` |
| `title` | user-provided | generated (e.g., "Page 3 of Report.pdf") |
| `user` | authenticated user | same as parent |

#### Librarian API for Child Documents

**Creating child documents** (internal, used by pdf-extractor):

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

For small extracted text (typical page text is < 100KB), single-operation
upload is acceptable. For very large text extractions, chunked upload
could be used.

**Listing child documents** (for debugging/admin):

```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

Response:
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### User-Facing Behavior

**`list-documents` default behavior:**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

Only top-level (source) documents appear in the user's document list.
Child documents are filtered out by default.

**Optional include-children flag** (for admin/debugging):

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

#### Cascade Delete

When a parent document is deleted, all children must be deleted:

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

#### Storage Considerations

Extracted text blobs do duplicate content:
- Original PDF stored in Garage
- Extracted text per page also stored in Garage

This tradeoff enables:
- **Uniform chunker interface**: Chunker always fetches by ID
- **Resume/retry**: Can restart at chunker stage without re-extracting PDF
- **Debugging**: Extracted text is inspectable
- **Separation of concerns**: PDF extractor and chunker are independent services

For a 500MB PDF with 200 pages averaging 5KB text per page:
- PDF storage: 500MB
- Extracted text storage: ~1MB total
- Overhead: negligible

#### PDF Extractor Output

The pdf-extractor, after processing a document:

1. Streams PDF from librarian to temp file
2. Extracts text page by page
3. For each page, stores extracted text as child document via librarian
4. Sends child document IDs to chunker queue

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

The chunker receives these child IDs and processes them identically to
how it would process a user-uploaded text document.

### Client Updates

#### Python SDK

The Python SDK (`trustgraph-base/trustgraph/api/library.py`) should handle
chunked uploads transparently. The public interface remains unchanged:

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

Internally, the SDK detects document size and switches strategy:

```python
class Library:
    CHUNKED_UPLOAD_THRESHOLD = 10 * 1024 * 1024  # 10MB

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

**Progress callbacks** (optional enhancement):

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

This allows UIs to display upload progress without changing the basic API.

#### CLI Tools

**`tg-add-library-document`** continues to work unchanged:

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

Optional progress display could be added:

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**Legacy tools removed:**

- `tg-load-pdf` - deprecated, use `tg-add-library-document`
- `tg-load-text` - deprecated, use `tg-add-library-document`

**Admin/debug commands** (optional, low priority):

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

These could be flags on the existing command rather than separate tools.

#### API Specification Updates

The OpenAPI spec (`specs/api/paths/librarian.yaml`) needs updates for:

**New operations:**

- `begin-upload` - Initialize chunked upload session
- `upload-chunk` - Upload individual chunk
- `complete-upload` - Finalize upload
- `abort-upload` - Cancel upload
- `get-upload-status` - Query upload progress
- `list-uploads` - List incomplete uploads for user
- `stream-document` - Streaming document retrieval
- `add-child-document` - Store extracted text (internal)
- `list-children` - List child documents (admin)

**Modified operations:**

- `list-documents` - Add `include-children` parameter

**New schemas:**

- `ChunkedUploadBeginRequest`
- `ChunkedUploadBeginResponse`
- `ChunkedUploadChunkRequest`
- `ChunkedUploadChunkResponse`
- `UploadSession`
- `UploadProgress`

**WebSocket spec updates** (`specs/websocket/`):

Mirror the REST operations for WebSocket clients, enabling real-time
progress updates during upload.

#### UX Considerations

The API spec updates enable frontend improvements:

**Upload progress UI:**
- Progress bar showing chunks uploaded
- Estimated time remaining
- Pause/resume capability

**Error recovery:**
- "Resume upload" option for interrupted uploads
- List of pending uploads on reconnect

**Large file handling:**
- Client-side file size detection
- Automatic chunked upload for large files
- Clear feedback during long uploads

These UX improvements require frontend work guided by the updated API spec.
