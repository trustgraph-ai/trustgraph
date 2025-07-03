# tg-put-flow-class

Uploads or updates a flow class definition in TrustGraph.

## Synopsis

```bash
tg-put-flow-class -n CLASS_NAME -c CONFIG_JSON [options]
```

## Description

The `tg-put-flow-class` command creates or updates a flow class definition in TrustGraph. Flow classes are templates that define processing pipeline configurations, service interfaces, and resource requirements. These classes are used by `tg-start-flow` to create running flow instances.

Flow classes define the structure and capabilities of processing flows, including which services are available and how they connect to Pulsar queues.

## Options

### Required Arguments

- `-n, --class-name CLASS_NAME`: Name for the flow class
- `-c, --config CONFIG_JSON`: Flow class configuration as raw JSON string

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Basic Flow Class Creation
```bash
tg-put-flow-class \
  -n "simple-processing" \
  -c '{"description": "Simple text processing flow", "interfaces": {"text-completion": {"request": "non-persistent://tg/request/text-completion:simple", "response": "non-persistent://tg/response/text-completion:simple"}}}'
```

### Document Processing Flow Class
```bash
tg-put-flow-class \
  -n "document-analysis" \
  -c '{
    "description": "Document analysis and RAG processing",
    "interfaces": {
      "document-rag": {
        "request": "non-persistent://tg/request/document-rag:doc-analysis",
        "response": "non-persistent://tg/response/document-rag:doc-analysis"
      },
      "text-load": "persistent://tg/flow/text-document-load:doc-analysis",
      "document-load": "persistent://tg/flow/document-load:doc-analysis"
    }
  }'
```

### Loading from File
```bash
# Create configuration file
cat > research-flow.json << 'EOF'
{
  "description": "Research analysis flow with multiple AI services",
  "interfaces": {
    "agent": {
      "request": "non-persistent://tg/request/agent:research",
      "response": "non-persistent://tg/response/agent:research"
    },
    "graph-rag": {
      "request": "non-persistent://tg/request/graph-rag:research",
      "response": "non-persistent://tg/response/graph-rag:research"
    },
    "document-rag": {
      "request": "non-persistent://tg/request/document-rag:research",
      "response": "non-persistent://tg/response/document-rag:research"
    },
    "embeddings": {
      "request": "non-persistent://tg/request/embeddings:research",
      "response": "non-persistent://tg/response/embeddings:research"
    },
    "text-load": "persistent://tg/flow/text-document-load:research",
    "triples-store": "persistent://tg/flow/triples-store:research"
  }
}
EOF

# Upload the flow class
tg-put-flow-class -n "research-analysis" -c "$(cat research-flow.json)"
```

### Update Existing Flow Class
```bash
# Modify existing flow class by adding new service
tg-put-flow-class \
  -n "existing-flow" \
  -c '{
    "description": "Updated flow with new capabilities",
    "interfaces": {
      "text-completion": {
        "request": "non-persistent://tg/request/text-completion:updated",
        "response": "non-persistent://tg/response/text-completion:updated"
      },
      "prompt": {
        "request": "non-persistent://tg/request/prompt:updated",
        "response": "non-persistent://tg/response/prompt:updated"
      }
    }
  }'
```

## Flow Class Configuration Format

### Required Fields

#### Description
```json
{
  "description": "Human-readable description of the flow class"
}
```

#### Interfaces
```json
{
  "interfaces": {
    "service-name": "queue-definition-or-object"
  }
}
```

### Interface Types

#### Request/Response Services
Services that accept requests and return responses:

```json
{
  "service-name": {
    "request": "pulsar-queue-url",
    "response": "pulsar-queue-url"
  }
}
```

Examples:
- `agent`
- `graph-rag`
- `document-rag`
- `text-completion`
- `prompt`
- `embeddings`
- `graph-embeddings`
- `triples`

#### Fire-and-Forget Services
Services that accept data without returning responses:

```json
{
  "service-name": "pulsar-queue-url"
}
```

Examples:
- `text-load`
- `document-load`
- `triples-store`
- `graph-embeddings-store`
- `document-embeddings-store`
- `entity-contexts-load`

### Queue Naming Conventions

#### Request/Response Queues
```
non-persistent://tg/request/{service}:{flow-identifier}
non-persistent://tg/response/{service}:{flow-identifier}
```

#### Fire-and-Forget Queues
```
persistent://tg/flow/{service}:{flow-identifier}
```

## Complete Example

### Comprehensive Flow Class
```bash
tg-put-flow-class \
  -n "full-processing-pipeline" \
  -c '{
    "description": "Complete document processing and analysis pipeline",
    "interfaces": {
      "agent": {
        "request": "non-persistent://tg/request/agent:full-pipeline",
        "response": "non-persistent://tg/response/agent:full-pipeline"
      },
      "graph-rag": {
        "request": "non-persistent://tg/request/graph-rag:full-pipeline",
        "response": "non-persistent://tg/response/graph-rag:full-pipeline"
      },
      "document-rag": {
        "request": "non-persistent://tg/request/document-rag:full-pipeline",
        "response": "non-persistent://tg/response/document-rag:full-pipeline"
      },
      "text-completion": {
        "request": "non-persistent://tg/request/text-completion:full-pipeline",
        "response": "non-persistent://tg/response/text-completion:full-pipeline"
      },
      "prompt": {
        "request": "non-persistent://tg/request/prompt:full-pipeline",
        "response": "non-persistent://tg/response/prompt:full-pipeline"
      },
      "embeddings": {
        "request": "non-persistent://tg/request/embeddings:full-pipeline",
        "response": "non-persistent://tg/response/embeddings:full-pipeline"
      },
      "graph-embeddings": {
        "request": "non-persistent://tg/request/graph-embeddings:full-pipeline",
        "response": "non-persistent://tg/response/graph-embeddings:full-pipeline"
      },
      "triples": {
        "request": "non-persistent://tg/request/triples:full-pipeline",
        "response": "non-persistent://tg/response/triples:full-pipeline"
      },
      "text-load": "persistent://tg/flow/text-document-load:full-pipeline",
      "document-load": "persistent://tg/flow/document-load:full-pipeline",
      "triples-store": "persistent://tg/flow/triples-store:full-pipeline",
      "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:full-pipeline",
      "document-embeddings-store": "persistent://tg/flow/document-embeddings-store:full-pipeline",
      "entity-contexts-load": "persistent://tg/flow/entity-contexts-load:full-pipeline"
    }
  }'
```

