# tg-start-flow

Starts a processing flow using a defined flow class.

## Synopsis

```bash
tg-start-flow -n CLASS_NAME -i FLOW_ID -d DESCRIPTION [options]
```

## Description

The `tg-start-flow` command creates and starts a new processing flow instance based on a predefined flow class. Flow classes define the processing pipeline configuration, while flow instances are running implementations of those classes with specific identifiers.

Once started, a flow provides endpoints for document processing, knowledge queries, and other TrustGraph services through its configured interfaces.

## Options

### Required Arguments

- `-n, --class-name CLASS_NAME`: Name of the flow class to instantiate
- `-i, --flow-id FLOW_ID`: Unique identifier for the new flow instance
- `-d, --description DESCRIPTION`: Human-readable description of the flow

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Start Basic Document Processing Flow
```bash
tg-start-flow \
  -n "document-rag+graph-rag" \
  -i "research-flow" \
  -d "Research document processing pipeline"
```

### Start Custom Flow Class
```bash
tg-start-flow \
  -n "medical-analysis" \
  -i "medical-research-2024" \
  -d "Medical research analysis for 2024 studies"
```

### Using Custom API URL
```bash
tg-start-flow \
  -n "document-processing" \
  -i "production-flow" \
  -d "Production document processing" \
  -u http://production:8088/
```

## Prerequisites

### Flow Class Must Exist
Before starting a flow, the flow class must be available in the system:

```bash
# Check available flow classes
tg-show-flow-classes

# Upload a flow class if needed
tg-put-flow-class -n "my-class" -f flow-definition.json
```

### System Requirements
- TrustGraph API gateway must be running
- Required processing components must be available
- Sufficient system resources for the flow's processing needs

## Flow Lifecycle

1. **Flow Class Definition**: Flow classes define processing pipelines
2. **Flow Instance Creation**: `tg-start-flow` creates a running instance
3. **Service Availability**: Flow provides configured service endpoints
4. **Processing**: Documents and queries can be processed through the flow
5. **Flow Termination**: Use `tg-stop-flow` to stop the instance

## Error Handling

### Flow Class Not Found
```bash
Exception: Flow class 'invalid-class' not found
```
**Solution**: Check available flow classes with `tg-show-flow-classes` and ensure the class name is correct.

### Flow ID Already Exists
```bash
Exception: Flow ID 'my-flow' already exists
```
**Solution**: Choose a different flow ID or stop the existing flow with `tg-stop-flow`.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Verify the API URL and ensure TrustGraph is running.

### Resource Errors
```bash
Exception: Insufficient resources to start flow
```
**Solution**: Check system resources and ensure required processing components are available.

## Output

On successful flow creation:
```bash
Flow 'research-flow' started successfully using class 'document-rag+graph-rag'
```

## Flow Configuration

Once started, flows provide service interfaces based on their class definition. Common interfaces include:

### Request/Response Services
- **agent**: Interactive Q&A service
- **graph-rag**: Graph-based retrieval augmented generation
- **document-rag**: Document-based retrieval augmented generation
- **text-completion**: LLM text completion
- **embeddings**: Text embedding generation
- **triples**: Knowledge graph queries

### Fire-and-Forget Services
- **text-load**: Text document loading
- **document-load**: Document file loading
- **triples-store**: Knowledge graph storage

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-stop-flow`](tg-stop-flow.md) - Stop a running flow
- [`tg-show-flows`](tg-show-flows.md) - List active flows and their interfaces
- [`tg-show-flow-classes`](tg-show-flow-classes.md) - List available flow classes
- [`tg-put-flow-class`](tg-put-flow-class.md) - Upload/update flow class definitions
- [`tg-show-flow-state`](tg-show-flow-state.md) - Check flow status

## API Integration

This command uses the [Flow API](../apis/api-flow.md) with the `start-flow` operation to create and start flow instances.

## Use Cases

### Development Environment
```bash
tg-start-flow \
  -n "dev-pipeline" \
  -i "dev-$(date +%Y%m%d)" \
  -d "Development testing flow for $(date)"
```

### Research Projects
```bash
tg-start-flow \
  -n "research-analysis" \
  -i "climate-study" \
  -d "Climate change research document analysis"
```

### Production Processing
```bash
tg-start-flow \
  -n "production-pipeline" \
  -i "prod-primary" \
  -d "Primary production document processing pipeline"
```

### Specialized Processing
```bash
tg-start-flow \
  -n "medical-nlp" \
  -i "medical-trials" \
  -d "Medical trial document analysis and extraction"
```

## Best Practices

1. **Descriptive IDs**: Use meaningful flow IDs that indicate purpose and scope
2. **Clear Descriptions**: Provide detailed descriptions for flow tracking
3. **Resource Planning**: Ensure adequate resources before starting flows
4. **Monitoring**: Use `tg-show-flows` to monitor active flows
5. **Cleanup**: Stop unused flows to free up resources
6. **Documentation**: Document flow purposes and configurations for team use