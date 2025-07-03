# TrustGraph Knowledge API

This API provides knowledge graph management for TrustGraph. It handles storage, retrieval, 
and flow integration of knowledge cores containing RDF triples and graph embeddings with 
multi-tenant support.

## Request/response

### Request

The request contains the following fields:
- `operation`: The operation to perform (see operations below)
- `user`: User identifier (for user-specific operations)
- `id`: Knowledge core identifier
- `flow`: Flow identifier (for load operations)
- `collection`: Collection identifier (for load operations)
- `triples`: RDF triples data (for put operations)
- `graph_embeddings`: Graph embeddings data (for put operations)

### Response

The response contains the following fields:
- `error`: Error information if operation fails
- `ids`: Array of knowledge core IDs (returned by list operation)
- `eos`: End of stream indicator for streaming responses
- `triples`: RDF triples data (returned by get operation)
- `graph_embeddings`: Graph embeddings data (returned by get operation)

## Operations

### PUT-KG-CORE - Store Knowledge Core

Request:
```json
{
    "operation": "put-kg-core",
    "user": "alice",
    "id": "core-123",
    "triples": {
        "metadata": {
            "id": "core-123",
            "user": "alice",
            "collection": "research"
        },
        "triples": [
            {
                "s": {"value": "Person1", "is_uri": true},
                "p": {"value": "hasName", "is_uri": true},
                "o": {"value": "John Doe", "is_uri": false}
            },
            {
                "s": {"value": "Person1", "is_uri": true},
                "p": {"value": "worksAt", "is_uri": true},
                "o": {"value": "Company1", "is_uri": true}
            }
        ]
    },
    "graph_embeddings": {
        "metadata": {
            "id": "core-123",
            "user": "alice",
            "collection": "research"
        },
        "entities": [
            {
                "entity": {"value": "Person1", "is_uri": true},
                "vectors": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            }
        ]
    }
}
```

Response:
```json
{}
```

### GET-KG-CORE - Retrieve Knowledge Core

Request:
```json
{
    "operation": "get-kg-core",
    "id": "core-123"
}
```

Response:
```json
{
    "triples": {
        "metadata": {
            "id": "core-123",
            "user": "alice",
            "collection": "research"
        },
        "triples": [
            {
                "s": {"value": "Person1", "is_uri": true},
                "p": {"value": "hasName", "is_uri": true},
                "o": {"value": "John Doe", "is_uri": false}
            }
        ]
    },
    "graph_embeddings": {
        "metadata": {
            "id": "core-123",
            "user": "alice",
            "collection": "research"
        },
        "entities": [
            {
                "entity": {"value": "Person1", "is_uri": true},
                "vectors": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            }
        ]
    }
}
```

### LIST-KG-CORES - List Knowledge Cores

Request:
```json
{
    "operation": "list-kg-cores",
    "user": "alice"
}
```

Response:
```json
{
    "ids": ["core-123", "core-456", "core-789"]
}
```

### DELETE-KG-CORE - Delete Knowledge Core

Request:
```json
{
    "operation": "delete-kg-core",
    "user": "alice",
    "id": "core-123"
}
```

Response:
```json
{}
```

### LOAD-KG-CORE - Load Knowledge Core into Flow

Request:
```json
{
    "operation": "load-kg-core",
    "id": "core-123",
    "flow": "qa-flow",
    "collection": "research"
}
```

Response:
```json
{}
```

### UNLOAD-KG-CORE - Unload Knowledge Core from Flow

Request:
```json
{
    "operation": "unload-kg-core",
    "id": "core-123"
}
```

Response:
```json
{}
```

## Data Structures

### Triple Structure
Each RDF triple contains:
- `s`: Subject (Value object)
- `p`: Predicate (Value object)
- `o`: Object (Value object)

### Value Structure
- `value`: The actual value as string
- `is_uri`: Boolean indicating if value is a URI
- `type`: Data type of the value (optional)

### Triples Structure
- `metadata`: Metadata including ID, user, collection
- `triples`: Array of Triple objects

### Graph Embeddings Structure
- `metadata`: Metadata including ID, user, collection
- `entities`: Array of EntityEmbeddings objects

### Entity Embeddings Structure
- `entity`: The entity being embedded (Value object)
- `vectors`: Array of vector embeddings (Array of Array of Double)

## REST service

The REST service is available at `/api/v1/knowledge` and accepts the above request formats.

## Websocket

Requests have a `request` object containing the operation fields.
Responses have a `response` object containing the response fields.

Request:
```json
{
    "id": "unique-request-id",
    "service": "knowledge",
    "request": {
        "operation": "list-kg-cores",
        "user": "alice"
    }
}
```

Response:
```json
{
    "id": "unique-request-id",
    "response": {
        "ids": ["core-123", "core-456"]
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Knowledge API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/knowledge.py

Default request queue:
`non-persistent://tg/request/knowledge`

Default response queue:
`non-persistent://tg/response/knowledge`

Request schema:
`trustgraph.schema.KnowledgeRequest`

Response schema:
`trustgraph.schema.KnowledgeResponse`

## Python SDK

The Python SDK provides convenient access to the Knowledge API:

```python
from trustgraph.api.knowledge import KnowledgeClient

client = KnowledgeClient()

# List knowledge cores
cores = await client.list_kg_cores("alice")

# Get a knowledge core
core = await client.get_kg_core("core-123")

# Store a knowledge core
await client.put_kg_core(
    user="alice",
    id="core-123",
    triples=triples_data,
    graph_embeddings=embeddings_data
)

# Load core into flow
await client.load_kg_core("core-123", "qa-flow", "research")

# Delete a knowledge core
await client.delete_kg_core("alice", "core-123")
```

## Features

- **Knowledge Core Management**: Store, retrieve, list, and delete knowledge cores
- **Dual Data Types**: Support for both RDF triples and graph embeddings
- **Flow Integration**: Load knowledge cores into processing flows
- **Multi-tenant Support**: User-specific knowledge cores with isolation
- **Streaming Support**: Efficient transfer of large knowledge cores
- **Collection Organization**: Group knowledge cores by collection
- **Semantic Reasoning**: RDF triples enable symbolic reasoning
- **Vector Similarity**: Graph embeddings enable neural approaches

## Use Cases

- **Knowledge Base Construction**: Build semantic knowledge graphs from documents
- **Question Answering**: Load knowledge cores for graph-based QA systems
- **Semantic Search**: Use embeddings for similarity-based knowledge retrieval
- **Multi-domain Knowledge**: Organize knowledge by user and collection
- **Hybrid Reasoning**: Combine symbolic (triples) and neural (embeddings) approaches
- **Knowledge Transfer**: Export and import knowledge cores between systems