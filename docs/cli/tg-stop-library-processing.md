# tg-stop-library-processing

Removes a library document processing record from TrustGraph.

## Synopsis

```bash
tg-stop-library-processing --id PROCESSING_ID [options]
```

## Description

The `tg-stop-library-processing` command removes a document processing record from TrustGraph's library processing system. This command removes the processing record but **does not stop in-flight processing** that may already be running.

This is primarily used for cleaning up processing records, managing processing queues, and maintaining processing history.

## Options

### Required Arguments

- `--id, --processing-id ID`: Processing ID to remove

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User ID (default: `trustgraph`)

## Examples

### Remove Single Processing Record
```bash
tg-stop-library-processing --id "proc_123456789"
```

### Remove with Custom User
```bash
tg-stop-library-processing --id "research_proc_001" -U "research-team"
```

### Remove with Custom API URL
```bash
tg-stop-library-processing --id "proc_555" -u http://staging:8088/
```

## Important Limitations

### Processing Record vs Active Processing
This command only removes the **processing record** and does not:
- Stop currently running processing jobs
- Cancel in-flight document analysis
- Interrupt active workflows

### What It Does
- Removes processing metadata from library
- Cleans up processing history
- Allows reuse of processing IDs
- Maintains processing queue hygiene

### What It Doesn't Do
- Stop active processing threads
- Cancel running analysis jobs
- Interrupt flow execution
- Free up computational resources immediately

## Use Cases

### Cleanup Failed Processing Records
```bash
# Remove failed processing records
failed_processes=("proc_failed_001" "proc_error_002" "proc_timeout_003")
for proc_id in "${failed_processes[@]}"; do
  echo "Removing failed processing record: $proc_id"
  tg-stop-library-processing --id "$proc_id"
done
```

### Batch Cleanup
```bash
# Clean up all processing records for a specific pattern
cleanup_batch_processing() {
  local pattern="$1"
  
  echo "Cleaning up processing records matching: $pattern"
  
  # This would require a way to list processing records
  # For now, use known processing IDs
  tg-show-flows | \
    grep "$pattern" | \
    awk '{print $1}' | \
    while read proc_id; do
      echo "Removing processing record: $proc_id"
      tg-stop-library-processing --id "$proc_id"
    done
}

# Clean up old batch processing records
cleanup_batch_processing "batch_proc_"
```

### User-Specific Cleanup
```bash
# Clean up processing records for specific user
cleanup_user_processing() {
  local user="$1"
  
  echo "Cleaning up processing records for user: $user"
  
  # Note: This assumes you have a way to list processing records by user
  # Implementation would depend on available APIs
  
  # Example with known processing IDs
  user_processes=("${user}_proc_001" "${user}_proc_002" "${user}_proc_003")
  
  for proc_id in "${user_processes[@]}"; do
    echo "Removing processing record: $proc_id"
    tg-stop-library-processing --id "$proc_id" -U "$user"
  done
}

# Clean up for specific user
cleanup_user_processing "temp-user"
```

### Age-Based Cleanup
```bash
# Clean up old processing records
cleanup_old_processing() {
  local days_old="$1"
  
  echo "Cleaning up processing records older than $days_old days"
  
  # This would require timestamp information from processing records
  # Implementation depends on available metadata
  
  cutoff_date=$(date -d "$days_old days ago" +"%Y%m%d")
  
  # Example with date-pattern processing IDs
  # proc_20231215_001, proc_20231214_002, etc.
  
  for proc_id in proc_*; do
    if [[ "$proc_id" =~ proc_([0-9]{8})_ ]]; then
      proc_date="${BASH_REMATCH[1]}"
      
      if [[ "$proc_date" < "$cutoff_date" ]]; then
        echo "Removing old processing record: $proc_id"
        tg-stop-library-processing --id "$proc_id"
      fi
    fi
  done
}

# Clean up processing records older than 30 days
cleanup_old_processing 30
```

## Safe Processing Management

### Before Removing Processing Records
```bash
# Check if processing is actually complete before cleanup
safe_processing_cleanup() {
  local proc_id="$1"
  local doc_id="$2"
  
  echo "Safe cleanup for processing: $proc_id"
  
  # Check if document is accessible (processing likely complete)
  if tg-invoke-document-rag -q "test" 2>/dev/null | grep -q "$doc_id"; then
    echo "Document $doc_id is accessible, safe to remove processing record"
    tg-stop-library-processing --id "$proc_id"
    echo "Processing record removed: $proc_id"
  else
    echo "Document $doc_id not yet accessible, processing may still be active"
    echo "Skipping removal of processing record: $proc_id"
  fi
}

# Usage
safe_processing_cleanup "proc_001" "doc_123"
```

