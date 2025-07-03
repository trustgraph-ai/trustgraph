# tg-unload-kg-core

Removes a knowledge core from an active flow without deleting the stored core.

## Synopsis

```bash
tg-unload-kg-core --id CORE_ID [options]
```

## Description

The `tg-unload-kg-core` command removes a previously loaded knowledge core from an active processing flow, making that knowledge unavailable for queries and processing within that specific flow. The knowledge core remains stored in the system and can be loaded again later or into different flows.

This is useful for managing flow memory usage, switching knowledge contexts, or temporarily removing knowledge without permanent deletion.

## Options

### Required Arguments

- `--id, --identifier CORE_ID`: Identifier of the knowledge core to unload

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User identifier (default: `trustgraph`)
- `-f, --flow-id FLOW`: Flow ID to unload knowledge from (default: `default`)

## Examples

### Unload from Default Flow
```bash
tg-unload-kg-core --id "research-knowledge"
```

### Unload from Specific Flow
```bash
tg-unload-kg-core \
  --id "medical-knowledge" \
  --flow-id "medical-analysis" \
  -U medical-team
```

### Unload Multiple Cores
```bash
# Unload several knowledge cores from a flow
tg-unload-kg-core --id "core-1" --flow-id "analysis-flow"
tg-unload-kg-core --id "core-2" --flow-id "analysis-flow"
tg-unload-kg-core --id "core-3" --flow-id "analysis-flow"
```

### Using Custom API URL
```bash
tg-unload-kg-core \
  --id "production-knowledge" \
  --flow-id "prod-flow" \
  -u http://production:8088/
```

## Prerequisites

### Knowledge Core Must Be Loaded
The knowledge core must currently be loaded in the specified flow:

```bash
# Check what's loaded by querying the flow
tg-show-graph -f target-flow | head -10

# If no output, core may not be loaded
```

### Flow Must Be Running
The target flow must be active:

```bash
# Check running flows
tg-show-flows

# Verify the target flow exists
tg-show-flows | grep "target-flow"
```

## Unloading Process

1. **Validation**: Verifies knowledge core is loaded in the specified flow
2. **Query Termination**: Stops any ongoing queries using the knowledge
3. **Index Cleanup**: Removes knowledge indexes from flow context
4. **Memory Release**: Frees memory allocated to the knowledge core
5. **Service Update**: Updates flow services to reflect knowledge unavailability

## Effects of Unloading

### Knowledge Becomes Unavailable
After unloading, the knowledge is no longer accessible through the flow:

```bash
# Before unloading - knowledge available
tg-invoke-graph-rag -q "What knowledge is loaded?" -f my-flow

# Unload the knowledge
tg-unload-kg-core --id "my-knowledge" --flow-id "my-flow"

# After unloading - reduced knowledge available
tg-invoke-graph-rag -q "What knowledge is loaded?" -f my-flow
```

### Memory Recovery
- RAM used by knowledge indexes is freed
- Flow performance may improve
- Other knowledge cores in the flow remain unaffected

### Core Preservation
- Knowledge core remains stored in the system
- Can be reloaded later
- Available for loading into other flows

## Output

Successful unloading typically produces no output:

```bash
# Unload core (no output expected)
tg-unload-kg-core --id "test-core" --flow-id "test-flow"

# Verify unloading by checking available knowledge
tg-show-graph -f test-flow | wc -l
# Should show fewer triples if core was successfully unloaded
```

## Error Handling

### Knowledge Core Not Loaded
```bash
Exception: Knowledge core 'my-core' not loaded in flow 'my-flow'
```
**Solution**: Verify the core is actually loaded using `tg-show-graph` or load it first with `tg-load-kg-core`.

### Flow Not Found
```bash
Exception: Flow 'invalid-flow' not found
```
**Solution**: Check running flows with `tg-show-flows` and verify the flow ID.

### Permission Errors
```bash
Exception: Access denied to unload knowledge core
```
**Solution**: Verify user permissions for the knowledge core and flow.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

## Verification

### Check Knowledge Reduction
```bash
# Count triples before unloading
before=$(tg-show-graph -f my-flow | wc -l)

# Unload knowledge
tg-unload-kg-core --id "my-core" --flow-id "my-flow"

# Count triples after unloading
after=$(tg-show-graph -f my-flow | wc -l)

echo "Triples before: $before, after: $after"
```

### Test Query Impact
```bash
# Test queries before and after unloading
tg-invoke-graph-rag -q "test query" -f my-flow

# Should work with loaded knowledge
tg-unload-kg-core --id "relevant-core" --flow-id "my-flow"

tg-invoke-graph-rag -q "test query" -f my-flow
# May return different results or "no relevant knowledge found"
```

