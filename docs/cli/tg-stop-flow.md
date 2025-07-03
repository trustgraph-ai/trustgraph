# tg-stop-flow

Stops a running processing flow.

## Synopsis

```bash
tg-stop-flow -i FLOW_ID [options]
```

## Description

The `tg-stop-flow` command terminates a running flow instance and releases its associated resources. When a flow is stopped, it becomes unavailable for processing requests, and all its service endpoints are shut down.

This command is essential for flow lifecycle management, resource cleanup, and system maintenance operations.

## Options

### Required Arguments

- `-i, --flow-id FLOW_ID`: Identifier of the flow to stop

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Stop Specific Flow
```bash
tg-stop-flow -i research-flow
```

### Using Custom API URL
```bash
tg-stop-flow -i production-flow -u http://production:8088/
```

### Stop Multiple Flows
```bash
# Stop multiple flows in sequence
tg-stop-flow -i dev-flow-1
tg-stop-flow -i dev-flow-2
tg-stop-flow -i test-flow
```

## Prerequisites

### Flow Must Exist and Be Running
Before stopping a flow, verify it exists:

```bash
# Check running flows
tg-show-flows

# Stop the desired flow
tg-stop-flow -i my-flow
```

## Flow Termination Process

1. **Request Validation**: Verifies flow exists and is running
2. **Service Shutdown**: Stops all flow service endpoints
3. **Resource Cleanup**: Releases allocated system resources
4. **Queue Cleanup**: Cleans up associated Pulsar queues
5. **State Update**: Updates flow status to stopped

## Impact of Stopping Flows

### Service Unavailability
Once stopped, the flow's services become unavailable:
- REST API endpoints return errors
- WebSocket connections are terminated
- Pulsar queues are cleaned up

### In-Progress Operations
- **Completed**: Already finished operations remain completed
- **Active**: In-progress operations may be interrupted
- **Queued**: Pending operations are lost

### Resource Recovery
- **Memory**: Memory allocated to flow components is freed
- **CPU**: Processing resources are returned to system pool
- **Storage**: Temporary storage is cleaned up

## Error Handling

### Flow Not Found
```bash
Exception: Flow 'invalid-flow' not found
```
**Solution**: Check available flows with `tg-show-flows` and verify the flow ID.

### Flow Already Stopped
```bash
Exception: Flow 'my-flow' is not running
```
**Solution**: The flow is already stopped. Use `tg-show-flows` to check current status.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Verify the API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Insufficient permissions to stop flow
```
**Solution**: Check user permissions and authentication credentials.

## Output

On successful flow termination:
```bash
Flow 'research-flow' stopped successfully.
```

No output typically indicates successful operation.

## Flow Management Workflow

### Development Cycle
```bash
# 1. Start flow for development
tg-start-flow -n "dev-class" -i "dev-flow" -d "Development testing"

# 2. Use flow for testing
tg-invoke-graph-rag -q "test query" -f dev-flow

# 3. Stop flow when done
tg-stop-flow -i dev-flow
```

### Resource Management
```bash
# Check active flows
tg-show-flows

# Stop unused flows to free resources
tg-stop-flow -i old-research-flow
tg-stop-flow -i temporary-test-flow
```

### System Maintenance
```bash
# Stop all flows before maintenance
for flow in $(tg-show-flows | grep "id" | awk '{print $2}'); do
    tg-stop-flow -i "$flow"
done
```

## Safety Considerations

### Data Preservation
- **Knowledge Cores**: Loaded knowledge cores are preserved
- **Library Documents**: Library documents remain intact
- **Configuration**: System configuration is unaffected

### Service Dependencies
- **Dependent Services**: Ensure no critical services depend on the flow
- **Active Users**: Notify users before stopping production flows
- **Scheduled Operations**: Check for scheduled operations using the flow

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-start-flow`](tg-start-flow.md) - Start a new flow instance
- [`tg-show-flows`](tg-show-flows.md) - List active flows
- [`tg-show-flow-state`](tg-show-flow-state.md) - Check detailed flow status
- [`tg-show-flow-classes`](tg-show-flow-classes.md) - List available flow classes

## API Integration

This command uses the [Flow API](../apis/api-flow.md) with the `stop-flow` operation to terminate flow instances.

## Use Cases

### Development Environment Cleanup
```bash
# Clean up development flows at end of day
tg-stop-flow -i dev-$(whoami)
tg-stop-flow -i test-experimental
```

### Resource Optimization
```bash
# Stop idle flows to free resources
tg-show-flows | grep "idle" | while read flow; do
    tg-stop-flow -i "$flow"
done
```

### Environment Switching
```bash
# Switch from development to production configuration
tg-stop-flow -i dev-flow
tg-start-flow -n "production-class" -i "prod-flow" -d "Production processing"
```

### Maintenance Operations
```bash
# Prepare for system maintenance
echo "Stopping all flows for maintenance..."
tg-show-flows | grep -E "^[a-z-]+" | while read flow_id; do
    echo "Stopping $flow_id"
    tg-stop-flow -i "$flow_id"
done
```

### Flow Recycling
```bash
# Restart flow with fresh configuration
tg-stop-flow -i my-flow
tg-start-flow -n "updated-class" -i "my-flow" -d "Updated configuration"
```

## Best Practices

1. **Graceful Shutdown**: Allow in-progress operations to complete when possible
2. **User Notification**: Inform users before stopping production flows
3. **Resource Monitoring**: Check system resources after stopping flows
4. **Documentation**: Record why flows were stopped for audit purposes
5. **Verification**: Confirm flow stopped successfully with `tg-show-flows`
6. **Cleanup Planning**: Plan flow stops during low-usage periods

## Troubleshooting

### Flow Won't Stop
```bash
# Check flow status
tg-show-flow-state -i problematic-flow

# Force stop if necessary (implementation dependent)
# Contact system administrator if flow remains stuck
```

### Resource Not Released
```bash
# Check system resources after stopping
ps aux | grep trustgraph
netstat -an | grep 8088

# Restart TrustGraph if resources not properly released
```

### Service Still Responding
```bash
# Verify flow services are actually stopped
tg-invoke-graph-rag -q "test" -f stopped-flow

# Should return flow not found error
```