### Verification Before Cleanup
```bash
# Verify processing completion before removing records
verify_and_cleanup() {
  local proc_id="$1"
  local collection="$2"
  
  echo "Verifying processing completion for: $proc_id"
  
  # Check if processing is still active in flows
  if tg-show-flows | grep -q "$proc_id"; then
    echo "Processing $proc_id is still active, not removing record"
    return 1
  fi
  
  # Additional verification could include:
  # - Checking if document content is available
  # - Verifying embeddings are generated
  # - Confirming knowledge graph updates
  
  echo "Processing appears complete, removing record"
  tg-stop-library-processing --id "$proc_id"
  
  echo "Processing record removed: $proc_id"
}

# Usage
verify_and_cleanup "proc_001" "research-docs"
```

## Advanced Usage

### Conditional Cleanup
```bash
# Clean up processing records based on success criteria
conditional_cleanup() {
  local proc_id="$1"
  local doc_id="$2"
  local collection="$3"
  
  echo "Conditional cleanup for: $proc_id"
  
  # Test if document is queryable (indicates successful processing)
  test_query="What is this document about?"
  
  if result=$(tg-invoke-document-rag -q "$test_query" -C "$collection" 2>/dev/null); then
    if echo "$result" | grep -q "answer"; then
      echo "✓ Document is queryable, processing successful"
      tg-stop-library-processing --id "$proc_id"
      echo "Processing record cleaned up: $proc_id"
    else
      echo "⚠ Document query returned no answer, processing may be incomplete"
      echo "Keeping processing record: $proc_id"
    fi
  else
    echo "✗ Document query failed, processing incomplete or failed"
    echo "Keeping processing record: $proc_id"
  fi
}

# Usage
conditional_cleanup "proc_001" "doc_123" "research-docs"
```

### Bulk Cleanup with Verification
```bash
# Bulk cleanup with individual verification
bulk_verified_cleanup() {
  local proc_pattern="$1"
  local collection="$2"
  
  echo "Bulk cleanup with verification for pattern: $proc_pattern"
  
  # Get list of processing IDs (this would need appropriate API)
  # For now, use example pattern
  
  for proc_id in proc_batch_*; do
    if [[ "$proc_id" =~ $proc_pattern ]]; then
      echo "Checking processing: $proc_id"
      
      # Extract document ID from processing ID (example pattern)
      if [[ "$proc_id" =~ _([^_]+)$ ]]; then
        doc_id="${BASH_REMATCH[1]}"
        
        # Verify document is accessible
        if tg-invoke-document-rag -q "test" -C "$collection" 2>/dev/null | grep -q "$doc_id"; then
          echo "✓ Verified: $proc_id"
          tg-stop-library-processing --id "$proc_id"
        else
          echo "⚠ Unverified: $proc_id"
        fi
      else
        echo "? Unknown pattern: $proc_id"
      fi
    fi
  done
}

# Usage
bulk_verified_cleanup "batch_" "processed-docs"
```

### Processing Record Maintenance
```bash
# Maintain processing record hygiene
maintain_processing_records() {
  local max_records="$1"
  
  echo "Maintaining processing records (max: $max_records)"
  
  # This would require an API to list and count processing records
  # For now, demonstrate the concept
  
  # Count current processing records (placeholder)
  current_count=150  # Would get this from API
  
  if [ "$current_count" -gt "$max_records" ]; then
    excess=$((current_count - max_records))
    echo "Found $current_count records, removing $excess oldest"
    
    # Remove oldest processing records
    # This would require timestamp information
    echo "Would remove $excess oldest processing records"
    
    # Example implementation:
    # oldest_records=($(get_oldest_processing_records $excess))
    # for proc_id in "${oldest_records[@]}"; do
    #   tg-stop-library-processing --id "$proc_id"
    # done
  else
    echo "Processing record count within limits: $current_count"
  fi
}

# Maintain maximum 100 processing records
maintain_processing_records 100
```

## Error Handling

### Processing ID Not Found
```bash
Exception: Processing ID not found
```
**Solution**: Verify processing ID exists and check spelling.

