# tg-save-doc-embeds

Saves document embeddings from TrustGraph processing streams to MessagePack format files.

## Synopsis

```bash
tg-save-doc-embeds -o OUTPUT_FILE [options]
```

## Description

The `tg-save-doc-embeds` command connects to TrustGraph's document embeddings export stream and saves the embeddings to a file in MessagePack format. This is useful for creating backups of document embeddings, exporting data for analysis, or preparing data for migration between systems.

The command should typically be started before document processing begins to capture all embeddings as they are generated.

## Options

### Required Arguments

- `-o, --output-file FILE`: Output file for saved embeddings

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_API` or `http://localhost:8088/`)
- `-f, --flow-id ID`: Flow instance ID to monitor (default: `default`)
- `--format FORMAT`: Output format - `msgpack` or `json` (default: `msgpack`)
- `--user USER`: Filter by user ID (default: no filter)
- `--collection COLLECTION`: Filter by collection ID (default: no filter)

## Examples

### Basic Document Embeddings Export
```bash
tg-save-doc-embeds -o document-embeddings.msgpack
```

### Export from Specific Flow
```bash
tg-save-doc-embeds \
  -o research-embeddings.msgpack \
  -f "research-processing-flow"
```

### Filter by User and Collection
```bash
tg-save-doc-embeds \
  -o filtered-embeddings.msgpack \
  --user "research-team" \
  --collection "research-docs"
```

### Export to JSON Format
```bash
tg-save-doc-embeds \
  -o embeddings.json \
  --format json
```

### Production Backup
```bash
tg-save-doc-embeds \
  -o "backup-$(date +%Y%m%d-%H%M%S).msgpack" \
  -u https://production-api.company.com/ \
  -f "production-flow"
```

## Output Format

### MessagePack Structure
Document embeddings are saved as MessagePack records:

```json
["de", {
  "m": {
    "i": "document-id",
    "m": [{"metadata": "objects"}],
    "u": "user-id",
    "c": "collection-id"
  },
  "c": [{
    "c": "text chunk content",
    "v": [0.1, 0.2, 0.3, ...]
  }]
}]
```

### Components
- **Record Type**: `"de"` indicates document embeddings
- **Metadata** (`m`): Document information and context
- **Chunks** (`c`): Text chunks with their vector embeddings

## Use Cases

### Backup Creation
```bash
# Create regular backups of document embeddings
create_embeddings_backup() {
  local backup_dir="embeddings-backups"
  local timestamp=$(date +%Y%m%d_%H%M%S)
  local backup_file="$backup_dir/embeddings-$timestamp.msgpack"
  
  mkdir -p "$backup_dir"
  
  echo "Creating embeddings backup: $backup_file"
  
  # Start backup process
  tg-save-doc-embeds -o "$backup_file" &
  save_pid=$!
  
  echo "Backup process started (PID: $save_pid)"
  echo "To stop: kill $save_pid"
  echo "Backup file: $backup_file"
  
  # Optionally wait for a specific duration
  # sleep 3600  # Run for 1 hour
  # kill $save_pid
}

# Create backup
create_embeddings_backup
```

### Data Migration Preparation
```bash
# Prepare embeddings for migration
prepare_migration_data() {
  local source_env="$1"
  local collection="$2"
  local migration_file="migration-$(date +%Y%m%d).msgpack"
  
  echo "Preparing migration data from: $source_env"
  echo "Collection: $collection"
  
  # Export embeddings from source
  tg-save-doc-embeds \
    -o "$migration_file" \
    -u "http://$source_env:8088/" \
    --collection "$collection" &
  
  export_pid=$!
  
  # Let it run for specified time to capture data
  echo "Capturing embeddings for migration..."
  echo "Process PID: $export_pid"
  
  # In practice, you'd run this for the duration needed
  # sleep 1800  # 30 minutes
  # kill $export_pid
  
  echo "Migration data will be saved to: $migration_file"
}

# Prepare migration from dev to production
prepare_migration_data "dev-server" "processed-docs"
```

