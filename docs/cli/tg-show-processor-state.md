# tg-show-processor-state

## Synopsis

```
tg-show-processor-state [OPTIONS]
```

## Description

The `tg-show-processor-state` command displays the current state of TrustGraph processors by querying the metrics endpoint. It retrieves processor information from the Prometheus metrics API and displays active processors with visual status indicators.

This command is useful for:
- Monitoring processor health and availability
- Verifying that processors are running correctly
- Troubleshooting processor connectivity issues
- Getting a quick overview of active TrustGraph components

## Options

- `-m, --metrics-url URL`
  - Metrics endpoint URL to query for processor information
  - Default: `http://localhost:8088/api/metrics`
  - Should point to a Prometheus-compatible metrics endpoint

- `-h, --help`
  - Show help message and exit

## Examples

### Basic Usage

Display processor states using the default metrics URL:
```bash
tg-show-processor-state
```

### Custom Metrics URL

Query processor states from a different metrics endpoint:
```bash
tg-show-processor-state -m http://metrics.example.com:8088/api/metrics
```

### Remote Monitoring

Monitor processors on a remote TrustGraph instance:
```bash
tg-show-processor-state --metrics-url http://10.0.1.100:8088/api/metrics
```

## Output Format

The command displays processor information in a table format:
```
  processor_name                 💚
  another_processor              💚
  third_processor                💚
```

Each line shows:
- Processor name (left-aligned, 30 characters wide)
- Status indicator (💚 for active processors)

## Advanced Usage

### Monitoring Script

Create a monitoring script to periodically check processor states:
```bash
#!/bin/bash
while true; do
    echo "=== Processor State Check ===" 
    date
    tg-show-processor-state
    echo
    sleep 30
done
```

### Health Check Integration

Use in health check scripts:
```bash
#!/bin/bash
output=$(tg-show-processor-state 2>&1)
if [ $? -eq 0 ]; then
    echo "Processors are running"
    echo "$output"
else
    echo "Error checking processor state: $output"
    exit 1
fi
```

### Multiple Environment Monitoring

Monitor processors across different environments:
```bash
#!/bin/bash
for env in dev staging prod; do
    echo "=== $env Environment ==="
    tg-show-processor-state -m "http://${env}-metrics:8088/api/metrics"
    echo
done
```

## Error Handling

The command handles various error conditions:

- **Connection errors**: If the metrics endpoint is unavailable
- **Invalid JSON**: If the metrics response is malformed
- **Missing data**: If the expected processor_info metric is not found
- **HTTP errors**: If the metrics endpoint returns an error status

Common error scenarios:
```bash
# Metrics endpoint not available
tg-show-processor-state -m http://invalid-host:8088/api/metrics
# Output: Exception: [Connection error details]

# Invalid URL format
tg-show-processor-state -m "not-a-url"
# Output: Exception: [URL parsing error]
```

## Integration with Other Commands

### With Flow Monitoring

Combine with flow state monitoring:
```bash
echo "=== Processor States ==="
tg-show-processor-state
echo
echo "=== Flow States ==="
tg-show-flow-state
```

### With Configuration Display

Check processors and current configuration:
```bash
echo "=== Active Processors ==="
tg-show-processor-state
echo
echo "=== Current Configuration ==="
tg-show-config
```

## Best Practices

1. **Regular Monitoring**: Include in regular health check routines
2. **Error Handling**: Always check command exit status in scripts
3. **Logging**: Capture output for historical analysis
4. **Alerting**: Set up alerts based on processor availability
5. **Documentation**: Keep track of expected processors for each environment

## Troubleshooting

### No Processors Shown

If no processors are displayed:
1. Verify the metrics endpoint is accessible
2. Check that TrustGraph processors are running
3. Ensure processors are properly configured to export metrics
4. Verify the metrics URL is correct

### Connection Issues

For connection problems:
1. Test network connectivity to the metrics endpoint
2. Verify the metrics service is running
3. Check firewall rules and network policies
4. Ensure the correct port is being used

### Metrics Format Issues

If the command fails with JSON parsing errors:
1. Verify the metrics endpoint returns Prometheus-compatible data
2. Check that the `processor_info` metric exists
3. Ensure the metrics service is properly configured

## Related Commands

- [`tg-show-flow-state`](tg-show-flow-state.md) - Display flow processor states
- [`tg-show-config`](tg-show-config.md) - Show TrustGraph configuration
- [`tg-show-token-costs`](tg-show-token-costs.md) - Display token usage costs
- [`tg-show-library-processing`](tg-show-library-processing.md) - Show library processing status

## See Also

- TrustGraph Processor Documentation
- Prometheus Metrics Configuration
- TrustGraph Monitoring Guide