### Processing Still Active
```bash
Exception: Cannot remove active processing record
```
**Solution**: Wait for processing to complete or verify if processing is actually active.

### Permission Errors
```bash
Exception: Access denied
```
**Solution**: Check user permissions and processing record ownership.

### API Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Check API URL and ensure TrustGraph is running.

## Monitoring and Verification

### Processing Record Status
```bash
# Check processing record status before removal
check_processing_status() {
  local proc_id="$1"
  
  echo "Checking status of processing: $proc_id"
  
  # Check if processing is in active flows
  if tg-show-flows | grep -q "$proc_id"; then
    echo "Status: ACTIVE - Processing is currently running"
    return 1
  else
    echo "Status: INACTIVE - Processing not found in active flows"
    return 0
  fi
}

# Usage
if check_processing_status "proc_001"; then
  echo "Safe to remove processing record"
  tg-stop-library-processing --id "proc_001"
else
  echo "Processing still active, not removing record"
fi
```

### Cleanup Verification
```bash
# Verify successful removal
verify_removal() {
  local proc_id="$1"
  
  echo "Verifying removal of processing record: $proc_id"
  
  # Check if processing record still exists
  # This would require an API to query processing records
  
  if tg-show-flows | grep -q "$proc_id"; then
    echo "✗ Processing record still exists"
    return 1
  else
    echo "✓ Processing record successfully removed"
    return 0
  fi
}

# Usage
tg-stop-library-processing --id "proc_001"
verify_removal "proc_001"
```

## Integration with Processing Workflow

### Complete Processing Lifecycle
```bash
# Complete processing lifecycle management
processing_lifecycle() {
  local doc_id="$1"
  local proc_id="$2"
  local collection="$3"
  
  echo "Managing complete processing lifecycle"
  echo "Document: $doc_id"
  echo "Processing: $proc_id"
  echo "Collection: $collection"
  
  # 1. Start processing
  echo "1. Starting processing..."
  tg-start-library-processing \
    -d "$doc_id" \
    --id "$proc_id" \
    --collection "$collection"
  
  # 2. Monitor processing
  echo "2. Monitoring processing..."
  timeout=300
  elapsed=0
  
  while [ $elapsed -lt $timeout ]; do
    if tg-invoke-document-rag -q "test" -C "$collection" 2>/dev/null | grep -q "$doc_id"; then
      echo "✓ Processing completed"
      break
    fi
    
    sleep 10
    elapsed=$((elapsed + 10))
  done
  
  # 3. Verify completion
  echo "3. Verifying completion..."
  if tg-invoke-document-rag -q "What is this document?" -C "$collection" 2>/dev/null; then
    echo "✓ Document is queryable"
    
    # 4. Clean up processing record
    echo "4. Cleaning up processing record..."
    tg-stop-library-processing --id "$proc_id"
    echo "✓ Processing record removed"
  else
    echo "✗ Processing verification failed"
    echo "Keeping processing record for investigation"
  fi
}

# Usage
processing_lifecycle "doc_123" "proc_test_001" "test-collection"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-start-library-processing`](tg-start-library-processing.md) - Start document processing
- [`tg-show-library-documents`](tg-show-library-documents.md) - List library documents
- [`tg-show-flows`](tg-show-flows.md) - Monitor active processing flows
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Verify processed documents

## API Integration

This command uses the [Library API](../apis/api-librarian.md) to remove processing records from the document processing system.

## Best Practices

1. **Verify Completion**: Ensure processing is complete before removing records
2. **Check Dependencies**: Verify no other processes depend on the processing record
3. **Gradual Cleanup**: Remove processing records gradually to avoid system impact
4. **Monitor Impact**: Watch for any effects of record removal on system performance
5. **Documentation**: Log processing record removals for audit purposes
6. **Backup**: Consider backing up processing metadata before removal
7. **Testing**: Test cleanup procedures in non-production environments

## Troubleshooting

### Record Won't Remove
```bash
# Check if processing is actually complete
tg-show-flows | grep "processing-id"

# Verify API connectivity
curl -s "$TRUSTGRAPH_URL/api/v1/library/processing" > /dev/null
```

### Unexpected Behavior After Removal
```bash
# Check if document is still accessible
tg-invoke-document-rag -q "test" -C "collection"

# Verify document processing status
tg-show-library-documents | grep "document-id"
```

### Permission Issues
```bash
# Check user permissions
tg-show-library-documents -U "your-user"

# Verify processing record ownership
```