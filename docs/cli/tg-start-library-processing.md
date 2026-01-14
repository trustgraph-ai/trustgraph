# tg-start-library-processing

Submits a library document for processing through TrustGraph workflows.

## Synopsis

```bash
tg-start-library-processing -d DOCUMENT_ID --id PROCESSING_ID [options]
```

## Description

The `tg-start-library-processing` command initiates processing of a document stored in TrustGraph's document library. This triggers workflows that can extract text, generate embeddings, create knowledge graphs, and enable document search and analysis.

Each processing job is assigned a unique processing ID for tracking and management purposes.

## Options

### Required Arguments

- `-d, --document-id ID`: Document ID from the library to process
- `--id, --processing-id ID`: Unique identifier for this processing job

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User ID for processing context (default: `trustgraph`)
- `-i, --flow-id ID`: Flow instance to use for processing (default: `default`)
- `--collection COLLECTION`: Collection to assign processed data (default: `default`)
- `--tags TAGS`: Comma-separated tags for the processing job

## Examples

### Basic Document Processing
```bash
tg-start-library-processing -d "doc_123456789" --id "proc_001"
```

### Processing with Custom Collection
```bash
tg-start-library-processing \
  -d "research_paper_456" \
  --id "research_proc_001" \
  --collection "research-papers" \
  --tags "nlp,research,2023"
```

### Processing with Specific Flow
```bash
tg-start-library-processing \
  -d "technical_manual" \
  --id "manual_proc_001" \
  -i "document-analysis-flow" \
  -U "technical-team" \
  --collection "technical-docs"
```

### Processing Multiple Documents
```bash
# Process several documents in sequence
documents=("doc_001" "doc_002" "doc_003")
for i in "${!documents[@]}"; do
  doc_id="${documents[$i]}"
  proc_id="batch_proc_$(printf %03d $((i+1)))"
  
  echo "Processing document: $doc_id"
  tg-start-library-processing \
    -d "$doc_id" \
    --id "$proc_id" \
    --collection "batch-processing" \
    --tags "batch,automated"
done
```

## Processing Workflow

### Document Processing Steps
1. **Document Retrieval**: Fetch document from library
2. **Content Extraction**: Extract text and metadata
3. **Text Processing**: Clean and normalize content
4. **Embedding Generation**: Create vector embeddings
5. **Knowledge Extraction**: Generate triples and entities
6. **Index Creation**: Make content searchable

### Processing Types
Different document types may trigger different processing workflows:
- **PDF Documents**: Text extraction, OCR if needed
- **Text Files**: Direct text processing
- **Images**: OCR and image analysis
- **Structured Data**: Schema extraction and mapping

## Use Cases

### Batch Document Processing
```bash
# Process all unprocessed documents
process_all_documents() {
  local collection="$1"
  local batch_id="batch_$(date +%Y%m%d_%H%M%S)"
  
  echo "Starting batch processing for collection: $collection"
  
  # Get all document IDs
  tg-show-library-documents | \
    grep "| id" | \
    awk '{print $3}' | \
    while read -r doc_id; do
      proc_id="${batch_id}_${doc_id}"
      
      echo "Processing document: $doc_id"
      tg-start-library-processing \
        -d "$doc_id" \
        --id "$proc_id" \
        --collection "$collection" \
        --tags "batch,automated,$(date +%Y%m%d)"
      
      # Add delay to avoid overwhelming the system
      sleep 2
    done
}

# Process all documents
process_all_documents "processed-docs"
```

### Department-Specific Processing
```bash
# Process documents by department
process_by_department() {
  local dept="$1"
  local flow="$2"
  
  echo "Processing documents for department: $dept"
  
  # Find documents with department tag
  tg-show-library-documents -U "$dept" | \
    grep "| id" | \
    awk '{print $3}' | \
    while read -r doc_id; do
      proc_id="${dept}_proc_$(date +%s)_${doc_id}"
      
      echo "Processing $dept document: $doc_id"
      tg-start-library-processing \
        -d "$doc_id" \
        --id "$proc_id" \
        -i "$flow" \
        -U "$dept" \
        --collection "${dept}-processed" \
        --tags "$dept,departmental"
    done
}

# Process documents for different departments
process_by_department "research" "research-flow"
process_by_department "finance" "document-flow"
process_by_department "legal" "compliance-flow"
```

### Priority Processing
```bash
# Process high-priority documents first
priority_processing() {
  local priority_tags=("urgent" "high-priority" "critical")
  
  for tag in "${priority_tags[@]}"; do
    echo "Processing $tag documents..."
    
    tg-show-library-documents | \
      grep -B5 -A5 "$tag" | \
      grep "| id" | \
      awk '{print $3}' | \
      while read -r doc_id; do
        proc_id="priority_$(date +%s)_${doc_id}"
        
        echo "Processing priority document: $doc_id"
        tg-start-library-processing \
          -d "$doc_id" \
          --id "$proc_id" \
          --collection "priority-processed" \
          --tags "priority,$tag"
      done
  done
}

priority_processing
```

