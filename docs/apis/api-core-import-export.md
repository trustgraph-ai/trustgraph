# TrustGraph Core Import/Export API

This API provides bulk import and export capabilities for TrustGraph knowledge cores. 
It handles efficient transfer of both RDF triples and graph embeddings using MessagePack 
binary format for high-performance data exchange.

## Overview

The Core Import/Export API enables:
- **Bulk Import**: Import large knowledge cores from binary streams
- **Bulk Export**: Export knowledge cores as binary streams  
- **Efficient Format**: Uses MessagePack for compact, fast serialization
- **Dual Data Types**: Handles both RDF triples and graph embeddings
- **Streaming**: Supports streaming for large datasets

## Import Endpoint

**Endpoint:** `POST /api/v1/import-core`

**Query Parameters:**
- `id`: Knowledge core identifier
- `user`: User identifier

**Content-Type:** `application/octet-stream`

**Request Body:** MessagePack-encoded binary stream

### Import Process

1. **Stream Processing**: Reads binary data in 128KB chunks
2. **MessagePack Decoding**: Unpacks binary data into structured messages
3. **Knowledge Storage**: Stores data via Knowledge API
4. **Response**: Returns success/error status

### Import Data Format

The import stream contains MessagePack-encoded tuples with type indicators:

#### Triples Data
```python
("t", {
    "m": {  # metadata
        "i": "core-id",
        "m": [],  # metadata triples
        "u": "user",
        "c": "collection"
    },
    "t": [  # triples array
        {
            "s": {"value": "subject", "is_uri": true},
            "p": {"value": "predicate", "is_uri": true}, 
            "o": {"value": "object", "is_uri": false}
        }
    ]
})
```

#### Graph Embeddings Data
```python
("ge", {
    "m": {  # metadata
        "i": "core-id",
        "m": [],  # metadata triples
        "u": "user", 
        "c": "collection"
    },
    "e": [  # entities array
        {
            "e": {"value": "entity", "is_uri": true},
            "v": [[0.1, 0.2, 0.3]]  # vectors
        }
    ]
})
```

## Export Endpoint

**Endpoint:** `GET /api/v1/export-core`

**Query Parameters:**
- `id`: Knowledge core identifier  
- `user`: User identifier

**Content-Type:** `application/octet-stream`

**Response Body:** MessagePack-encoded binary stream

### Export Process

1. **Knowledge Retrieval**: Fetches data via Knowledge API
2. **MessagePack Encoding**: Encodes data into binary format
3. **Streaming Response**: Sends data as binary stream
4. **Type Identification**: Uses type prefixes for data classification

## Usage Examples

### Import Knowledge Core

```bash
# Import from file
curl -X POST \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @knowledge-core.msgpack \
  "http://api-gateway:8080/api/v1/import-core?id=core-123&user=alice"
```

### Export Knowledge Core

```bash
# Export to file
curl -H "Authorization: Bearer your-token" \
  "http://api-gateway:8080/api/v1/export-core?id=core-123&user=alice" \
  -o knowledge-core.msgpack
```

## Python Integration

### Import Example

```python
import msgpack
import requests

def import_knowledge_core(core_id, user, triples_data, embeddings_data, token):
    # Prepare data
    messages = []
    
    # Add triples
    if triples_data:
        messages.append(("t", {
            "m": {
                "i": core_id,
                "m": [],
                "u": user,
                "c": "default"
            },
            "t": triples_data
        }))
    
    # Add embeddings
    if embeddings_data:
        messages.append(("ge", {
            "m": {
                "i": core_id,
                "m": [],
                "u": user,
                "c": "default"
            },
            "e": embeddings_data
        }))
    
    # Pack data
    binary_data = b''.join(msgpack.packb(msg) for msg in messages)
    
    # Upload
    response = requests.post(
        f"http://api-gateway:8080/api/v1/import-core?id={core_id}&user={user}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream"
        },
        data=binary_data
    )
    
    return response.status_code == 200

# Usage
triples = [
    {
        "s": {"value": "Person1", "is_uri": True},
        "p": {"value": "hasName", "is_uri": True},
        "o": {"value": "John Doe", "is_uri": False}
    }
]

embeddings = [
    {
        "e": {"value": "Person1", "is_uri": True},
        "v": [[0.1, 0.2, 0.3, 0.4]]
    }
]

success = import_knowledge_core("core-123", "alice", triples, embeddings, "your-token")
```

