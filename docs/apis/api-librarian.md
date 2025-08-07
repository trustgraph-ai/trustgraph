# TrustGraph Librarian API

This API provides document library management for TrustGraph. It handles document storage, 
metadata management, and processing orchestration using hybrid storage (MinIO for content, 
Cassandra for metadata) with multi-user support.

## Request/response

### Request

The request contains the following fields:
- `operation`: The operation to perform (see operations below)
- `document_id`: Document identifier (for document operations)
- `document_metadata`: Document metadata object (for add/update operations)
  - `id`: Document identifier (required)
  - `time`: Unix timestamp in seconds as a float (required for add operations)
  - `kind`: MIME type of document (required, e.g., "text/plain", "application/pdf")
  - `title`: Document title (optional)
  - `comments`: Document comments (optional)
  - `user`: Document owner (required)
  - `tags`: Array of tags (optional)
  - `metadata`: Array of RDF triples (optional) - each triple has:
    - `s`: Subject with `v` (value) and `e` (is_uri boolean)
    - `p`: Predicate with `v` (value) and `e` (is_uri boolean)
    - `o`: Object with `v` (value) and `e` (is_uri boolean)
- `content`: Document content as base64-encoded bytes (for add operations)
- `processing_id`: Processing job identifier (for processing operations)
- `processing_metadata`: Processing metadata object (for add-processing)
- `user`: User identifier (required for most operations)
- `collection`: Collection filter (optional for list operations)
- `criteria`: Query criteria array (for filtering operations)

### Response

The response contains the following fields:
- `error`: Error information if operation fails
- `document_metadata`: Single document metadata (for get operations)
- `content`: Document content as base64-encoded bytes (for get-content)
- `document_metadatas`: Array of document metadata (for list operations)
- `processing_metadatas`: Array of processing metadata (for list-processing)

## Document Operations

### ADD-DOCUMENT - Add Document to Library

Request:
```json
{
    "operation": "add-document",
    "document_metadata": {
        "id": "doc-123",
        "time": 1640995200.0,
        "kind": "application/pdf",
        "title": "Research Paper",
        "comments": "Important research findings",
        "user": "alice",
        "tags": ["research", "ai", "machine-learning"],
        "metadata": [
            {
                "s": {
                    "v": "http://example.com/doc-123",
                    "e": true
                },
                "p": {
                    "v": "http://purl.org/dc/elements/1.1/creator",
                    "e": true
                },
                "o": {
                    "v": "Dr. Smith",
                    "e": false
                }
            }
        ]
    },
    "content": "JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCg=="
}
```

Response:
```json
{}
```

### GET-DOCUMENT-METADATA - Get Document Metadata

Request:
```json
{
    "operation": "get-document-metadata",
    "document_id": "doc-123",
    "user": "alice"
}
```

Response:
```json
{
    "document_metadata": {
        "id": "doc-123",
        "time": 1640995200.0,
        "kind": "application/pdf",
        "title": "Research Paper",
        "comments": "Important research findings",
        "user": "alice",
        "tags": ["research", "ai", "machine-learning"],
        "metadata": [
            {
                "s": {
                    "v": "http://example.com/doc-123",
                    "e": true
                },
                "p": {
                    "v": "http://purl.org/dc/elements/1.1/creator",
                    "e": true
                },
                "o": {
                    "v": "Dr. Smith",
                    "e": false
                }
            }
        ]
    }
}
```

### GET-DOCUMENT-CONTENT - Get Document Content

Request:
```json
{
    "operation": "get-document-content",
    "document_id": "doc-123",
    "user": "alice"
}
```

Response:
```json
{
    "content": "JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCg=="
}
```

### LIST-DOCUMENTS - List User's Documents

Request:
```json
{
    "operation": "list-documents",
    "user": "alice",
    "collection": "research"
}
```

Response:
```json
{
    "document_metadatas": [
        {
            "id": "doc-123",
            "time": 1640995200.0,
            "kind": "application/pdf",
            "title": "Research Paper",
            "comments": "Important research findings",
            "user": "alice",
            "tags": ["research", "ai"]
        },
        {
            "id": "doc-124",
            "time": 1640995300.0,
            "kind": "text/plain",
            "title": "Meeting Notes",
            "comments": "Team meeting discussion",
            "user": "alice",
            "tags": ["meeting", "notes"]
        }
    ]
}
```

