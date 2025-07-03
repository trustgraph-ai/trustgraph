# tg-show-library-processing

Displays all active library document processing records and their details.

## Synopsis

```bash
tg-show-library-processing [options]
```

## Description

The `tg-show-library-processing` command lists all library document processing records, showing the status and details of document processing jobs that have been initiated through the library system. This provides visibility into which documents are being processed, their associated flows, and processing metadata.

## Options

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User ID to filter processing records (default: `trustgraph`)

## Examples

### Show All Processing Records
```bash
tg-show-library-processing
```

### Show Processing for Specific User
```bash
tg-show-library-processing -U "research-team"
```

### Use Custom API URL
```bash
tg-show-library-processing -u http://production:8088/
```

## Output Format

The command displays processing records in formatted tables:

```
+----------------+----------------------------------+
| id             | proc_research_001                |
| document-id    | doc_123456789                    |
| time           | 2023-12-15 14:30:22             |
| flow           | research-processing              |
| collection     | research-docs                    |
| tags           | nlp, research, automated         |
+----------------+----------------------------------+

+----------------+----------------------------------+
| id             | proc_batch_002                   |
| document-id    | doc_987654321                    |
| time           | 2023-12-15 14:25:18             |
| flow           | document-analysis                |
| collection     | batch-processed                  |
| tags           | batch, analysis                  |
+----------------+----------------------------------+
```

### Field Details

- **id**: Unique processing record identifier
- **document-id**: ID of the document being processed
- **time**: Timestamp when processing was initiated
- **flow**: Flow instance used for processing
- **collection**: Target collection for processed data
- **tags**: Associated tags for categorization

### Empty Results

If no processing records exist:
```
No processing objects.
```

## Use Cases

### Processing Status Monitoring
```bash
# Monitor active processing jobs
monitor_processing_status() {
  local interval="${1:-30}"  # Default 30 seconds
  
  echo "Monitoring library processing status..."
  echo "Refresh interval: ${interval}s"
  echo "Press Ctrl+C to stop"
  
  while true; do
    clear
    echo "Library Processing Monitor - $(date)"
    echo "===================================="
    
    tg-show-library-processing
    
    echo -e "\nProcessing Summary:"
    processing_count=$(tg-show-library-processing 2>/dev/null | grep -c "| id" || echo "0")
    echo "Active processing jobs: $processing_count"
    
    sleep "$interval"
  done
}

# Start monitoring
monitor_processing_status 15
```

### User Activity Analysis
```bash
# Analyze processing activity by user
analyze_user_processing() {
  local users=("user1" "user2" "user3" "research-team")
  
  echo "Processing Activity Analysis"
  echo "==========================="
  
  for user in "${users[@]}"; do
    echo -e "\n--- User: $user ---"
    
    processing_output=$(tg-show-library-processing -U "$user" 2>/dev/null)
    
    if echo "$processing_output" | grep -q "No processing objects"; then
      echo "No active processing"
    else
      count=$(echo "$processing_output" | grep -c "| id" || echo "0")
      echo "Active processing jobs: $count"
      
      # Show recent jobs
      echo "Recent processing:"
      echo "$processing_output" | grep -E "(id|time|flow)" | head -9
    fi
  done
}

# Run analysis
analyze_user_processing
```

### Processing Queue Management
```bash
# Manage processing queue
manage_processing_queue() {
  echo "Processing Queue Management"
  echo "=========================="
  
  # Show current queue
  echo "Current processing queue:"
  tg-show-library-processing
  
  # Count by flow
  echo -e "\nProcessing jobs by flow:"
  tg-show-library-processing | \
    grep "| flow" | \
    awk '{print $3}' | \
    sort | uniq -c | sort -nr
  
  # Count by collection
  echo -e "\nProcessing jobs by collection:"
  tg-show-library-processing | \
    grep "| collection" | \
    awk '{print $3}' | \
    sort | uniq -c | sort -nr
  
  # Find long-running jobs (would need timestamps comparison)
  echo -e "\nNote: Check timestamps for long-running jobs"
}

# Run queue management
manage_processing_queue
```

### Cleanup and Maintenance
```bash
# Clean up completed processing records
cleanup_processing_records() {
  local user="$1"
  local max_age_days="${2:-7}"  # Default 7 days
  
  echo "Cleaning up processing records older than $max_age_days days for user: $user"
  
  # Get processing records
  processing_output=$(tg-show-library-processing -U "$user")
  
  if echo "$processing_output" | grep -q "No processing objects"; then
    echo "No processing records to clean up"
    return
  fi
  
  # Parse processing records (this is a simplified example)
  echo "$processing_output" | \
    grep "| id" | \
    awk '{print $3}' | \
    while read proc_id; do
      echo "Checking processing record: $proc_id"
      
      # Get the time for this processing record
      proc_time=$(echo "$processing_output" | \
        grep -A10 "$proc_id" | \
        grep "| time" | \
        awk '{print $3 " " $4}')
      
      if [ -n "$proc_time" ]; then
        # Calculate age (this would need proper date comparison)
        echo "Processing record $proc_id from: $proc_time"
        
        # Check if document processing is complete
        if tg-invoke-document-rag -q "test" -U "$user" 2>/dev/null | grep -q "answer"; then
          echo "Document appears to be processed, considering cleanup..."
          # tg-stop-library-processing --id "$proc_id" -U "$user"
        fi
      fi
    done
}

# Clean up old records
cleanup_processing_records "test-user" 3
```