### Conditional Processing
```bash
# Process documents based on criteria
conditional_processing() {
  local criteria="$1"
  local flow="$2"
  
  echo "Processing documents matching criteria: $criteria"
  
  tg-show-library-documents | \
    grep -B10 -A10 "$criteria" | \
    grep "| id" | \
    awk '{print $3}' | \
    while read -r doc_id; do
      # Check if already processed
      if tg-invoke-document-rag -q "test" 2>/dev/null | grep -q "$doc_id"; then
        echo "Document $doc_id already processed, skipping"
        continue
      fi
      
      proc_id="conditional_$(date +%s)_${doc_id}"
      
      echo "Processing document: $doc_id"
      tg-start-library-processing \
        -d "$doc_id" \
        --id "$proc_id" \
        -i "$flow" \
        --collection "conditional-processed" \
        --tags "conditional,$criteria"
    done
}

# Process technical documents
conditional_processing "technical" "technical-flow"
```

## Advanced Usage

### Processing with Validation
```bash
# Process with pre and post validation
validated_processing() {
  local doc_id="$1"
  local proc_id="$2"
  local collection="$3"
  
  echo "Starting validated processing for: $doc_id"
  
  # Pre-processing validation
  if ! tg-show-library-documents | grep -q "$doc_id"; then
    echo "ERROR: Document $doc_id not found"
    return 1
  fi
  
  # Check if processing ID is unique
  if tg-show-flows | grep -q "$proc_id"; then
    echo "ERROR: Processing ID $proc_id already in use"
    return 1
  fi
  
  # Start processing
  echo "Starting processing..."
  tg-start-library-processing \
    -d "$doc_id" \
    --id "$proc_id" \
    --collection "$collection" \
    --tags "validated,$(date +%Y%m%d)"
  
  # Monitor processing
  echo "Monitoring processing progress..."
  timeout=300  # 5 minutes
  elapsed=0
  interval=10
  
  while [ $elapsed -lt $timeout ]; do
    if tg-invoke-document-rag -q "test" -C "$collection" 2>/dev/null | grep -q "$doc_id"; then
      echo "✓ Processing completed successfully"
      return 0
    fi
    
    echo "Processing in progress... (${elapsed}s elapsed)"
    sleep $interval
    elapsed=$((elapsed + interval))
  done
  
  echo "⚠ Processing timeout reached"
  return 1
}

# Usage
validated_processing "doc_123" "validated_proc_001" "validated-docs"
```

### Parallel Processing with Limits
```bash
# Process multiple documents in parallel with concurrency limits
parallel_processing() {
  local doc_list=("$@")
  local max_concurrent=5
  local current_jobs=0
  
  echo "Processing ${#doc_list[@]} documents with max $max_concurrent concurrent jobs"
  
  for doc_id in "${doc_list[@]}"; do
    # Wait if max concurrent jobs reached
    while [ $current_jobs -ge $max_concurrent ]; do
      wait -n  # Wait for any job to complete
      current_jobs=$((current_jobs - 1))
    done
    
    # Start processing in background
    (
      proc_id="parallel_$(date +%s)_${doc_id}"
      echo "Starting processing: $doc_id"
      
      tg-start-library-processing \
        -d "$doc_id" \
        --id "$proc_id" \
        --collection "parallel-processed" \
        --tags "parallel,batch"
      
      echo "Completed processing: $doc_id"
    ) &
    
    current_jobs=$((current_jobs + 1))
  done
  
  # Wait for all remaining jobs
  wait
  echo "All processing jobs completed"
}

# Get document list and process in parallel
doc_list=($(tg-show-library-documents | grep "| id" | awk '{print $3}'))
parallel_processing "${doc_list[@]}"
```

### Processing with Retry Logic
```bash
# Process with automatic retry on failure
processing_with_retry() {
  local doc_id="$1"
  local proc_id="$2"
  local max_retries=3
  local retry_delay=30
  
  for attempt in $(seq 1 $max_retries); do
    echo "Processing attempt $attempt/$max_retries for document: $doc_id"
    
    if tg-start-library-processing \
        -d "$doc_id" \
        --id "${proc_id}_attempt_${attempt}" \
        --collection "retry-processed" \
        --tags "retry,attempt_$attempt"; then
      
      # Wait and check if processing succeeded
      sleep $retry_delay
      
      if tg-invoke-document-rag -q "test" 2>/dev/null | grep -q "$doc_id"; then
        echo "✓ Processing succeeded on attempt $attempt"
        return 0
      else
        echo "Processing started but content not yet accessible"
      fi
    else
      echo "✗ Processing failed on attempt $attempt"
    fi
    
    if [ $attempt -lt $max_retries ]; then
      echo "Retrying in ${retry_delay}s..."
      sleep $retry_delay
    fi
  done
  
  echo "✗ Processing failed after $max_retries attempts"
  return 1
}

# Usage
processing_with_retry "doc_123" "retry_proc_001"
```

