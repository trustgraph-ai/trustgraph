# tg-put-kg-core

Stores a knowledge core in the TrustGraph system from MessagePack format.

## Synopsis

```bash
tg-put-kg-core --id CORE_ID -i INPUT_FILE [options]
```

## Description

The `tg-put-kg-core` command loads a knowledge core from a MessagePack-formatted file and stores it in the TrustGraph knowledge system. Knowledge cores contain RDF triples and graph embeddings that represent structured knowledge and can be loaded into flows for processing.

This command processes MessagePack files containing both triples (RDF knowledge) and graph embeddings (vector representations) and stores them via WebSocket connection to the Knowledge API.

## Options

### Required Arguments

- `--id, --identifier CORE_ID`: Unique identifier for the knowledge core
- `-i, --input INPUT_FILE`: Path to MessagePack input file

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `ws://localhost:8088/`)
- `-U, --user USER`: User identifier (default: `trustgraph`)

## Examples

### Store Knowledge Core
```bash
tg-put-kg-core --id "research-core-v1" -i knowledge.msgpack
```

### With Custom User
```bash
tg-put-kg-core \
  --id "medical-knowledge" \
  -i medical-data.msgpack \
  -U researcher
```

### Using Custom API URL
```bash
tg-put-kg-core \
  --id "production-core" \
  -i prod-knowledge.msgpack \
  -u ws://production:8088/
```

## Input File Format

The input file must be in MessagePack format containing structured knowledge data:

### MessagePack Structure
The file contains tuples with type indicators:

#### Triple Data (`"t"`)
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

#### Graph Embeddings Data (`"ge"`)
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

## Processing Flow

1. **File Reading**: Opens MessagePack file for binary reading
2. **Message Unpacking**: Unpacks MessagePack tuples sequentially
3. **Type Processing**: Handles both triples (`"t"`) and graph embeddings (`"ge"`)
4. **WebSocket Transmission**: Sends each message via WebSocket to Knowledge API
5. **Response Handling**: Waits for confirmation of each message
6. **Progress Reporting**: Shows count of processed messages

## Output

The command reports the number of messages processed:

```bash
Put: 150 triple, 75 GE messages.
```

Where:
- **triple**: Number of triple data messages processed
- **GE**: Number of graph embedding messages processed

## Error Handling

### File Not Found
```bash
Exception: No such file or directory: 'missing.msgpack'
```
**Solution**: Verify the input file path exists and is readable.

### Invalid MessagePack Format
```bash
Exception: Unpacked unexpected message type 'x'
```
**Solution**: Ensure the input file is properly formatted MessagePack with correct type indicators.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Verify the API URL and ensure TrustGraph is running.

### Knowledge API Errors
```bash
Exception: Knowledge core operation failed
```
**Solution**: Check that the Knowledge API is available and the core ID is valid.

## File Creation

MessagePack files can be created using:

### Python Example
```python
import msgpack

# Create triples data
triples_msg = ("t", {
    "m": {"i": "core-id", "m": [], "u": "user", "c": "default"},
    "t": [
        {
            "s": {"value": "Person1", "is_uri": True},
            "p": {"value": "hasName", "is_uri": True},
            "o": {"value": "John Doe", "is_uri": False}
        }
    ]
})

# Create embeddings data
embeddings_msg = ("ge", {
    "m": {"i": "core-id", "m": [], "u": "user", "c": "default"},
    "e": [
        {
            "e": {"value": "Person1", "is_uri": True},
            "v": [[0.1, 0.2, 0.3, 0.4]]
        }
    ]
})

# Write to file
with open("knowledge.msgpack", "wb") as f:
    msgpack.pack(triples_msg, f)
    msgpack.pack(embeddings_msg, f)
```

### Export from Existing Core
```bash
# Export existing core to MessagePack
tg-get-kg-core --id "existing-core" -o exported.msgpack

# Import to new core
tg-put-kg-core --id "new-core" -i exported.msgpack
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL (automatically converted to WebSocket format)

## Related Commands

- [`tg-get-kg-core`](tg-get-kg-core.md) - Retrieve knowledge core
- [`tg-load-kg-core`](tg-load-kg-core.md) - Load knowledge core into flow
- [`tg-show-kg-cores`](tg-show-kg-cores.md) - List available knowledge cores
- [`tg-delete-kg-core`](tg-delete-kg-core.md) - Remove knowledge core
- [`tg-dump-msgpack`](tg-dump-msgpack.md) - Debug MessagePack files

## API Integration

This command uses the [Knowledge API](../apis/api-knowledge.md) via WebSocket connection with `put-kg-core` operations to store knowledge data.

## Use Cases

### Knowledge Import
```bash
# Import knowledge from external systems
tg-put-kg-core --id "external-kb" -i imported-knowledge.msgpack
```

### Data Migration
```bash
# Migrate knowledge between environments
tg-get-kg-core --id "prod-core" -o backup.msgpack
tg-put-kg-core --id "dev-core" -i backup.msgpack
```

### Knowledge Versioning
```bash
# Store versioned knowledge cores
tg-put-kg-core --id "research-v2.0" -i research-updated.msgpack
```

### Batch Knowledge Loading
```bash
# Load multiple knowledge domains
tg-put-kg-core --id "medical-core" -i medical.msgpack
tg-put-kg-core --id "legal-core" -i legal.msgpack
tg-put-kg-core --id "technical-core" -i technical.msgpack
```

## Best Practices

1. **Unique IDs**: Use descriptive, unique identifiers for knowledge cores
2. **Versioning**: Include version information in core IDs
3. **Validation**: Verify MessagePack files before importing
4. **Backup**: Keep backup copies of important knowledge cores
5. **Documentation**: Document knowledge core contents and sources
6. **Testing**: Test imports with small datasets first