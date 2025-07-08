# TrustGraph Document Embeddings API

This API provides import, export, and query capabilities for document embeddings. It handles 
document chunks with their vector embeddings and metadata, supporting both real-time WebSocket 
operations and request/response patterns.

## Schema Overview

### DocumentEmbeddings Structure
- `metadata`: Document metadata (ID, user, collection, RDF triples)
- `chunks`: Array of document chunks with embeddings

### ChunkEmbeddings Structure
- `chunk`: Text chunk as bytes
- `vectors`: Array of vector embeddings (Array of Array of Double)

### DocumentEmbeddingsRequest Structure
- `vectors`: Query vector embeddings
- `limit`: Maximum number of results
- `user`: User identifier
- `collection`: Collection identifier

### DocumentEmbeddingsResponse Structure
- `error`: Error information if operation fails
- `documents`: Array of matching documents as bytes

## Import/Export Operations

### Import - WebSocket Endpoint

**Endpoint:** `/api/v1/flow/{flow}/import/document-embeddings`

**Method:** WebSocket connection

**Request Format:**
```json
{
    "metadata": {
        "id": "doc-123",
        "user": "alice",
        "collection": "research",
        "metadata": [
            {
                "s": {"v": "doc-123", "e": true},
                "p": {"v": "dc:title", "e": true},
                "o": {"v": "Research Paper", "e": false}
            }
        ]
    },
    "chunks": [
        {
            "chunk": "This is the first chunk of the document...",
            "vectors": [
                [0.1, 0.2, 0.3, 0.4],
                [0.5, 0.6, 0.7, 0.8]
            ]
        },
        {
            "chunk": "This is the second chunk...",
            "vectors": [
                [0.9, 0.8, 0.7, 0.6],
                [0.5, 0.4, 0.3, 0.2]
            ]
        }
    ]
}
```

**Response:** Import operations are fire-and-forget with no response payload.

### Export - WebSocket Endpoint

**Endpoint:** `/api/v1/flow/{flow}/export/document-embeddings`

**Method:** WebSocket connection

The export endpoint streams document embeddings data in real-time. Each message contains:

```json
{
    "metadata": {
        "id": "doc-123",
        "user": "alice",
        "collection": "research",
        "metadata": [
            {
                "s": {"v": "doc-123", "e": true},
                "p": {"v": "dc:title", "e": true},
                "o": {"v": "Research Paper", "e": false}
            }
        ]
    },
    "chunks": [
        {
            "chunk": "Decoded text content of chunk",
            "vectors": [[0.1, 0.2, 0.3, 0.4]]
        }
    ]
}
```

## Query Operations

### Query Document Embeddings

**Purpose:** Find documents similar to provided vector embeddings

**Request:**
```json
{
    "vectors": [
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.6, 0.7, 0.8, 0.9, 1.0]
    ],
    "limit": 10,
    "user": "alice",
    "collection": "research"
}
```

**Response:**
```json
{
    "documents": [
        "base64-encoded-document-1",
        "base64-encoded-document-2"
    ]
}
```

## WebSocket Usage Examples

### Importing Document Embeddings

```javascript
// Connect to import endpoint
const ws = new WebSocket('ws://api-gateway:8080/api/v1/flow/my-flow/import/document-embeddings');

// Send document embeddings
ws.send(JSON.stringify({
    metadata: {
        id: "doc-123",
        user: "alice",
        collection: "research"
    },
    chunks: [
        {
            chunk: "Document content chunk 1",
            vectors: [[0.1, 0.2, 0.3]]
        }
    ]
}));
```

### Exporting Document Embeddings

```javascript
// Connect to export endpoint
const ws = new WebSocket('ws://api-gateway:8080/api/v1/flow/my-flow/export/document-embeddings');

// Listen for exported data
ws.onmessage = (event) => {
    const documentEmbeddings = JSON.parse(event.data);
    console.log('Received document:', documentEmbeddings.metadata.id);
    console.log('Chunks:', documentEmbeddings.chunks.length);
};
```

## Data Format Details

### Metadata Format
Each metadata triple contains:
- `s`: Subject (object with `v` for value and `e` for is_entity boolean)
- `p`: Predicate (object with `v` for value and `e` for is_entity boolean)
- `o`: Object (object with `v` for value and `e` for is_entity boolean)

### Vector Format
- Vectors are arrays of floating-point numbers
- Each chunk can have multiple vectors (different embedding models)
- Vectors should be consistently dimensioned within a collection

### Text Encoding
- Chunk text is handled as UTF-8 encoded bytes internally
- WebSocket API accepts/returns plain text strings
- Base64 encoding used for binary data in query responses

## Python SDK

```python
from trustgraph.clients.document_embeddings_client import DocumentEmbeddingsClient

# Create client
client = DocumentEmbeddingsClient()

# Query similar documents
request = {
    "vectors": [[0.1, 0.2, 0.3, 0.4]],
    "limit": 5,
    "user": "alice",
    "collection": "research"
}

response = await client.query(request)
documents = response.documents
```

## Integration with TrustGraph

### Storage Integration
- Document embeddings are stored in vector databases
- Metadata is cross-referenced with knowledge graph
- Supports multi-tenant isolation by user and collection

### Processing Pipeline
1. **Document Ingestion**: Text documents loaded via text-load API
2. **Chunking**: Documents split into manageable chunks
3. **Embedding Generation**: Vector embeddings created for each chunk
4. **Storage**: Embeddings stored via import API
5. **Retrieval**: Similar documents found via query API

### Use Cases
- **Semantic Search**: Find documents similar to query embeddings
- **RAG Systems**: Retrieve relevant document chunks for question answering
- **Document Clustering**: Group similar documents using embeddings
- **Content Recommendations**: Suggest related documents to users
- **Knowledge Discovery**: Find connections between document collections

## Error Handling

Common error scenarios:
- Invalid vector dimensions
- Missing required metadata fields
- User/collection access restrictions
- WebSocket connection failures
- Malformed JSON data

Errors are returned in the response `error` field:
```json
{
    "error": {
        "type": "ValidationError",
        "message": "Invalid vector dimensions"
    }
}
```

## Performance Considerations

- **Batch Processing**: Import multiple documents in single WebSocket session
- **Vector Dimensions**: Consistent embedding dimensions improve performance
- **Collection Sizing**: Limit collections to reasonable sizes for query performance
- **Real-time vs Batch**: Choose appropriate method based on use case requirements