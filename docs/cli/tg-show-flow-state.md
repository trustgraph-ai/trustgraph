# tg-show-flow-state

Displays the processor states for a specific flow and its associated flow class.

## Synopsis

```bash
tg-show-flow-state [options]
```

## Description

The `tg-show-flow-state` command shows the current state of processors within a specific TrustGraph flow instance and its corresponding flow class. It queries the metrics system to determine which processing components are running and displays their status with visual indicators.

This command is essential for monitoring flow health and debugging processing issues.

## Options

### Optional Arguments

- `-f, --flow-id ID`: Flow instance ID to examine (default: `default`)
- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-m, --metrics-url URL`: Metrics API URL (default: `http://localhost:8088/api/metrics`)

## Examples

### Check Default Flow State
```bash
tg-show-flow-state
```

### Check Specific Flow
```bash
tg-show-flow-state -f "production-flow"
```

### Use Custom Metrics URL
```bash
tg-show-flow-state \
  -f "research-flow" \
  -m "http://metrics-server:8088/api/metrics"
```

### Check Flow in Different Environment
```bash
tg-show-flow-state \
  -f "staging-flow" \
  -u "http://staging:8088/" \
  -m "http://staging:8088/api/metrics"
```

## Output Format

The command displays processor states for both the flow instance and its flow class:

```
Flow production-flow
- pdf-processor                💚
- text-extractor              💚
- embeddings-generator        💚
- knowledge-builder           ❌
- document-indexer            💚

Class document-processing-v2
- base-pdf-processor          💚
- base-text-extractor         💚
- base-embeddings-generator   💚
- base-knowledge-builder      💚
- base-document-indexer       💚
```

### Status Indicators
- **💚 (Green Heart)**: Processor is running and healthy
- **❌ (Red X)**: Processor is not running or unhealthy

### Information Displayed
- **Flow Section**: Shows the state of processors in the specific flow instance
- **Class Section**: Shows the state of processors in the flow class template
- **Processor Names**: Individual processing components within the flow

## Use Cases

### Flow Health Monitoring
```bash
# Monitor flow health continuously
monitor_flow_health() {
  local flow_id="$1"
  local interval="${2:-30}"  # Default 30 seconds
  
  echo "Monitoring flow health: $flow_id"
  echo "Refresh interval: ${interval}s"
  echo "Press Ctrl+C to stop"
  
  while true; do
    clear
    echo "Flow Health Monitor - $(date)"
    echo "=============================="
    
    tg-show-flow-state -f "$flow_id"
    
    sleep "$interval"
  done
}

# Monitor production flow
monitor_flow_health "production-flow" 15
```

### Debugging Processing Issues
```bash
# Comprehensive flow debugging
debug_flow_issues() {
  local flow_id="$1"
  
  echo "Debugging flow: $flow_id"
  echo "======================="
  
  # Check flow state
  echo "1. Processor States:"
  tg-show-flow-state -f "$flow_id"
  
  # Check flow configuration
  echo -e "\n2. Flow Configuration:"
  tg-show-flows | grep "$flow_id"
  
  # Check active processing
  echo -e "\n3. Active Processing:"
  tg-show-flows | grep -i processing
  
  # Check system resources
  echo -e "\n4. System Resources:"
  free -h
  df -h
  
  echo -e "\nDebugging complete for: $flow_id"
}

# Debug specific flow
debug_flow_issues "problematic-flow"
```

### Multi-Flow Status Dashboard
```bash
# Create status dashboard for multiple flows
create_flow_dashboard() {
  local flows=("$@")
  
  echo "TrustGraph Flow Dashboard - $(date)"
  echo "==================================="
  
  for flow in "${flows[@]}"; do
    echo -e "\n=== Flow: $flow ==="
    tg-show-flow-state -f "$flow" 2>/dev/null || echo "Flow not found or inaccessible"
  done
  
  echo -e "\n=== Summary ==="
  echo "Total flows monitored: ${#flows[@]}"
  echo "Dashboard generated: $(date)"
}

# Monitor multiple flows
flows=("production-flow" "research-flow" "development-flow")
create_flow_dashboard "${flows[@]}"
```

### Automated Health Checks
```bash
# Automated health check with alerts
health_check_with_alerts() {
  local flow_id="$1"
  local alert_email="$2"
  
  echo "Performing health check for: $flow_id"
  
  # Capture flow state
  flow_state=$(tg-show-flow-state -f "$flow_id" 2>&1)
  
  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to get flow state"
    # Send alert email if configured
    if [ -n "$alert_email" ]; then
      echo "Flow $flow_id is not responding" | mail -s "TrustGraph Alert" "$alert_email"
    fi
    return 1
  fi
  
  # Check for failed processors
  failed_count=$(echo "$flow_state" | grep -c "❌")
  
  if [ "$failed_count" -gt 0 ]; then
    echo "WARNING: $failed_count processors are not running"
    echo "$flow_state"
    
    # Send alert if configured
    if [ -n "$alert_email" ]; then
      echo -e "Flow $flow_id has $failed_count failed processors:\n\n$flow_state" | \
        mail -s "TrustGraph Health Alert" "$alert_email"
    fi
    return 1
  else
    echo "✓ All processors are running normally"
    return 0
  fi
}

# Run health check
health_check_with_alerts "production-flow" "admin@company.com"
```