## Advanced Usage

### Processing Performance Analysis
```bash
# Analyze processing performance
analyze_processing_performance() {
  echo "Processing Performance Analysis"
  echo "=============================="
  
  # Get all processing records
  processing_data=$(tg-show-library-processing)
  
  if echo "$processing_data" | grep -q "No processing objects"; then
    echo "No processing data available"
    return
  fi
  
  # Count total processing jobs
  total_jobs=$(echo "$processing_data" | grep -c "| id")
  echo "Total active processing jobs: $total_jobs"
  
  # Analyze by flow type
  echo -e "\nJobs by flow type:"
  echo "$processing_data" | \
    grep "| flow" | \
    awk '{print $3}' | \
    sort | uniq -c | sort -nr | \
    while read count flow; do
      echo "  $flow: $count jobs"
    done
  
  # Analyze by time patterns
  echo -e "\nJobs by hour (last 24h):"
  echo "$processing_data" | \
    grep "| time" | \
    awk '{print $4}' | \
    cut -d: -f1 | \
    sort | uniq -c | sort -k2n | \
    while read count hour; do
      echo "  ${hour}:00: $count jobs"
    done
}

# Run performance analysis
analyze_processing_performance
```

### Cross-User Processing Comparison
```bash
# Compare processing across users
compare_user_processing() {
  local users=("$@")
  
  echo "Cross-User Processing Comparison"
  echo "==============================="
  
  for user in "${users[@]}"; do
    echo -e "\n--- User: $user ---"
    
    processing_data=$(tg-show-library-processing -U "$user" 2>/dev/null)
    
    if echo "$processing_data" | grep -q "No processing objects"; then
      echo "Active jobs: 0"
      echo "Collections: none"
      echo "Flows: none"
    else
      # Count jobs
      job_count=$(echo "$processing_data" | grep -c "| id")
      echo "Active jobs: $job_count"
      
      # List collections
      collections=$(echo "$processing_data" | \
        grep "| collection" | \
        awk '{print $3}' | \
        sort | uniq | tr '\n' ', ' | sed 's/,$//')
      echo "Collections: $collections"
      
      # List flows
      flows=$(echo "$processing_data" | \
        grep "| flow" | \
        awk '{print $3}' | \
        sort | uniq | tr '\n' ', ' | sed 's/,$//')
      echo "Flows: $flows"
    fi
  done
}

# Compare processing for multiple users
compare_user_processing "user1" "user2" "research-team" "admin"
```

### Processing Health Check
```bash
# Health check for processing system
processing_health_check() {
  echo "Library Processing Health Check"
  echo "=============================="
  
  # Check if processing service is responsive
  if tg-show-library-processing > /dev/null 2>&1; then
    echo "✓ Processing service is responsive"
  else
    echo "✗ Processing service is not responsive"
    return 1
  fi
  
  # Get processing statistics
  processing_data=$(tg-show-library-processing 2>/dev/null)
  
  if echo "$processing_data" | grep -q "No processing objects"; then
    echo "ℹ No active processing jobs"
  else
    active_jobs=$(echo "$processing_data" | grep -c "| id")
    echo "ℹ Active processing jobs: $active_jobs"
    
    # Check for stuck jobs (simplified check)
    echo "Recent job timestamps:"
    echo "$processing_data" | \
      grep "| time" | \
      awk '{print $3 " " $4}' | \
      head -5
  fi
  
  # Check flow availability
  echo -e "\nFlow availability check:"
  flows=$(echo "$processing_data" | grep "| flow" | awk '{print $3}' | sort | uniq)
  
  for flow in $flows; do
    if tg-show-flows | grep -q "$flow"; then
      echo "✓ Flow '$flow' is available"
    else
      echo "⚠ Flow '$flow' may not be available"
    fi
  done
  
  echo "Health check completed"
}

# Run health check
processing_health_check
```