### Export Example

```python
import msgpack
import requests

def export_knowledge_core(core_id, user, token):
    response = requests.get(
        f"http://api-gateway:8080/api/v1/export-core?id={core_id}&user={user}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        return None
    
    # Decode MessagePack stream
    data = response.content
    unpacker = msgpack.Unpacker()
    unpacker.feed(data)
    
    triples = []
    embeddings = []
    
    for unpacked in unpacker:
        msg_type, msg_data = unpacked
        
        if msg_type == "t":
            triples.extend(msg_data["t"])
        elif msg_type == "ge":
            embeddings.extend(msg_data["e"])
    
    return {
        "triples": triples,
        "embeddings": embeddings
    }

# Usage
data = export_knowledge_core("core-123", "alice", "your-token")
if data:
    print(f"Exported {len(data['triples'])} triples")
    print(f"Exported {len(data['embeddings'])} embeddings")
```

## Data Format Specification

### MessagePack Tuples

Each message is a tuple: `(type_indicator, data_object)`

**Type Indicators:**
- `"t"`: RDF triples data
- `"ge"`: Graph embeddings data

### Metadata Structure

```python
{
    "i": "core-identifier",     # ID
    "m": [...],                 # Metadata triples array
    "u": "user-identifier",     # User
    "c": "collection-name"      # Collection
}
```

### Triple Structure

```python
{
    "s": {"value": "subject", "is_uri": boolean},
    "p": {"value": "predicate", "is_uri": boolean},
    "o": {"value": "object", "is_uri": boolean}
}
```

### Entity Embedding Structure

```python
{
    "e": {"value": "entity", "is_uri": boolean},
    "v": [[float, float, ...]]  # Array of vectors
}
```

## Performance Characteristics

### Import Performance
- **Streaming**: Processes data in 128KB chunks
- **Memory Efficient**: Incremental unpacking
- **Concurrent**: Multiple imports can run simultaneously
- **Error Handling**: Robust error recovery

### Export Performance  
- **Direct Streaming**: Data streamed directly from knowledge store
- **Efficient Encoding**: MessagePack for minimal overhead
- **Large Dataset Support**: Handles cores of any size

## Error Handling

### Import Errors
- **Format Errors**: Invalid MessagePack data
- **Type Errors**: Unknown type indicators
- **Storage Errors**: Knowledge API failures
- **Authentication**: Invalid user credentials

### Export Errors
- **Not Found**: Core ID doesn't exist
- **Access Denied**: User lacks permissions
- **System Errors**: Knowledge API failures

### Error Responses
- **HTTP 400**: Bad request (invalid parameters)
- **HTTP 401**: Unauthorized access
- **HTTP 404**: Core not found
- **HTTP 500**: Internal server error

## Use Cases

### Data Migration
- **System Upgrades**: Export/import during system migrations
- **Environment Sync**: Copy cores between environments
- **Backup/Restore**: Full knowledge core backup operations

### Batch Processing
- **Bulk Loading**: Load large knowledge datasets efficiently
- **Data Integration**: Merge knowledge from multiple sources
- **ETL Pipelines**: Extract-Transform-Load operations

### Performance Optimization
- **Faster Than REST**: Binary format reduces transfer time
- **Atomic Operations**: Complete import/export as single operation
- **Resource Efficient**: Minimal memory footprint during transfer

## Security Considerations

- **Authentication Required**: Bearer token authentication
- **User Isolation**: Access restricted to user's own cores
- **Data Validation**: Input validation on import
- **Audit Logging**: Operations logged for security auditing