## Use Cases

### Memory Management
```bash
# Free up memory by unloading unused knowledge
tg-unload-kg-core --id "large-historical-data" --flow-id "analysis-flow"

# Load more relevant knowledge
tg-load-kg-core --id "current-data" --flow-id "analysis-flow"
```

### Context Switching
```bash
# Switch from medical to legal knowledge context
tg-unload-kg-core --id "medical-knowledge" --flow-id "analysis-flow"
tg-load-kg-core --id "legal-knowledge" --flow-id "analysis-flow"
```

### Selective Knowledge Loading
```bash
# Load only specific knowledge for focused analysis
tg-unload-kg-core --id "general-knowledge" --flow-id "specialized-flow"
tg-load-kg-core --id "domain-specific" --flow-id "specialized-flow"
```

### Testing and Development
```bash
# Test flow behavior with different knowledge sets
tg-unload-kg-core --id "production-data" --flow-id "test-flow"
tg-load-kg-core --id "test-data" --flow-id "test-flow"

# Run tests
./run-knowledge-tests.sh

# Restore production knowledge
tg-unload-kg-core --id "test-data" --flow-id "test-flow"
tg-load-kg-core --id "production-data" --flow-id "test-flow"
```

### Flow Maintenance
```bash
# Prepare flow for maintenance by unloading all knowledge
cores=$(tg-show-kg-cores)
for core in $cores; do
    tg-unload-kg-core --id "$core" --flow-id "maintenance-flow" 2>/dev/null || true
done

# Perform maintenance
./flow-maintenance.sh

# Reload required knowledge
tg-load-kg-core --id "essential-core" --flow-id "maintenance-flow"
```

## Knowledge Management Workflow

### Dynamic Knowledge Loading
```bash
# Function to switch knowledge contexts
switch_knowledge_context() {
    local flow_id=$1
    local old_core=$2
    local new_core=$3
    
    echo "Switching from $old_core to $new_core in $flow_id"
    
    # Unload old knowledge
    tg-unload-kg-core --id "$old_core" --flow-id "$flow_id"
    
    # Load new knowledge
    tg-load-kg-core --id "$new_core" --flow-id "$flow_id"
    
    echo "Context switch completed"
}

# Usage
switch_knowledge_context "analysis-flow" "old-data" "new-data"
```

### Bulk Knowledge Management
```bash
# Unload all knowledge from a flow
unload_all_knowledge() {
    local flow_id=$1
    
    # Get list of potentially loaded cores
    tg-show-kg-cores | while read core; do
        echo "Attempting to unload $core from $flow_id"
        tg-unload-kg-core --id "$core" --flow-id "$flow_id" 2>/dev/null || true
    done
    
    echo "All knowledge unloaded from $flow_id"
}

# Usage
unload_all_knowledge "cleanup-flow"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-load-kg-core`](tg-load-kg-core.md) - Load knowledge core into flow
- [`tg-show-kg-cores`](tg-show-kg-cores.md) - List available knowledge cores
- [`tg-show-graph`](tg-show-graph.md) - View currently loaded knowledge
- [`tg-show-flows`](tg-show-flows.md) - List active flows

## API Integration

This command uses the [Knowledge API](../apis/api-knowledge.md) with the `unload-kg-core` operation to remove knowledge from active flows.

## Best Practices

1. **Memory Monitoring**: Monitor flow memory usage when loading/unloading knowledge
2. **Graceful Unloading**: Ensure no critical queries are running before unloading
3. **Documentation**: Document which knowledge cores are needed for each flow
4. **Testing**: Test flow behavior after unloading knowledge
5. **Backup Strategy**: Keep knowledge cores stored even when not loaded
6. **Performance Optimization**: Unload unused knowledge to improve performance

## Troubleshooting

### Knowledge Still Appears in Queries
```bash
# If knowledge still appears after unloading
# Check if multiple cores contain similar data
tg-show-graph -f my-flow | grep "expected-removed-entity"

# Verify all relevant cores were unloaded
```

### Memory Not Released
```bash
# If memory usage doesn't decrease after unloading
# Check system memory usage
free -h

# Contact system administrator if memory leak suspected
```

### Query Performance Issues
```bash
# If queries become slow after unloading
# May need to reload essential knowledge
tg-load-kg-core --id "essential-core" --flow-id "slow-flow"

# Or restart the flow
tg-stop-flow -i "slow-flow"
tg-start-flow -n "flow-class" -i "slow-flow" -d "Restarted flow"
```