## Output

Successful upload typically produces no output:

```bash
# Upload flow class (no output expected)
tg-put-flow-class -n "my-flow" -c '{"description": "test", "interfaces": {}}'

# Verify upload
tg-show-flow-classes | grep "my-flow"
```

## Error Handling

### Invalid JSON Format
```bash
Exception: Invalid JSON in config parameter
```
**Solution**: Validate JSON syntax using tools like `jq` or online JSON validators.

### Missing Required Fields
```bash
Exception: Missing required field 'description'
```
**Solution**: Ensure configuration includes all required fields (description, interfaces).

### Invalid Queue Names
```bash
Exception: Invalid queue URL format
```
**Solution**: Verify queue URLs follow the correct Pulsar format with proper tenant/namespace.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

## Validation

### JSON Syntax Check
```bash
# Validate JSON before uploading
config='{"description": "test flow", "interfaces": {}}'
echo "$config" | jq . > /dev/null && echo "Valid JSON" || echo "Invalid JSON"
```

### Flow Class Verification
```bash
# After uploading, verify the flow class exists
tg-show-flow-classes | grep "my-flow-class"

# Get the flow class definition to verify content
tg-get-flow-class -n "my-flow-class"
```

## Flow Class Lifecycle

### Development Workflow
```bash
# 1. Create flow class
tg-put-flow-class -n "dev-flow" -c "$dev_config"

# 2. Test with flow instance
tg-start-flow -n "dev-flow" -i "test-instance" -d "Testing"

# 3. Update flow class as needed
tg-put-flow-class -n "dev-flow" -c "$updated_config"

# 4. Restart flow instance with updates
tg-stop-flow -i "test-instance"
tg-start-flow -n "dev-flow" -i "test-instance" -d "Testing updated"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-get-flow-class`](tg-get-flow-class.md) - Retrieve flow class definitions
- [`tg-show-flow-classes`](tg-show-flow-classes.md) - List available flow classes
- [`tg-delete-flow-class`](tg-delete-flow-class.md) - Remove flow class definitions
- [`tg-start-flow`](tg-start-flow.md) - Create flow instances from classes

## API Integration

This command uses the [Flow API](../apis/api-flow.md) with the `put-class` operation to store flow class definitions.

## Use Cases

### Custom Processing Pipelines
```bash
# Create specialized medical analysis flow
tg-put-flow-class -n "medical-nlp" -c "$medical_config"
```

### Development Environments
```bash
# Create lightweight development flow
tg-put-flow-class -n "dev-minimal" -c "$minimal_config"
```

### Production Deployments
```bash
# Create robust production flow with all services
tg-put-flow-class -n "production-full" -c "$production_config"
```

### Domain-Specific Workflows
```bash
# Create legal document analysis flow
tg-put-flow-class -n "legal-analysis" -c "$legal_config"
```

## Best Practices

1. **Descriptive Names**: Use clear, descriptive flow class names
2. **Comprehensive Descriptions**: Include detailed descriptions of flow capabilities
3. **Consistent Naming**: Follow consistent queue naming conventions
4. **Version Control**: Store flow class configurations in version control
5. **Testing**: Test flow classes thoroughly before production use
6. **Documentation**: Document flow class purposes and requirements

## Template Examples

### Minimal Flow Class
```json
{
  "description": "Minimal text processing flow",
  "interfaces": {
    "text-completion": {
      "request": "non-persistent://tg/request/text-completion:minimal",
      "response": "non-persistent://tg/response/text-completion:minimal"
    }
  }
}
```

### RAG-Focused Flow Class
```json
{
  "description": "Retrieval Augmented Generation flow",
  "interfaces": {
    "graph-rag": {
      "request": "non-persistent://tg/request/graph-rag:rag-flow",
      "response": "non-persistent://tg/response/graph-rag:rag-flow"
    },
    "document-rag": {
      "request": "non-persistent://tg/request/document-rag:rag-flow",
      "response": "non-persistent://tg/response/document-rag:rag-flow"
    },
    "embeddings": {
      "request": "non-persistent://tg/request/embeddings:rag-flow",
      "response": "non-persistent://tg/response/embeddings:rag-flow"
    }
  }
}
```

### Document Processing Flow Class
```json
{
  "description": "Document ingestion and processing flow",
  "interfaces": {
    "text-load": "persistent://tg/flow/text-document-load:doc-proc",
    "document-load": "persistent://tg/flow/document-load:doc-proc",
    "triples-store": "persistent://tg/flow/triples-store:doc-proc",
    "embeddings": {
      "request": "non-persistent://tg/request/embeddings:doc-proc",
      "response": "non-persistent://tg/response/embeddings:doc-proc"
    }
  }
}
```