### Continuous Export
```bash
# Continuous embeddings export with rotation
continuous_export() {
  local output_dir="continuous-exports"
  local rotation_hours=24
  local file_prefix="embeddings"
  
  mkdir -p "$output_dir"
  
  while true; do
    timestamp=$(date +%Y%m%d_%H%M%S)
    output_file="$output_dir/${file_prefix}-${timestamp}.msgpack"
    
    echo "Starting export to: $output_file"
    
    # Start export for specified duration
    timeout ${rotation_hours}h tg-save-doc-embeds -o "$output_file"
    
    # Compress completed file
    gzip "$output_file"
    
    echo "Export completed and compressed: ${output_file}.gz"
    
    # Optional: clean up old files
    find "$output_dir" -name "*.msgpack.gz" -mtime +30 -delete
    
    # Brief pause before next rotation
    sleep 60
  done
}

# Start continuous export (run in background)
continuous_export &
```

### Analysis and Research
```bash
# Export embeddings for research analysis
export_for_research() {
  local research_topic="$1"
  local output_file="research-${research_topic}-$(date +%Y%m%d).msgpack"
  
  echo "Exporting embeddings for research: $research_topic"
  
  # Start export with filtering
  tg-save-doc-embeds \
    -o "$output_file" \
    --collection "$research_topic" &
  
  export_pid=$!
  
  echo "Research export started (PID: $export_pid)"
  echo "Output: $output_file"
  
  # Create analysis script
  cat > "analyze-${research_topic}.sh" << EOF
#!/bin/bash
# Analysis script for $research_topic embeddings

echo "Analyzing $research_topic embeddings..."

# Basic statistics
echo "=== Basic Statistics ==="
tg-dump-msgpack -i "$output_file" --summary

# Detailed analysis
echo "=== Detailed Analysis ==="
tg-dump-msgpack -i "$output_file" | head -10

echo "Analysis complete for $research_topic"
EOF
  
  chmod +x "analyze-${research_topic}.sh"
  echo "Analysis script created: analyze-${research_topic}.sh"
}

# Export for different research topics
export_for_research "cybersecurity"
export_for_research "climate-change"
```

## Advanced Usage

### Selective Export
```bash
# Export embeddings with multiple filters
selective_export() {
  local users=("user1" "user2" "user3")
  local collections=("docs1" "docs2")
  
  for user in "${users[@]}"; do
    for collection in "${collections[@]}"; do
      output_file="embeddings-${user}-${collection}.msgpack"
      
      echo "Exporting for user: $user, collection: $collection"
      
      tg-save-doc-embeds \
        -o "$output_file" \
        --user "$user" \
        --collection "$collection" &
      
      # Store PID for later management
      echo $! > "${output_file}.pid"
    done
  done
  
  echo "All selective exports started"
}
```

### Monitoring and Statistics
```bash
# Monitor export progress with statistics
monitor_export() {
  local output_file="$1"
  local pid_file="${output_file}.pid"
  
  if [ ! -f "$pid_file" ]; then
    echo "PID file not found: $pid_file"
    return 1
  fi
  
  local export_pid=$(cat "$pid_file")
  
  echo "Monitoring export (PID: $export_pid)..."
  echo "Output file: $output_file"
  
  while kill -0 "$export_pid" 2>/dev/null; do
    if [ -f "$output_file" ]; then
      file_size=$(stat -c%s "$output_file" 2>/dev/null || echo "0")
      human_size=$(numfmt --to=iec-i --suffix=B "$file_size")
      
      # Try to count embeddings
      embedding_count=$(tg-dump-msgpack -i "$output_file" 2>/dev/null | grep -c '^\["de"' || echo "0")
      
      echo "File size: $human_size, Embeddings: $embedding_count"
    else
      echo "Output file not yet created..."
    fi
    
    sleep 30
  done
  
  echo "Export process completed"
  rm "$pid_file"
}

# Start export and monitor
tg-save-doc-embeds -o "monitored-export.msgpack" &
echo $! > "monitored-export.msgpack.pid"
monitor_export "monitored-export.msgpack"
```

