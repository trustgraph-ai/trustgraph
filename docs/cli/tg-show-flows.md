# tg-show-flows

Shows configured flows with their interfaces and queue information.

## Synopsis

```bash
tg-show-flows [options]
```

## Description

The `tg-show-flows` command displays all currently configured flow instances, including their identifiers, class names, descriptions, and available service interfaces with corresponding Pulsar queue names.

This command is essential for understanding what flows are available, discovering service endpoints, and finding Pulsar queue names for direct API integration.

## Options

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Show All Flows
```bash
tg-show-flows
```

### Using Custom API URL
```bash
tg-show-flows -u http://production:8088/
```

## Output Format

The command displays each flow in a formatted table with the following information:

```
+-------+---------------------------+
| id    | research-flow             |
| class | document-rag+graph-rag    |
| desc  | Research document pipeline |
| queue | agent request: non-persistent://tg/request/agent:default |
|       | agent response: non-persistent://tg/request/agent:default |
|       | graph-rag request: non-persistent://tg/request/graph-rag:document-rag+graph-rag |
|       | graph-rag response: non-persistent://tg/request/graph-rag:document-rag+graph-rag |
|       | text-load: persistent://tg/flow/text-document-load:default |
+-------+---------------------------+

+-------+---------------------------+
| id    | medical-analysis          |
| class | medical-nlp               |
| desc  | Medical document analysis |
| queue | embeddings request: non-persistent://tg/request/embeddings:medical-nlp |
|       | embeddings response: non-persistent://tg/request/embeddings:medical-nlp |
|       | document-load: persistent://tg/flow/document-load:medical-analysis |
+-------+---------------------------+
```

### No Flows Available
```bash
No flows.
```

## Interface Types

The queue information shows two types of service interfaces:

### Request/Response Services
Services that accept requests and return responses:
```
agent request: non-persistent://tg/request/agent:default
agent response: non-persistent://tg/response/agent:default
```

### Fire-and-Forget Services
Services that accept data without returning responses:
```
text-load: persistent://tg/flow/text-document-load:default
```

## Service Interface Discovery

Use this command to discover available services and their queue names:

### Common Request/Response Services
- **agent**: Interactive Q&A service
- **graph-rag**: Graph-based retrieval augmented generation
- **document-rag**: Document-based retrieval augmented generation
- **text-completion**: LLM text completion service
- **prompt**: Prompt-based text generation
- **embeddings**: Text embedding generation
- **graph-embeddings**: Graph entity embeddings
- **triples**: Knowledge graph triple queries

### Common Fire-and-Forget Services
- **text-load**: Text document loading
- **document-load**: Document file loading
- **triples-store**: Knowledge graph storage
- **graph-embeddings-store**: Graph embedding storage
- **document-embeddings-store**: Document embedding storage
- **entity-contexts-load**: Entity context loading

## Queue Name Patterns

### Flow-Hosted Request/Response
```
non-persistent://tg/request/{service}:{flow-class}
non-persistent://tg/response/{service}:{flow-class}
```

### Flow-Hosted Fire-and-Forget
```
persistent://tg/flow/{service}:{flow-id}
```

## Error Handling

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Verify the API URL and ensure TrustGraph is running.

### Authentication Errors
```bash
Exception: Unauthorized
```
**Solution**: Check authentication credentials and permissions.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-start-flow`](tg-start-flow.md) - Start a new flow instance
- [`tg-stop-flow`](tg-stop-flow.md) - Stop a running flow
- [`tg-show-flow-blueprints`](tg-show-flow-blueprints.md) - List available flow blueprintes
- [`tg-show-flow-state`](tg-show-flow-state.md) - Show detailed flow status
- [`tg-show-config`](tg-show-config.md) - Show complete system configuration

## API Integration

This command uses the [Flow API](../apis/api-flow.md) to list flows and the [Config API](../apis/api-config.md) to retrieve interface descriptions.

## Use Cases

### Service Discovery
Find available services and their endpoints:
```bash
# List all flows and their services
tg-show-flows

# Use discovered queue names for direct Pulsar integration
```

### System Monitoring
Monitor active flows and their configurations:
```bash
# Check what flows are running
tg-show-flows

# Verify flow services are properly configured
```

### Development and Debugging
Understand flow configurations during development:
```bash
# Check if flow started correctly
tg-start-flow -n "my-class" -i "test-flow" -d "Test"
tg-show-flows

# Verify service interfaces are available
```

### Integration Planning
Plan API integrations by understanding available services:
```bash
# Discover queue names for Pulsar clients
tg-show-flows | grep "graph-rag request"

# Find WebSocket endpoints for real-time services
```

## Output Interpretation

### Flow Information
- **id**: Unique flow instance identifier
- **class**: Flow blueprint name used to create the instance
- **desc**: Human-readable flow description
- **queue**: Service interfaces and their Pulsar queue names

### Queue Names
Queue names indicate:
- **Persistence**: `persistent://` vs `non-persistent://`
- **Tenant**: Usually `tg`
- **Namespace**: `request`, `response`, or `flow`
- **Service**: The specific service name
- **Flow Identifier**: Either flow blueprint or flow ID

## Best Practices

1. **Regular Monitoring**: Check flows regularly to ensure they're running correctly
2. **Queue Documentation**: Save queue names for API integration documentation
3. **Flow Lifecycle**: Use in conjunction with flow start/stop commands
4. **Capacity Planning**: Monitor number of active flows for resource planning
5. **Service Discovery**: Use output to understand available capabilities