### UPDATE-DOCUMENT - Update Document Metadata

Request:
```json
{
    "operation": "update-document",
    "document_metadata": {
        "id": "doc-123",
        "time": 1640995500.0,
        "title": "Updated Research Paper",
        "comments": "Updated findings and conclusions",
        "user": "alice",
        "tags": ["research", "ai", "machine-learning", "updated"],
        "metadata": []
    }
}
```

Response:
```json
{}
```

### REMOVE-DOCUMENT - Remove Document

Request:
```json
{
    "operation": "remove-document",
    "document_id": "doc-123",
    "user": "alice"
}
```

Response:
```json
{}
```

## Processing Operations

### ADD-PROCESSING - Start Document Processing

Request:
```json
{
    "operation": "add-processing",
    "processing_metadata": {
        "id": "proc-456",
        "document_id": "doc-123",
        "time": 1640995400.0,
        "flow": "pdf-extraction",
        "user": "alice",
        "collection": "research",
        "tags": ["extraction", "nlp"]
    }
}
```

Response:
```json
{}
```

### LIST-PROCESSING - List Processing Jobs

Request:
```json
{
    "operation": "list-processing",
    "user": "alice",
    "collection": "research"
}
```

Response:
```json
{
    "processing_metadatas": [
        {
            "id": "proc-456",
            "document_id": "doc-123",
            "time": 1640995400.0,
            "flow": "pdf-extraction",
            "user": "alice",
            "collection": "research",
            "tags": ["extraction", "nlp"]
        }
    ]
}
```

### REMOVE-PROCESSING - Stop Processing Job

Request:
```json
{
    "operation": "remove-processing",
    "processing_id": "proc-456",
    "user": "alice"
}
```

Response:
```json
{}
```

## REST service

The REST service is available at `/api/v1/librarian` and accepts the above request formats.

## Websocket

Requests have a `request` object containing the operation fields.
Responses have a `response` object containing the response fields.

Request:
```json
{
    "id": "unique-request-id",
    "service": "librarian",
    "request": {
        "operation": "list-documents",
        "user": "alice"
    }
}
```

Response:
```json
{
    "id": "unique-request-id",
    "response": {
        "document_metadatas": [...]
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Librarian API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/library.py

Default request queue:
`non-persistent://tg/request/librarian`

Default response queue:
`non-persistent://tg/response/librarian`

Request schema:
`trustgraph.schema.LibrarianRequest`

Response schema:
`trustgraph.schema.LibrarianResponse`

## Python SDK

The Python SDK provides convenient access to the Librarian API:

```python
from trustgraph.api.library import LibrarianClient

client = LibrarianClient()

# Add a document
with open("document.pdf", "rb") as f:
    content = f.read()
    
await client.add_document(
    doc_id="doc-123",
    title="Research Paper",
    content=content,
    user="alice",
    tags=["research", "ai"]
)

# Get document metadata
metadata = await client.get_document_metadata("doc-123", "alice")

# List documents
documents = await client.list_documents("alice", collection="research")

# Start processing
await client.add_processing(
    processing_id="proc-456",
    document_id="doc-123",
    flow="pdf-extraction",
    user="alice"
)
```

## Features

- **Hybrid Storage**: MinIO for content, Cassandra for metadata
- **Multi-user Support**: User-based document ownership and access control
- **Rich Metadata**: RDF-style metadata triples and tagging system
- **Processing Integration**: Automatic triggering of document processing workflows
- **Content Types**: Support for multiple document formats (PDF, text, etc.)
- **Collection Management**: Optional document grouping by collection
- **Metadata Search**: Query documents by metadata criteria

## Use Cases

- **Document Management**: Store and organize documents with rich metadata
- **Knowledge Extraction**: Process documents to extract structured knowledge
- **Research Libraries**: Manage collections of research papers and documents
- **Content Processing**: Orchestrate document processing workflows
- **Multi-tenant Systems**: Support multiple users with isolated document libraries