### Export Validation
```bash
# Validate exported embeddings
validate_export() {
  local export_file="$1"
  
  echo "Validating export file: $export_file"
  
  # Check file exists and has content
  if [ ! -s "$export_file" ]; then
    echo "✗ Export file is empty or missing"
    return 1
  fi
  
  # Check MessagePack format
  if tg-dump-msgpack -i "$export_file" --summary > /dev/null 2>&1; then
    echo "✓ Valid MessagePack format"
  else
    echo "✗ Invalid MessagePack format"
    return 1
  fi
  
  # Check for document embeddings
  embedding_count=$(tg-dump-msgpack -i "$export_file" | grep -c '^\["de"' || echo "0")
  
  if [ "$embedding_count" -gt 0 ]; then
    echo "✓ Contains $embedding_count document embeddings"
  else
    echo "✗ No document embeddings found"
    return 1
  fi
  
  # Get vector dimension information
  summary=$(tg-dump-msgpack -i "$export_file" --summary)
  if echo "$summary" | grep -q "Vector dimension:"; then
    dimension=$(echo "$summary" | grep "Vector dimension:" | awk '{print $3}')
    echo "✓ Vector dimension: $dimension"
  else
    echo "⚠ Could not determine vector dimension"
  fi
  
  echo "Validation completed successfully"
}
```

### Export Scheduling
```bash
# Scheduled export with cron-like functionality
schedule_export() {
  local schedule="$1"  # e.g., "daily", "hourly", "weekly"
  local output_prefix="$2"
  
  case "$schedule" in
    "hourly")
      interval=3600
      ;;
    "daily")
      interval=86400
      ;;
    "weekly")
      interval=604800
      ;;
    *)
      echo "Invalid schedule: $schedule"
      return 1
      ;;
  esac
  
  echo "Starting $schedule exports with prefix: $output_prefix"
  
  while true; do
    timestamp=$(date +%Y%m%d_%H%M%S)
    output_file="${output_prefix}-${timestamp}.msgpack"
    
    echo "Starting scheduled export: $output_file"
    
    # Run export for the scheduled interval
    timeout ${interval}s tg-save-doc-embeds -o "$output_file"
    
    # Validate and compress
    if validate_export "$output_file"; then
      gzip "$output_file"
      echo "✓ Export completed and compressed: ${output_file}.gz"
    else
      echo "✗ Export validation failed: $output_file"
      mv "$output_file" "${output_file}.failed"
    fi
    
    # Brief pause before next cycle
    sleep 60
  done
}

# Start daily scheduled exports
schedule_export "daily" "daily-embeddings" &
```

## Performance Considerations

### Memory Management
```bash
# Monitor memory usage during export
monitor_memory_export() {
  local output_file="$1"
  
  # Start export
  tg-save-doc-embeds -o "$output_file" &
  export_pid=$!
  
  echo "Monitoring memory usage for export (PID: $export_pid)..."
  
  while kill -0 "$export_pid" 2>/dev/null; do
    memory_usage=$(ps -p "$export_pid" -o rss= 2>/dev/null | awk '{print $1/1024}')
    
    if [ -n "$memory_usage" ]; then
      echo "Memory usage: ${memory_usage}MB"
    fi
    
    sleep 10
  done
  
  echo "Export completed"
}
```

### Network Optimization
```bash
# Optimize for network conditions
network_optimized_export() {
  local output_file="$1"
  local api_url="$2"
  
  echo "Starting network-optimized export..."
  
  # Use compression and buffering
  tg-save-doc-embeds \
    -o "$output_file" \
    -u "$api_url" \
    --format msgpack &  # MessagePack is more compact than JSON
  
  export_pid=$!
  
  # Monitor network usage
  echo "Monitoring export (PID: $export_pid)..."
  
  while kill -0 "$export_pid" 2>/dev/null; do
    # Monitor network connections
    connections=$(netstat -an | grep ":8088" | wc -l)
    echo "Active connections: $connections"
    sleep 30
  done
}
```