### Processing Report Generation
```bash
# Generate comprehensive processing report
generate_processing_report() {
  local output_file="processing_report_$(date +%Y%m%d_%H%M%S).txt"
  
  echo "Generating processing report: $output_file"
  
  cat > "$output_file" << EOF
TrustGraph Library Processing Report
Generated: $(date)
====================================

EOF
  
  # Overall statistics
  echo "OVERVIEW" >> "$output_file"
  echo "--------" >> "$output_file"
  
  processing_data=$(tg-show-library-processing 2>/dev/null)
  
  if echo "$processing_data" | grep -q "No processing objects"; then
    echo "No active processing jobs" >> "$output_file"
  else
    total_jobs=$(echo "$processing_data" | grep -c "| id")
    echo "Total active jobs: $total_jobs" >> "$output_file"
    
    # Flow distribution
    echo -e "\nFLOW DISTRIBUTION" >> "$output_file"
    echo "-----------------" >> "$output_file"
    echo "$processing_data" | \
      grep "| flow" | \
      awk '{print $3}' | \
      sort | uniq -c | sort -nr >> "$output_file"
    
    # Collection distribution
    echo -e "\nCOLLECTION DISTRIBUTION" >> "$output_file"
    echo "-----------------------" >> "$output_file"
    echo "$processing_data" | \
      grep "| collection" | \
      awk '{print $3}' | \
      sort | uniq -c | sort -nr >> "$output_file"
    
    # Recent activity
    echo -e "\nRECENT PROCESSING JOBS" >> "$output_file"
    echo "----------------------" >> "$output_file"
    echo "$processing_data" | head -50 >> "$output_file"
  fi
  
  echo "Report generated: $output_file"
}

# Generate report
generate_processing_report
```

## Integration with Other Commands

### Processing Workflow Management
```bash
# Complete processing workflow
manage_processing_workflow() {
  local user="$1"
  local action="$2"
  
  case "$action" in
    "status")
      echo "Processing status for user: $user"
      tg-show-library-processing -U "$user"
      ;;
    "start-batch")
      echo "Starting batch processing for user: $user"
      tg-show-library-documents -U "$user" | \
        grep "| id" | \
        awk '{print $3}' | \
        while read doc_id; do
          proc_id="batch_$(date +%s)_${doc_id}"
          tg-start-library-processing -d "$doc_id" --id "$proc_id" -U "$user"
        done
      ;;
    "cleanup")
      echo "Cleaning up completed processing for user: $user"
      cleanup_processing_records "$user"
      ;;
    *)
      echo "Usage: manage_processing_workflow <user> <status|start-batch|cleanup>"
      ;;
  esac
}

# Manage workflow for user
manage_processing_workflow "research-team" "status"
```

### Monitoring Integration
```bash
# Integration with system monitoring
processing_metrics_export() {
  local metrics_file="processing_metrics.txt"
  
  # Get processing data
  processing_data=$(tg-show-library-processing 2>/dev/null)
  
  if echo "$processing_data" | grep -q "No processing objects"; then
    active_jobs=0
  else
    active_jobs=$(echo "$processing_data" | grep -c "| id")
  fi
  
  # Export metrics
  echo "trustgraph_library_processing_active_jobs $active_jobs" > "$metrics_file"
  echo "trustgraph_library_processing_timestamp $(date +%s)" >> "$metrics_file"
  
  # Export by flow
  if [ "$active_jobs" -gt 0 ]; then
    echo "$processing_data" | \
      grep "| flow" | \
      awk '{print $3}' | \
      sort | uniq -c | \
      while read count flow; do
        echo "trustgraph_library_processing_jobs_by_flow{flow=\"$flow\"} $count" >> "$metrics_file"
      done
  fi
  
  echo "Metrics exported to: $metrics_file"
}

processing_metrics_export
```

## Error Handling

### API Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Check API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Access denied
```
**Solution**: Verify user permissions for library access.

### User Not Found
```bash
Exception: User not found
```
**Solution**: Check user ID and ensure user exists in the system.

### Service Unavailable
```bash
Exception: Service temporarily unavailable
```
**Solution**: Check TrustGraph service status and try again.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-start-library-processing`](tg-start-library-processing.md) - Start document processing
- [`tg-stop-library-processing`](tg-stop-library-processing.md) - Stop document processing
- [`tg-show-library-documents`](tg-show-library-documents.md) - List library documents
- [`tg-show-flows`](tg-show-flows.md) - List available flows

## API Integration

This command uses the [Library API](../apis/api-librarian.md) to retrieve processing record information.

## Best Practices

1. **Regular Monitoring**: Check processing status regularly
2. **User Filtering**: Use user filtering to focus on relevant processing
3. **Cleanup**: Regularly clean up completed processing records
4. **Performance Tracking**: Monitor processing patterns and performance
5. **Integration**: Integrate with monitoring and alerting systems
6. **Documentation**: Document processing workflows and procedures
7. **Troubleshooting**: Use processing information for issue diagnosis

## Troubleshooting

### No Processing Records
```bash
# Check if library service is running
curl -s http://localhost:8088/api/v1/library/processing

# Verify documents exist
tg-show-library-documents
```

### Stale Processing Records
```bash
# Check for long-running processes
tg-show-library-processing | grep "$(date -d '1 hour ago' '+%Y-%m-%d')"

# Check flow status
tg-show-flows
```

### Performance Issues
```bash
# Check system resources
free -h
df -h

# Monitor API response times
time tg-show-library-processing
```