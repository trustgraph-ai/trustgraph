# tg-show-token-rate

## Synopsis

```
tg-show-token-rate [OPTIONS]
```

## Description

The `tg-show-token-rate` command displays a live stream of token usage rates from TrustGraph processors. It monitors both input and output tokens, showing instantaneous rates and cumulative averages over time. This command is essential for monitoring LLM token consumption and understanding processing throughput.

The command queries the metrics endpoint for token usage data and displays:
- Input token rates (tokens per second)
- Output token rates (tokens per second) 
- Total token rates (combined input + output)

All rates are calculated as averages since the command started running.

## Options

- `-m, --metrics-url URL`
  - Metrics endpoint URL to query for token information
  - Default: `http://localhost:8088/api/metrics`
  - Should point to a Prometheus-compatible metrics endpoint

- `-p, --period SECONDS`
  - Sampling period in seconds between measurements
  - Default: `1`
  - Controls how frequently token rates are updated

- `-n, --number-samples COUNT`
  - Number of samples to collect before stopping
  - Default: `100`
  - Set to a large value for continuous monitoring

- `-h, --help`
  - Show help message and exit

## Examples

### Basic Usage

Monitor token rates with default settings (1-second intervals, 100 samples):
```bash
tg-show-token-rate
```

### Custom Sampling Period

Monitor token rates with 5-second intervals:
```bash
tg-show-token-rate --period 5
```

### Continuous Monitoring

Monitor token rates continuously (1000 samples):
```bash
tg-show-token-rate -n 1000
```

### Remote Monitoring

Monitor token rates from a remote TrustGraph instance:
```bash
tg-show-token-rate -m http://10.0.1.100:8088/api/metrics
```

### High-Frequency Monitoring

Monitor token rates with sub-second precision:
```bash
tg-show-token-rate --period 0.5 --number-samples 200
```

## Output Format

The command displays a table with continuously updated token rates:
```
     Input     Output      Total
     -----     ------      -----
      12.3       8.7       21.0
      15.2      10.1       25.3
      18.7      12.4       31.1
      ...
```

Each row shows:
- **Input**: Average input tokens per second since monitoring started
- **Output**: Average output tokens per second since monitoring started  
- **Total**: Combined input + output tokens per second

## Advanced Usage

### Token Rate Analysis

Create a script to analyze token usage patterns:
```bash
#!/bin/bash
echo "Starting token rate analysis..."
tg-show-token-rate --period 2 --number-samples 60 > token_rates.txt
echo "Analysis complete. Data saved to token_rates.txt"
```

### Performance Monitoring

Monitor token rates during load testing:
```bash
#!/bin/bash
echo "Starting load test monitoring..."
tg-show-token-rate --period 1 --number-samples 300 | tee load_test_tokens.log
```

### Alert on High Token Usage

Create an alert script for excessive token consumption:
```bash
#!/bin/bash
tg-show-token-rate -n 10 -p 5 | tail -n 1 | awk '{
    if ($3 > 100) {
        print "WARNING: High token rate detected:", $3, "tokens/sec"
        exit 1
    }
}'
```

### Cost Estimation

Estimate token costs during processing:
```bash
#!/bin/bash
echo "Monitoring token usage for cost estimation..."
tg-show-token-rate --period 10 --number-samples 36 | \
awk 'NR>2 {total+=$3} END {print "Average tokens/sec:", total/NR-2}'
```

## Error Handling

The command handles various error conditions:

- **Connection errors**: If the metrics endpoint is unavailable
- **Invalid JSON**: If the metrics response is malformed
- **Missing metrics**: If token metrics are not found
- **Network timeouts**: If requests to the metrics endpoint time out

Common error scenarios:
```bash
# Metrics endpoint not available
tg-show-token-rate -m http://invalid-host:8088/api/metrics
# Output: Exception: [Connection error details]

# Invalid period value
tg-show-token-rate --period 0
# Output: Exception: [Invalid period error]
```

## Integration with Other Commands

### With Cost Monitoring

Combine with token cost analysis:
```bash
echo "=== Token Rates ==="
tg-show-token-rate -n 5 -p 2
echo
echo "=== Token Costs ==="
tg-show-token-costs
```

### With Processor State

Monitor tokens alongside processor health:
```bash
echo "=== Processor States ==="
tg-show-processor-state
echo
echo "=== Token Rates ==="
tg-show-token-rate -n 10 -p 1
```

### With Flow Monitoring

Track token usage per flow:
```bash
#!/bin/bash
echo "=== Active Flows ==="
tg-show-flows
echo
echo "=== Token Usage ==="
tg-show-token-rate -n 20 -p 3
```

## Best Practices

1. **Baseline Monitoring**: Establish baseline token rates for normal operation
2. **Alert Thresholds**: Set up alerts for unusually high token consumption
3. **Cost Tracking**: Monitor token rates to estimate operational costs
4. **Load Testing**: Use during load testing to understand capacity limits
5. **Historical Analysis**: Save token rate data for trend analysis

## Troubleshooting

### No Token Data

If no token rates are displayed:
1. Verify that TrustGraph processors are actively processing requests
2. Check that token metrics are being exported properly
3. Ensure the metrics endpoint is accessible
4. Verify that LLM services are receiving requests

### Inconsistent Rates

For inconsistent or erratic token rates:
1. Check for network issues affecting metrics collection
2. Verify that the sampling period is appropriate for your workload
3. Ensure multiple processors aren't conflicting
4. Check system resources (CPU, memory) on the TrustGraph instance

### High Token Rates

If token rates are unexpectedly high:
1. Investigate the types of queries being processed
2. Check for inefficient prompts or large document processing
3. Verify that caching is working properly
4. Consider if the workload justifies the token usage

## Performance Considerations

- **Sampling Frequency**: Higher frequencies provide more granular data but consume more resources
- **Network Latency**: Consider network latency when setting sampling periods
- **Metrics Storage**: Long monitoring sessions generate significant data
- **Resource Usage**: The command itself uses minimal resources

## Related Commands

- [`tg-show-token-costs`](tg-show-token-costs.md) - Display token usage costs
- [`tg-show-processor-state`](tg-show-processor-state.md) - Show processor states
- [`tg-show-flow-state`](tg-show-flow-state.md) - Display flow processor states
- [`tg-show-config`](tg-show-config.md) - Show TrustGraph configuration

## See Also

- TrustGraph Token Management Documentation
- Prometheus Metrics Configuration
- LLM Cost Optimization Guide