## Error Handling

### Connection Issues
```bash
Exception: WebSocket connection failed
```
**Solution**: Check API URL and ensure TrustGraph WebSocket service is running.

### Disk Space Issues
```bash
Exception: No space left on device
```
**Solution**: Free up disk space or use a different output location.

### Permission Errors
```bash
Exception: Permission denied
```
**Solution**: Check write permissions for the output file location.

### Memory Issues
```bash
MemoryError: Unable to allocate memory
```
**Solution**: Monitor memory usage and consider using smaller export windows.

## Integration with Other Commands

### Complete Backup Workflow
```bash
# Complete backup and restore workflow
backup_restore_workflow() {
  local backup_file="embeddings-backup.msgpack"
  
  echo "=== Backup Phase ==="
  
  # Create backup
  tg-save-doc-embeds -o "$backup_file" &
  backup_pid=$!
  
  # Let it run for a while
  sleep 300  # 5 minutes
  kill $backup_pid
  
  echo "Backup created: $backup_file"
  
  # Validate backup
  validate_export "$backup_file"
  
  echo "=== Restore Phase ==="
  
  # Restore from backup (to different collection)
  tg-load-doc-embeds -i "$backup_file" --collection "restored"
  
  echo "Backup and restore workflow completed"
}
```

### Analysis Pipeline
```bash
# Export and analyze embeddings
export_analyze_pipeline() {
  local topic="$1"
  local export_file="analysis-${topic}.msgpack"
  
  echo "Starting export and analysis pipeline for: $topic"
  
  # Export embeddings
  tg-save-doc-embeds \
    -o "$export_file" \
    --collection "$topic" &
  
  export_pid=$!
  
  # Run for analysis duration
  sleep 600  # 10 minutes
  kill $export_pid
  
  # Analyze exported data
  echo "Analyzing exported embeddings..."
  tg-dump-msgpack -i "$export_file" --summary
  
  # Count embeddings by user
  echo "Embeddings by user:"
  tg-dump-msgpack -i "$export_file" | \
    jq -r '.[1].m.u' | \
    sort | uniq -c
  
  echo "Analysis pipeline completed"
}
```

## Environment Variables

- `TRUSTGRAPH_API`: Default API URL

## Related Commands

- [`tg-load-doc-embeds`](tg-load-doc-embeds.md) - Load document embeddings from files
- [`tg-dump-msgpack`](tg-dump-msgpack.md) - Analyze MessagePack files
- [`tg-show-flows`](tg-show-flows.md) - List available flows for monitoring

## API Integration

This command uses TrustGraph's WebSocket API for document embeddings export, specifically the `/api/v1/flow/{flow-id}/export/document-embeddings` endpoint.

## Best Practices

1. **Start Early**: Begin export before processing starts to capture all data
2. **Monitoring**: Monitor export progress and file sizes
3. **Validation**: Always validate exported files
4. **Compression**: Use compression for long-term storage
5. **Rotation**: Implement file rotation for continuous exports
6. **Backup**: Keep multiple backup copies in different locations
7. **Documentation**: Document export schedules and procedures

## Troubleshooting

### No Data Captured
```bash
# Check if processing is generating embeddings
tg-show-flows | grep processing

# Verify WebSocket connection
netstat -an | grep :8088
```

### Large File Issues
```bash
# Monitor file growth
watch -n 5 'ls -lh *.msgpack'

# Check available disk space
df -h
```

### Process Management
```bash
# List running export processes
ps aux | grep tg-save-doc-embeds

# Kill stuck processes
pkill -f tg-save-doc-embeds
```