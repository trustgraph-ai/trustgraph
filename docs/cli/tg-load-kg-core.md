# tg-load-kg-core

Loads a stored knowledge core into a processing flow for active use.

## Synopsis

```bash
tg-load-kg-core --id CORE_ID [options]
```

## Description

The `tg-load-kg-core` command loads a previously stored knowledge core into an active processing flow, making the knowledge available for queries, reasoning, and other AI operations. This is different from storing knowledge cores - this command makes stored knowledge active and accessible within a specific flow context.

Once loaded, the knowledge core's RDF triples and graph embeddings become available for Graph RAG queries, agent reasoning, and other knowledge-based operations within the specified flow.

## Options

### Required Arguments

- `--id, --identifier CORE_ID`: Identifier of the knowledge core to load

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User identifier (default: `trustgraph`)
- `-f, --flow-id FLOW`: Flow ID to load knowledge into (default: `default`)
- `-c, --collection COLLECTION`: Collection identifier (default: `default`)

## Examples

### Load Knowledge Core into Default Flow
```bash
tg-load-kg-core --id "research-knowledge-v1"
```

### Load into Specific Flow
```bash
tg-load-kg-core \
  --id "medical-knowledge" \
  --flow-id "medical-analysis" \
  --user researcher
```

### Load with Custom Collection
```bash
tg-load-kg-core \
  --id "legal-documents" \
  --flow-id "legal-flow" \
  --collection "law-firm-data"
```

### Using Custom API URL
```bash
tg-load-kg-core \
  --id "production-knowledge" \
  --flow-id "prod-flow" \
  -u http://production:8088/
```

## Prerequisites

### Knowledge Core Must Exist
The knowledge core must be stored in the system:

```bash
# Check available knowledge cores
tg-show-kg-cores

# Store knowledge core if needed
tg-put-kg-core --id "my-knowledge" -i knowledge.msgpack
```

### Flow Must Be Running
The target flow must be active:

```bash
# Check running flows
tg-show-flows

# Start flow if needed
tg-start-flow -n "my-class" -i "my-flow" -d "Knowledge processing flow"
```

## Loading Process

1. **Validation**: Verifies knowledge core exists and flow is running
2. **Knowledge Retrieval**: Retrieves RDF triples and graph embeddings
3. **Flow Integration**: Makes knowledge available within flow context
4. **Index Building**: Creates searchable indexes for efficient querying
5. **Service Activation**: Enables knowledge-based services in the flow

## What Gets Loaded

### RDF Triples
- Subject-predicate-object relationships
- Entity definitions and properties
- Factual knowledge and assertions
- Metadata and provenance information

### Graph Embeddings
- Vector representations of entities
- Semantic similarity data
- Neural network-compatible formats
- Machine learning-ready representations

## Knowledge Availability

Once loaded, knowledge becomes available through:

### Graph RAG Queries
```bash
tg-invoke-graph-rag \
  -q "What information is available about AI research?" \
  -f my-flow
```

### Agent Interactions
```bash
tg-invoke-agent \
  -q "Tell me about the loaded knowledge" \
  -f my-flow
```

### Direct Triple Queries
```bash
tg-show-graph -f my-flow
```

## Output

Successful loading typically produces no output, but knowledge becomes queryable:

```bash
# Load knowledge (no output expected)
tg-load-kg-core --id "research-knowledge"

# Verify loading by querying
tg-show-graph | head -10
```

## Error Handling

### Knowledge Core Not Found
```bash
Exception: Knowledge core 'invalid-core' not found
```
**Solution**: Check available cores with `tg-show-kg-cores` and verify the core ID.

### Flow Not Found
```bash
Exception: Flow 'invalid-flow' not found
```
**Solution**: Verify the flow exists and is running with `tg-show-flows`.

### Permission Errors
```bash
Exception: Access denied to knowledge core
```
**Solution**: Verify user permissions for the specified knowledge core.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Resource Errors
```bash
Exception: Insufficient memory to load knowledge core
```
**Solution**: Check system resources or try loading smaller knowledge cores.

## Knowledge Core Management