## Advanced Usage

### Flow State Comparison
```bash
# Compare flow states between environments
compare_flow_states() {
  local flow_id="$1"
  local env1_url="$2"
  local env2_url="$3"
  
  echo "Comparing flow state: $flow_id"
  echo "Environment 1: $env1_url"
  echo "Environment 2: $env2_url"
  echo "================================"
  
  # Get states from both environments
  echo "Environment 1 State:"
  tg-show-flow-state -f "$flow_id" -u "$env1_url" -m "$env1_url/api/metrics"
  
  echo -e "\nEnvironment 2 State:"
  tg-show-flow-state -f "$flow_id" -u "$env2_url" -m "$env2_url/api/metrics"
  
  echo -e "\nComparison complete"
}

# Compare production vs staging
compare_flow_states "main-flow" "http://prod:8088" "http://staging:8088"
```

### Historical State Tracking
```bash
# Track flow state over time
track_flow_state_history() {
  local flow_id="$1"
  local log_file="flow_state_history.log"
  local interval="${2:-60}"  # Default 1 minute
  
  echo "Starting flow state tracking: $flow_id"
  echo "Log file: $log_file"
  echo "Interval: ${interval}s"
  
  while true; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Get current state
    state_output=$(tg-show-flow-state -f "$flow_id" 2>&1)
    
    if [ $? -eq 0 ]; then
      # Count healthy and failed processors
      healthy_count=$(echo "$state_output" | grep -c "💚")
      failed_count=$(echo "$state_output" | grep -c "❌")
      
      # Log summary
      echo "$timestamp,$flow_id,$healthy_count,$failed_count" >> "$log_file"
      
      # If there are failures, log details
      if [ "$failed_count" -gt 0 ]; then
        echo "$timestamp - FAILURES DETECTED in $flow_id:" >> "${log_file}.detailed"
        echo "$state_output" >> "${log_file}.detailed"
        echo "---" >> "${log_file}.detailed"
      fi
    else
      echo "$timestamp,$flow_id,ERROR,ERROR" >> "$log_file"
    fi
    
    sleep "$interval"
  done
}

# Start tracking (run in background)
track_flow_state_history "production-flow" 30 &
```

### State-Based Actions
```bash
# Perform actions based on flow state
state_based_actions() {
  local flow_id="$1"
  
  echo "Checking flow state for automated actions: $flow_id"
  
  # Get current state
  state_output=$(tg-show-flow-state -f "$flow_id")
  
  if [ $? -ne 0 ]; then
    echo "ERROR: Cannot get flow state"
    return 1
  fi
  
  # Check specific processors
  if echo "$state_output" | grep -q "pdf-processor.*❌"; then
    echo "PDF processor is down - attempting restart..."
    # Restart specific processor (this would need additional commands)
    # restart_processor "$flow_id" "pdf-processor"
  fi
  
  if echo "$state_output" | grep -q "embeddings-generator.*❌"; then
    echo "Embeddings generator is down - checking dependencies..."
    # Check GPU availability, memory, etc.
    nvidia-smi 2>/dev/null || echo "GPU not available"
  fi
  
  # Count total failures
  failed_count=$(echo "$state_output" | grep -c "❌")
  
  if [ "$failed_count" -gt 3 ]; then
    echo "CRITICAL: More than 3 processors failed - considering flow restart"
    # This would trigger more serious recovery actions
  fi
}
```

### Performance Correlation
```bash
# Correlate flow state with performance metrics
correlate_state_performance() {
  local flow_id="$1"
  local metrics_url="$2"
  
  echo "Correlating flow state with performance for: $flow_id"
  
  # Get flow state
  state_output=$(tg-show-flow-state -f "$flow_id" -m "$metrics_url")
  healthy_count=$(echo "$state_output" | grep -c "💚")
  failed_count=$(echo "$state_output" | grep -c "❌")
  
  echo "Processors - Healthy: $healthy_count, Failed: $failed_count"
  
  # Get performance metrics (this would need additional API calls)
  # throughput=$(get_flow_throughput "$flow_id" "$metrics_url")
  # latency=$(get_flow_latency "$flow_id" "$metrics_url")
  
  # echo "Performance - Throughput: ${throughput}/min, Latency: ${latency}ms"
  
  # Calculate health ratio
  total_processors=$((healthy_count + failed_count))
  if [ "$total_processors" -gt 0 ]; then
    health_ratio=$(echo "scale=2; $healthy_count * 100 / $total_processors" | bc)
    echo "Health ratio: ${health_ratio}%"
  fi
}
```

