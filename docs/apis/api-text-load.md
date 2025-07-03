# TrustGraph Text Load API

This API loads text documents into TrustGraph processing pipelines. It's a sender API 
that accepts text documents with metadata and queues them for processing through 
specified flows.

## Request Format

The text-load API accepts a JSON request with the following fields:
- `id`: Document identifier (typically a URI)
- `metadata`: Array of RDF triples providing document metadata
- `charset`: Character encoding (defaults to "utf-8")
- `text`: Base64-encoded text content
- `user`: User identifier (defaults to "trustgraph")
- `collection`: Collection identifier (defaults to "default")

## Request Example

```json
{
    "id": "https://example.com/documents/research-paper-123",
    "metadata": [
        {
            "s": {"v": "https://example.com/documents/research-paper-123", "e": true},
            "p": {"v": "http://purl.org/dc/terms/title", "e": true},
            "o": {"v": "Machine Learning in Healthcare", "e": false}
        },
        {
            "s": {"v": "https://example.com/documents/research-paper-123", "e": true},
            "p": {"v": "http://purl.org/dc/terms/creator", "e": true},
            "o": {"v": "Dr. Jane Smith", "e": false}
        },
        {
            "s": {"v": "https://example.com/documents/research-paper-123", "e": true},
            "p": {"v": "http://purl.org/dc/terms/subject", "e": true},
            "o": {"v": "Healthcare AI", "e": false}
        }
    ],
    "charset": "utf-8",
    "text": "VGhpcyBpcyBhIHNhbXBsZSByZXNlYXJjaCBwYXBlciBhYm91dCBtYWNoaW5lIGxlYXJuaW5nIGluIGhlYWx0aGNhcmUuLi4=",
    "user": "researcher",
    "collection": "healthcare-research"
}
```

## Response

The text-load API is a sender API with no response body. Success is indicated by HTTP status code 200.

## REST service

The text-load service is available at:
`POST /api/v1/flow/{flow-id}/service/text-load`

Where `{flow-id}` is the identifier of the flow that will process the document.

Example:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d @document.json \
  http://api-gateway:8080/api/v1/flow/pdf-processing/service/text-load
```

## Metadata Format

Each metadata triple contains:
- `s`: Subject (object with `v` for value and `e` for is_entity boolean)
- `p`: Predicate (object with `v` for value and `e` for is_entity boolean)
- `o`: Object (object with `v` for value and `e` for is_entity boolean)

The `e` field indicates whether the value should be treated as an entity (true) or literal (false).

## Common Metadata Properties

### Document Properties
- `http://purl.org/dc/terms/title`: Document title
- `http://purl.org/dc/terms/creator`: Document author
- `http://purl.org/dc/terms/subject`: Document subject/topic
- `http://purl.org/dc/terms/description`: Document description
- `http://purl.org/dc/terms/date`: Publication date
- `http://purl.org/dc/terms/language`: Document language

### Organizational Properties
- `http://xmlns.com/foaf/0.1/name`: Organization name
- `http://www.w3.org/2006/vcard/ns#hasAddress`: Organization address
- `http://xmlns.com/foaf/0.1/homepage`: Organization website

### Publication Properties
- `http://purl.org/ontology/bibo/doi`: DOI identifier
- `http://purl.org/ontology/bibo/isbn`: ISBN identifier
- `http://purl.org/ontology/bibo/volume`: Publication volume
- `http://purl.org/ontology/bibo/issue`: Publication issue

## Text Encoding

The `text` field must contain base64-encoded content. To encode text:

```bash
# Command line encoding
echo "Your text content here" | base64

# Python encoding
import base64
encoded_text = base64.b64encode("Your text content here".encode('utf-8')).decode('utf-8')
```

## Integration with Processing Flows

Once loaded, text documents are processed through the specified flow, which typically includes:

1. **Text Chunking**: Breaking documents into manageable chunks
2. **Embedding Generation**: Creating vector embeddings for semantic search
3. **Knowledge Extraction**: Extracting entities and relationships
4. **Graph Storage**: Storing extracted knowledge in the knowledge graph
5. **Indexing**: Making content searchable for RAG queries

## Error Handling

Common errors include:
- Invalid base64 encoding in text field
- Missing required fields (id, text)
- Invalid metadata triple format
- Flow not found or inactive

## Python SDK

```python
import base64
from trustgraph.api.text_load import TextLoadClient

client = TextLoadClient()

# Prepare document
document = {
    "id": "https://example.com/doc-123",
    "metadata": [
        {
            "s": {"v": "https://example.com/doc-123", "e": True},
            "p": {"v": "http://purl.org/dc/terms/title", "e": True},
            "o": {"v": "Sample Document", "e": False}
        }
    ],
    "charset": "utf-8",
    "text": base64.b64encode("Document content here".encode('utf-8')).decode('utf-8'),
    "user": "alice",
    "collection": "research"
}

# Load document
await client.load_text_document("my-flow", document)
```

## Use Cases

- **Research Paper Ingestion**: Load academic papers with rich metadata
- **Document Processing**: Ingest documents for knowledge extraction
- **Content Management**: Build searchable document repositories
- **RAG System Population**: Load content for question-answering systems
- **Knowledge Base Construction**: Convert documents into structured knowledge

## Features

- **Rich Metadata**: Full RDF metadata support for semantic annotation
- **Flow Integration**: Direct integration with TrustGraph processing flows
- **Multi-tenant**: User and collection-based document organization
- **Encoding Support**: Flexible character encoding support
- **No Response Required**: Fire-and-forget operation for high throughput