### Configuration-Driven Processing
```bash
# Process documents based on configuration file
config_driven_processing() {
  local config_file="$1"
  
  if [ ! -f "$config_file" ]; then
    echo "Configuration file not found: $config_file"
    return 1
  fi
  
  echo "Processing documents based on configuration: $config_file"
  
  # Example configuration format:
  # doc_id,flow_id,collection,tags
  # doc_123,research-flow,research-docs,nlp research
  
  while IFS=',' read -r doc_id flow_id collection tags; do
    # Skip header line
    if [ "$doc_id" = "doc_id" ]; then
      continue
    fi
    
    proc_id="config_$(date +%s)_${doc_id}"
    
    echo "Processing: $doc_id -> $collection (flow: $flow_id)"
    
    tg-start-library-processing \
      -d "$doc_id" \
      --id "$proc_id" \
      -i "$flow_id" \
      --collection "$collection" \
      --tags "$tags"
    
  done < "$config_file"
}

# Create example configuration
cat > processing_config.csv << EOF
doc_id,flow_id,collection,tags
doc_123,research-flow,research-docs,nlp research
doc_456,finance-flow,finance-docs,financial quarterly
doc_789,general-flow,general-docs,general processing
EOF

# Process based on configuration
config_driven_processing "processing_config.csv"
```

## Error Handling

### Document Not Found
```bash
Exception: Document not found
```
**Solution**: Verify document exists with `tg-show-library-documents`.

### Processing ID Conflict
```bash
Exception: Processing ID already exists
```
**Solution**: Use a unique processing ID or check existing jobs with `tg-show-flows`.

### Flow Not Found
```bash
Exception: Flow instance not found
```
**Solution**: Verify flow exists with `tg-show-flows` or `tg-show-flow-blueprints`.

### Insufficient Resources
```bash
Exception: Processing queue full
```
**Solution**: Wait for current jobs to complete or scale processing resources.

## Monitoring and Management

### Processing Status
```bash
# Monitor processing progress
monitor_processing() {
  local proc_id="$1"
  local timeout="${2:-300}"  # 5 minutes default
  
  echo "Monitoring processing: $proc_id"
  
  elapsed=0
  interval=10
  
  while [ $elapsed -lt $timeout ]; do
    # Check if processing is active
    if tg-show-flows | grep -q "$proc_id"; then
      echo "Processing active... (${elapsed}s elapsed)"
    else
      echo "Processing completed or stopped"
      break
    fi
    
    sleep $interval
    elapsed=$((elapsed + interval))
  done
  
  if [ $elapsed -ge $timeout ]; then
    echo "Monitoring timeout reached"
  fi
}

# Monitor specific processing job
monitor_processing "proc_001" 600
```

### Batch Monitoring
```bash
# Monitor multiple processing jobs
monitor_batch() {
  local proc_pattern="$1"
  
  echo "Monitoring batch processing: $proc_pattern"
  
  while true; do
    active_jobs=$(tg-show-flows | grep -c "$proc_pattern" || echo "0")
    
    if [ "$active_jobs" -eq 0 ]; then
      echo "All batch processing jobs completed"
      break
    fi
    
    echo "Active jobs: $active_jobs"
    sleep 30
  done
}

# Monitor batch processing
monitor_batch "batch_proc_"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-library-documents`](tg-show-library-documents.md) - List available documents
- [`tg-stop-library-processing`](tg-stop-library-processing.md) - Stop processing jobs
- [`tg-show-flows`](tg-show-flows.md) - Monitor processing flows
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Query processed documents

## API Integration

This command uses the [Library API](../apis/api-librarian.md) to initiate document processing workflows.

## Best Practices

1. **Unique IDs**: Always use unique processing IDs to avoid conflicts
2. **Resource Management**: Monitor system resources during batch processing
3. **Error Handling**: Implement retry logic for robust processing
4. **Monitoring**: Track processing progress and completion
5. **Collection Organization**: Use meaningful collection names
6. **Tagging**: Apply consistent tagging for better organization
7. **Documentation**: Document processing procedures and configurations

## Troubleshooting

### Processing Not Starting
```bash
# Check document exists
tg-show-library-documents | grep "document-id"

# Check flow is available
tg-show-flows | grep "flow-id"

# Check system resources
free -h
df -h
```

### Slow Processing
```bash
# Check processing queue
tg-show-flows | grep processing | wc -l

# Monitor system load
top
htop
```

### Processing Failures
```bash
# Check processing logs
# (Log location depends on TrustGraph configuration)

# Retry with different flow
tg-start-library-processing -d "doc-id" --id "retry-proc" -i "alternative-flow"
```