## Integration with Monitoring Systems

### Prometheus Integration
```bash
# Export flow state metrics to Prometheus format
export_prometheus_metrics() {
  local flow_id="$1"
  local metrics_file="flow_state_metrics.prom"
  
  # Get flow state
  state_output=$(tg-show-flow-state -f "$flow_id")
  
  # Count states
  healthy_count=$(echo "$state_output" | grep -c "💚")
  failed_count=$(echo "$state_output" | grep -c "❌")
  
  # Generate Prometheus metrics
  cat > "$metrics_file" << EOF
# HELP trustgraph_flow_processors_healthy Number of healthy processors in flow
# TYPE trustgraph_flow_processors_healthy gauge
trustgraph_flow_processors_healthy{flow_id="$flow_id"} $healthy_count

# HELP trustgraph_flow_processors_failed Number of failed processors in flow
# TYPE trustgraph_flow_processors_failed gauge
trustgraph_flow_processors_failed{flow_id="$flow_id"} $failed_count

# HELP trustgraph_flow_health_ratio Ratio of healthy processors
# TYPE trustgraph_flow_health_ratio gauge
EOF
  
  total=$((healthy_count + failed_count))
  if [ "$total" -gt 0 ]; then
    ratio=$(echo "scale=4; $healthy_count / $total" | bc)
    echo "trustgraph_flow_health_ratio{flow_id=\"$flow_id\"} $ratio" >> "$metrics_file"
  fi
  
  echo "Prometheus metrics exported to: $metrics_file"
}
```

### Grafana Dashboard Data
```bash
# Generate data for Grafana dashboard
generate_grafana_data() {
  local flows=("$@")
  local output_file="grafana_flow_data.json"
  
  echo "Generating Grafana dashboard data..."
  
  echo "{" > "$output_file"
  echo "  \"flows\": [" >> "$output_file"
  
  for i in "${!flows[@]}"; do
    flow="${flows[$i]}"
    
    # Get flow state
    state_output=$(tg-show-flow-state -f "$flow" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
      healthy=$(echo "$state_output" | grep -c "💚")
      failed=$(echo "$state_output" | grep -c "❌")
    else
      healthy=0
      failed=0
    fi
    
    echo "    {" >> "$output_file"
    echo "      \"flow_id\": \"$flow\"," >> "$output_file"
    echo "      \"healthy_processors\": $healthy," >> "$output_file"
    echo "      \"failed_processors\": $failed," >> "$output_file"
    echo "      \"timestamp\": \"$(date -Iseconds)\"" >> "$output_file"
    
    if [ $i -lt $((${#flows[@]} - 1)) ]; then
      echo "    }," >> "$output_file"
    else
      echo "    }" >> "$output_file"
    fi
  done
  
  echo "  ]" >> "$output_file"
  echo "}" >> "$output_file"
  
  echo "Grafana data generated: $output_file"
}
```

## Error Handling

### Flow Not Found
```bash
Exception: Flow 'nonexistent-flow' not found
```
**Solution**: Verify the flow ID exists with `tg-show-flows`.

### Metrics API Unavailable
```bash
Exception: Connection refused to metrics API
```
**Solution**: Check metrics URL and ensure metrics service is running.

### Permission Issues
```bash
Exception: Access denied to metrics
```
**Solution**: Verify permissions for accessing metrics and flow information.

### Invalid Flow State
```bash
Exception: Unable to parse flow state
```
**Solution**: Check if the flow is properly initialized and processors are configured.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-flows`](tg-show-flows.md) - List all flows
- [`tg-show-processor-state`](tg-show-processor-state.md) - Show all processor states
- [`tg-start-flow`](tg-start-flow.md) - Start flow instances
- [`tg-stop-flow`](tg-stop-flow.md) - Stop flow instances

## API Integration

This command integrates with:
- TrustGraph Flow API for flow information
- Prometheus/Metrics API for processor state information

## Best Practices

1. **Regular Monitoring**: Check flow states regularly in production
2. **Automated Alerts**: Set up automated health checks with alerting
3. **Historical Tracking**: Maintain historical flow state data
4. **Integration**: Integrate with monitoring systems like Prometheus/Grafana
5. **Documentation**: Document expected processor configurations
6. **Correlation**: Correlate flow state with performance metrics
7. **Recovery Procedures**: Develop automated recovery procedures for common failures

## Troubleshooting

### No Processors Shown
```bash
# Check if flow exists
tg-show-flows | grep "flow-id"

# Verify metrics service
curl -s http://localhost:8088/api/metrics/query?query=processor_info
```

### Inconsistent States
```bash
# Check metrics service health
curl -s http://localhost:8088/api/metrics/health

# Restart metrics collection if needed
```

### Connection Issues
```bash
# Test API connectivity
curl -s http://localhost:8088/api/v1/flows

# Test metrics connectivity  
curl -s http://localhost:8088/api/metrics/query?query=up
```