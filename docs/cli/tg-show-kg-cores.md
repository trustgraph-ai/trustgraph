# tg-show-kg-cores

Shows available knowledge cores in the TrustGraph system.

## Synopsis

```bash
tg-show-kg-cores [options]
```

## Description

The `tg-show-kg-cores` command lists all knowledge cores available in the TrustGraph system for a specific user. Knowledge cores contain structured knowledge (RDF triples and graph embeddings) that can be loaded into flows for processing and querying.

This command is useful for discovering what knowledge resources are available, managing knowledge core inventories, and preparing for knowledge loading operations.

## Options

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User identifier (default: `trustgraph`)

## Examples

### List All Knowledge Cores
```bash
tg-show-kg-cores
```

### List Cores for Specific User
```bash
tg-show-kg-cores -U researcher
```

### Using Custom API URL
```bash
tg-show-kg-cores -u http://production:8088/
```

## Output Format

The command lists knowledge core identifiers, one per line:

```
medical-knowledge-v1
research-papers-2024
legal-documents-core
technical-specifications
climate-data-march
```

### No Knowledge Cores
```bash
No knowledge cores.
```

## Knowledge Core Naming

Knowledge cores typically follow naming conventions that include:
- **Domain**: `medical-`, `legal-`, `technical-`
- **Content Type**: `papers-`, `documents-`, `data-`
- **Version/Date**: `v1`, `2024`, `march`

Example patterns:
- `medical-knowledge-v2.1`
- `research-papers-2024-q1`
- `legal-documents-updated`
- `technical-specs-current`

## Related Operations

After discovering knowledge cores, you can:

### Load into Flow
```bash
# Load core into active flow
tg-load-kg-core --kg-core-id "medical-knowledge-v1" --flow-id "medical-flow"
```

### Examine Contents
```bash
# Export core for examination
tg-get-kg-core --id "research-papers-2024" -o examination.msgpack
```

### Remove Unused Cores
```bash
# Delete obsolete cores
tg-delete-kg-core --id "old-knowledge-v1" -U researcher
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
**Solution**: Check authentication credentials and user permissions.

### User Not Found
```bash
Exception: User not found
```
**Solution**: Verify the user identifier exists in the system.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-put-kg-core`](tg-put-kg-core.md) - Store knowledge core from file
- [`tg-get-kg-core`](tg-get-kg-core.md) - Retrieve knowledge core to file
- [`tg-load-kg-core`](tg-load-kg-core.md) - Load knowledge core into flow
- [`tg-delete-kg-core`](tg-delete-kg-core.md) - Remove knowledge core
- [`tg-unload-kg-core`](tg-unload-kg-core.md) - Unload knowledge core from flow

## API Integration

This command uses the [Knowledge API](../apis/api-knowledge.md) with the `list-kg-cores` operation to retrieve available knowledge cores.

## Use Cases

### Knowledge Inventory
```bash
# Check what knowledge is available
tg-show-kg-cores

# Document available knowledge resources
tg-show-kg-cores > knowledge-inventory.txt
```

### Pre-Processing Verification
```bash
# Verify knowledge cores exist before loading
tg-show-kg-cores | grep "medical"
tg-load-kg-core --kg-core-id "medical-knowledge-v1" --flow-id "medical-flow"
```

### Multi-User Management
```bash
# Check knowledge for different users
tg-show-kg-cores -U researcher
tg-show-kg-cores -U analyst
tg-show-kg-cores -U admin
```

### Knowledge Discovery
```bash
# Find knowledge cores by pattern
tg-show-kg-cores | grep "2024"
tg-show-kg-cores | grep "medical"
tg-show-kg-cores | grep "v[0-9]"
```

### System Administration
```bash
# Audit knowledge core usage
for user in $(cat users.txt); do
    echo "User: $user"
    tg-show-kg-cores -U $user
    echo
done
```

### Development Workflow
```bash
# Check development knowledge cores
tg-show-kg-cores -U developer | grep "test"

# Load test knowledge for development
tg-load-kg-core --kg-core-id "test-knowledge" --flow-id "dev-flow"
```

## Knowledge Core Lifecycle

1. **Creation**: Knowledge cores created via `tg-put-kg-core` or document processing
2. **Discovery**: Use `tg-show-kg-cores` to find available cores
3. **Loading**: Load cores into flows with `tg-load-kg-core`
4. **Usage**: Query loaded knowledge via RAG or agent services
5. **Management**: Update, backup, or remove cores as needed

## Best Practices

1. **Regular Inventory**: Check available knowledge cores regularly
2. **Naming Conventions**: Use consistent naming for easier discovery
3. **User Organization**: Organize knowledge cores by user and purpose
4. **Version Management**: Track knowledge core versions and updates
5. **Cleanup**: Remove obsolete knowledge cores to save storage
6. **Documentation**: Document knowledge core contents and purposes

## Integration with Other Commands

### Knowledge Loading Workflow
```bash
# 1. Discover available knowledge
tg-show-kg-cores

# 2. Start appropriate flow
tg-start-flow -n "research-class" -i "research-flow" -d "Research analysis"

# 3. Load relevant knowledge
tg-load-kg-core --kg-core-id "research-papers-2024" --flow-id "research-flow"

# 4. Query the knowledge
tg-invoke-graph-rag -q "What are the latest research trends?" -f "research-flow"
```

### Knowledge Management Workflow
```bash
# 1. Audit current knowledge
tg-show-kg-cores > current-cores.txt

# 2. Import new knowledge
tg-put-kg-core --id "new-research-2024" -i new-research.msgpack

# 3. Verify import
tg-show-kg-cores | grep "new-research-2024"

# 4. Remove old versions
tg-delete-kg-core --id "old-research-2023"
```