# TrustGraph Entity Contexts API

This API provides import and export capabilities for entity contexts data. Entity contexts 
associate entities with their textual context information, commonly used for entity 
descriptions, definitions, or explanatory text in knowledge graphs.

## Schema Overview

### EntityContext Structure
- `entity`: Entity identifier (Value object with value, is_uri, type)
- `context`: Textual context or description string

### EntityContexts Structure
- `metadata`: Metadata including ID, user, collection, and RDF triples
- `entities`: Array of EntityContext objects

### Value Structure
- `value`: The entity value as string
- `is_uri`: Boolean indicating if the value is a URI
- `type`: Data type of the value (optional)

## Import/Export Operations

### Import - WebSocket Endpoint

**Endpoint:** `/api/v1/flow/{flow}/import/entity-contexts`

**Method:** WebSocket connection

**Request Format:**
```json
{
    "metadata": {
        "id": "context-batch-123",
        "user": "alice",
        "collection": "research",
        "metadata": [
            {
                "s": {"value": "source-doc", "is_uri": true},
                "p": {"value": "dc:title", "is_uri": true},
                "o": {"value": "Research Paper", "is_uri": false}
            }
        ]
    },
    "entities": [
        {
            "entity": {
                "v": "https://example.com/Person/JohnDoe",
                "e": true
            },
            "context": "John Doe is a researcher at MIT specializing in artificial intelligence and machine learning."
        },
        {
            "entity": {
                "v": "https://example.com/Organization/MIT",
                "e": true
            },
            "context": "Massachusetts Institute of Technology (MIT) is a private research university in Cambridge, Massachusetts."
        },
        {
            "entity": {
                "v": "machine learning",
                "e": false
            },
            "context": "Machine learning is a method of data analysis that automates analytical model building using algorithms."
        }
    ]
}
```

**Response:** Import operations are fire-and-forget with no response payload.

### Export - WebSocket Endpoint

**Endpoint:** `/api/v1/flow/{flow}/export/entity-contexts`

**Method:** WebSocket connection

The export endpoint streams entity contexts data in real-time. Each message contains:

```json
{
    "metadata": {
        "id": "context-batch-123",
        "user": "alice",
        "collection": "research",
        "metadata": [
            {
                "s": {"value": "source-doc", "is_uri": true},
                "p": {"value": "dc:title", "is_uri": true},
                "o": {"value": "Research Paper", "is_uri": false}
            }
        ]
    },
    "entities": [
        {
            "entity": {
                "v": "https://example.com/Person/JohnDoe",
                "e": true
            },
            "context": "John Doe is a researcher at MIT specializing in artificial intelligence."
        }
    ]
}
```

## WebSocket Usage Examples

### Importing Entity Contexts

```javascript
// Connect to import endpoint
const ws = new WebSocket('ws://api-gateway:8080/api/v1/flow/my-flow/import/entity-contexts');

// Send entity contexts
ws.send(JSON.stringify({
    metadata: {
        id: "context-batch-1",
        user: "alice",
        collection: "research"
    },
    entities: [
        {
            entity: {
                v: "Albert Einstein",
                e: false
            },
            context: "Albert Einstein was a German-born theoretical physicist widely acknowledged to be one of the greatest physicists of all time."
        }
    ]
}));
```

### Exporting Entity Contexts

```javascript
// Connect to export endpoint
const ws = new WebSocket('ws://api-gateway:8080/api/v1/flow/my-flow/export/entity-contexts');

// Listen for exported data
ws.onmessage = (event) => {
    const entityContexts = JSON.parse(event.data);
    console.log('Received contexts for', entityContexts.entities.length, 'entities');
    
    entityContexts.entities.forEach(item => {
        console.log('Entity:', item.entity.v);
        console.log('Context:', item.context);
    });
};
```

## Data Format Details

### Entity Format
The `entity` field uses the Value structure:
- `v`: The entity value (name, URI, identifier)
- `e`: Boolean indicating if it's a URI entity (true) or literal (false)
- `type`: Optional data type specification

### Context Format
- Plain text string providing description or context
- Can include definitions, explanations, or background information
- Supports multi-sentence descriptions and detailed context

### Metadata Format
Each metadata triple contains:
- `s`: Subject (object with `value` and `is_uri` fields)
- `p`: Predicate (object with `value` and `is_uri` fields)
- `o`: Object (object with `value` and `is_uri` fields)

## Integration with TrustGraph

### Storage Integration
- Entity contexts are stored in graph databases
- Links entities to their descriptive text
- Supports multi-tenant isolation by user and collection

### Processing Pipeline
1. **Text Analysis**: Extract entities from documents
2. **Context Extraction**: Identify descriptive text for entities
3. **Entity Linking**: Associate entities with their contexts
4. **Import**: Store entity-context pairs via import API
5. **Knowledge Enhancement**: Use contexts for better entity understanding

### Use Cases
- **Entity Disambiguation**: Provide context to distinguish similar entities
- **Knowledge Base Enhancement**: Add descriptive information to entities
- **Question Answering**: Use entity contexts to provide detailed answers
- **Entity Summarization**: Generate summaries based on collected contexts
- **Knowledge Graph Visualization**: Display rich entity information

## Authentication

Both import and export endpoints support authentication:
- API token authentication via Authorization header
- Flow-based access control
- User and collection isolation

## Error Handling

Common error scenarios:
- Invalid JSON format
- Missing required metadata fields
- User/collection access restrictions
- WebSocket connection failures
- Invalid entity value formats

Errors are typically handled at the WebSocket connection level with connection termination or error messages.

## Performance Considerations

- **Batch Processing**: Import multiple entity contexts in single messages
- **Context Length**: Balance detailed context with performance
- **Flow Capacity**: Ensure target flow can handle entity context volume
- **Real-time vs Batch**: Choose appropriate method based on use case

## Python Integration

While no direct Python SDK is mentioned in the codebase, integration can be achieved through:

```python
import websocket
import json

# Connect to import endpoint
def import_entity_contexts(flow_id, contexts_data):
    ws_url = f"ws://api-gateway:8080/api/v1/flow/{flow_id}/import/entity-contexts"
    ws = websocket.create_connection(ws_url)
    
    # Send data
    ws.send(json.dumps(contexts_data))
    ws.close()

# Usage example
contexts = {
    "metadata": {
        "id": "batch-1",
        "user": "alice",
        "collection": "research"
    },
    "entities": [
        {
            "entity": {"v": "Neural Networks", "e": False},
            "context": "Neural networks are computing systems inspired by biological neural networks."
        }
    ]
}

import_entity_contexts("my-flow", contexts)
```

## Features

- **Real-time Streaming**: WebSocket-based import/export for live data flow
- **Batch Operations**: Process multiple entity contexts efficiently
- **Rich Metadata**: Full metadata support with RDF triples
- **Entity Types**: Support for both URI entities and literal values
- **Flow Integration**: Direct integration with TrustGraph processing flows
- **Multi-tenant Support**: User and collection-based data isolation