### Loading Workflow
```bash
# 1. Check available knowledge
tg-show-kg-cores

# 2. Ensure flow is running
tg-show-flows

# 3. Load knowledge into flow
tg-load-kg-core --id "my-knowledge" --flow-id "my-flow"

# 4. Verify knowledge is accessible
tg-invoke-graph-rag -q "What knowledge is loaded?" -f my-flow
```

### Multiple Knowledge Cores
```bash
# Load multiple cores for comprehensive knowledge
tg-load-kg-core --id "core-1" --flow-id "research-flow"
tg-load-kg-core --id "core-2" --flow-id "research-flow"
tg-load-kg-core --id "core-3" --flow-id "research-flow"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-kg-cores`](tg-show-kg-cores.md) - List available knowledge cores
- [`tg-put-kg-core`](tg-put-kg-core.md) - Store knowledge core in system
- [`tg-unload-kg-core`](tg-unload-kg-core.md) - Remove knowledge from flow
- [`tg-show-graph`](tg-show-graph.md) - View loaded knowledge triples
- [`tg-invoke-graph-rag`](tg-invoke-graph-rag.md) - Query loaded knowledge

## API Integration

This command uses the [Knowledge API](../apis/api-knowledge.md) with the `load-kg-core` operation to make stored knowledge active within flows.

## Use Cases

### Research Analysis
```bash
# Load research knowledge for analysis
tg-load-kg-core \
  --id "research-papers-2024" \
  --flow-id "research-analysis" \
  --collection "academic-research"

# Query the research knowledge
tg-invoke-graph-rag \
  -q "What are the main research trends in AI?" \
  -f research-analysis
```

### Domain-Specific Processing
```bash
# Load medical knowledge for healthcare analysis
tg-load-kg-core \
  --id "medical-terminology" \
  --flow-id "healthcare-nlp" \
  --user medical-team
```

### Multi-Domain Knowledge
```bash
# Load knowledge from multiple domains
tg-load-kg-core --id "technical-specs" --flow-id "analysis-flow"
tg-load-kg-core --id "business-data" --flow-id "analysis-flow"
tg-load-kg-core --id "market-research" --flow-id "analysis-flow"
```

### Development and Testing
```bash
# Load test knowledge for development
tg-load-kg-core \
  --id "test-knowledge" \
  --flow-id "dev-flow" \
  --user developer
```

### Production Processing
```bash
# Load production knowledge
tg-load-kg-core \
  --id "production-kb-v2.1" \
  --flow-id "production-flow" \
  --collection "live-data"
```

## Performance Considerations

### Loading Time
- Large knowledge cores may take time to load
- Loading includes indexing for efficient querying
- Multiple cores can be loaded incrementally

### Memory Usage
- Knowledge cores consume memory proportional to their size
- Monitor system resources when loading large cores
- Consider flow capacity when loading multiple cores

### Query Performance
- Loaded knowledge enables faster query responses
- Pre-built indexes improve search performance
- Multiple cores may impact query speed

## Best Practices

1. **Pre-Loading**: Load knowledge cores before intensive querying
2. **Resource Planning**: Monitor memory usage with large knowledge cores
3. **Flow Management**: Use dedicated flows for specific knowledge domains
4. **Version Control**: Load specific knowledge core versions for reproducibility
5. **Testing**: Verify knowledge loading with simple queries
6. **Documentation**: Document which knowledge cores are loaded in which flows

## Knowledge Loading Strategy

### Single Domain
```bash
# Load focused knowledge for specific tasks
tg-load-kg-core --id "specialized-domain" --flow-id "domain-flow"
```

### Multi-Domain
```bash
# Load comprehensive knowledge for broad analysis
tg-load-kg-core --id "general-knowledge" --flow-id "general-flow"
tg-load-kg-core --id "domain-specific" --flow-id "general-flow"
```

### Incremental Loading
```bash
# Load knowledge incrementally as needed
tg-load-kg-core --id "base-knowledge" --flow-id "analysis-flow"
# ... perform some analysis ...
tg-load-kg-core --id "additional-knowledge" --flow-id "analysis-flow"
```