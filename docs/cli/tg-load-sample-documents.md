# tg-load-sample-documents

Loads predefined sample documents into TrustGraph library for testing and demonstration purposes.

## Synopsis

```bash
tg-load-sample-documents [options]
```

## Description

The `tg-load-sample-documents` command loads a curated set of sample documents into TrustGraph's document library. These documents include academic papers, government reports, and reference materials that demonstrate TrustGraph's capabilities and provide data for testing and evaluation.

The command downloads documents from public sources and adds them to the library with comprehensive metadata including RDF triples for semantic relationships.

## Options

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User ID for document ownership (default: `trustgraph`)

## Examples

### Basic Loading
```bash
tg-load-sample-documents
```

### Load with Custom User
```bash
tg-load-sample-documents -U "demo-user"
```

### Load to Custom Environment
```bash
tg-load-sample-documents -u http://demo.trustgraph.ai:8088/
```

## Sample Documents

The command loads the following sample documents:

### 1. NASA Challenger Report
- **Title**: Report of the Presidential Commission on the Space Shuttle Challenger Accident, Volume 1
- **Topics**: Safety engineering, space shuttle, NASA
- **Format**: PDF
- **Source**: NASA Technical Reports Server
- **Use Case**: Demonstrates technical document processing and safety analysis

### 2. Old Icelandic Dictionary
- **Title**: A Concise Dictionary of Old Icelandic
- **Topics**: Language, linguistics, Old Norse, grammar
- **Format**: PDF
- **Publication**: 1910, Clarendon Press
- **Use Case**: Historical document processing and linguistic analysis

### 3. US Intelligence Threat Assessment
- **Title**: Annual Threat Assessment of the U.S. Intelligence Community - March 2025
- **Topics**: National security, cyberthreats, geopolitics
- **Format**: PDF
- **Source**: Director of National Intelligence
- **Use Case**: Current affairs analysis and security research

### 4. Intelligence and State Policy
- **Title**: The Role of Intelligence and State Policies in International Security
- **Topics**: Intelligence, international security, state policy
- **Format**: PDF (sample)
- **Publication**: Cambridge Scholars Publishing, 2021
- **Use Case**: Academic research and policy analysis

### 5. Globalization and Intelligence
- **Title**: Beyond the Vigilant State: Globalisation and Intelligence
- **Topics**: Intelligence, globalization, security studies
- **Format**: PDF
- **Author**: Richard J. Aldrich
- **Use Case**: Academic paper analysis and research

## Use Cases

### Demo Environment Setup
```bash
# Set up demonstration environment
setup_demo_environment() {
  echo "Setting up TrustGraph demo environment..."
  
  # Initialize system
  tg-init-trustgraph
  
  # Load sample documents
  echo "Loading sample documents..."
  tg-load-sample-documents -U "demo"
  
  # Wait for processing
  echo "Waiting for document processing..."
  sleep 60
  
  # Start document processing
  echo "Starting document processing..."
  tg-show-library-documents -U "demo" | \
    grep "| id" | \
    awk '{print $3}' | \
    while read doc_id; do
      proc_id="demo_proc_$(date +%s)_${doc_id}"
      tg-start-library-processing -d "$doc_id" --id "$proc_id" -U "demo"
    done
  
  echo "Demo environment ready!"
  echo "Try: tg-invoke-document-rag -q 'What caused the Challenger accident?' -U demo"
}
```

### Testing Data Pipeline
```bash
# Test complete document processing pipeline
test_document_pipeline() {
  echo "Testing document processing pipeline..."
  
  # Load sample documents
  tg-load-sample-documents -U "test"
  
  # List loaded documents
  echo "Loaded documents:"
  tg-show-library-documents -U "test"
  
  # Start processing for each document
  tg-show-library-documents -U "test" | \
    grep "| id" | \
    awk '{print $3}' | \
    while read doc_id; do
      echo "Processing document: $doc_id"
      proc_id="test_$(date +%s)_${doc_id}"
      tg-start-library-processing -d "$doc_id" --id "$proc_id" -U "test"
    done
  
  # Wait for processing
  echo "Processing documents... (this may take several minutes)"
  sleep 300
  
  # Test document queries
  echo "Testing document queries..."
  
  test_queries=(
    "What is the Challenger accident?"
    "What is Old Icelandic?"
    "What are the main cybersecurity threats?"
    "What is intelligence policy?"
  )
  
  for query in "${test_queries[@]}"; do
    echo "Query: $query"
    tg-invoke-document-rag -q "$query" -U "test" | head -5
    echo "---"
  done
  
  echo "Pipeline test complete!"
}
```

### Educational Environment
```bash
# Set up educational/training environment
setup_educational_environment() {
  local class_name="$1"
  
  echo "Setting up educational environment for: $class_name"
  
  # Create user for the class
  class_user=$(echo "$class_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
  
  # Load sample documents for the class
  tg-load-sample-documents -U "$class_user"
  
  # Process documents
  echo "Processing documents for educational use..."
  tg-show-library-documents -U "$class_user" | \
    grep "| id" | \
    awk '{print $3}' | \
    while read doc_id; do
      proc_id="edu_$(date +%s)_${doc_id}"
      tg-start-library-processing \
        -d "$doc_id" \
        --id "$proc_id" \
        -U "$class_user" \
        --collection "education"
    done
  
  echo "Educational environment ready for: $class_name"
  echo "User: $class_user"
  echo "Collection: education"
}

# Set up for different classes
setup_educational_environment "AI Research Methods"
setup_educational_environment "Security Studies"
```

### Benchmarking and Performance Testing
```bash
# Benchmark document processing performance
benchmark_processing() {
  echo "Starting document processing benchmark..."
  
  # Load sample documents
  start_time=$(date +%s)
  tg-load-sample-documents -U "benchmark"
  load_time=$(date +%s)
  
  echo "Document loading time: $((load_time - start_time))s"
  
  # Count documents
  doc_count=$(tg-show-library-documents -U "benchmark" | grep -c "| id")
  echo "Documents loaded: $doc_count"
  
  # Start processing
  processing_ids=()
  tg-show-library-documents -U "benchmark" | \
    grep "| id" | \
    awk '{print $3}' | \
    while read doc_id; do
      proc_id="bench_$(date +%s)_${doc_id}"
      processing_ids+=("$proc_id")
      tg-start-library-processing -d "$doc_id" --id "$proc_id" -U "benchmark"
    done
  
  processing_start=$(date +%s)
  
  # Monitor processing completion
  echo "Monitoring processing completion..."
  while true; do
    active_processing=$(tg-show-flows | grep -c "bench_" || echo "0")
    
    if [ "$active_processing" -eq 0 ]; then
      break
    fi
    
    echo "Active processing jobs: $active_processing"
    sleep 30
  done
  
  processing_end=$(date +%s)
  
  echo "Processing completion time: $((processing_end - processing_start))s"
  echo "Total benchmark time: $((processing_end - start_time))s"
  
  # Test query performance
  echo "Testing query performance..."
  query_start=$(date +%s)
  
  for i in {1..10}; do
    tg-invoke-document-rag \
      -q "What are the main topics in these documents?" \
      -U "benchmark" > /dev/null
  done
  
  query_end=$(date +%s)
  echo "Average query time: $(echo "scale=2; ($query_end - $query_start) / 10" | bc)s"
}
```

## Advanced Usage

### Selective Document Loading
```bash
# Load only specific types of documents
load_by_category() {
  local category="$1"
  
  case "$category" in
    "government")
      echo "Loading government documents..."
      # This would require modifying the script to load selectively
      # For now, we load all and filter by tags later
      tg-load-sample-documents -U "gov-docs"
      ;;
    "academic")
      echo "Loading academic documents..."
      tg-load-sample-documents -U "academic-docs"
      ;;
    "historical")
      echo "Loading historical documents..."
      tg-load-sample-documents -U "historical-docs"
      ;;
    *)
      echo "Loading all sample documents..."
      tg-load-sample-documents
      ;;
  esac
}

# Load by category
load_by_category "government"
load_by_category "academic"
```

### Multi-Environment Loading
```bash
# Load sample documents to multiple environments
multi_environment_setup() {
  local environments=("dev" "staging" "demo")
  
  for env in "${environments[@]}"; do
    echo "Setting up $env environment..."
    
    tg-load-sample-documents \
      -u "http://$env.trustgraph.company.com:8088/" \
      -U "sample-data"
    
    echo "✓ $env environment loaded"
  done
  
  echo "All environments loaded with sample documents"
}
```

### Custom Document Sets
```bash
# Create custom document loading scripts based on the sample
create_custom_loader() {
  local domain="$1"
  
  cat > "load-${domain}-documents.py" << 'EOF'
#!/usr/bin/env python3
"""
Custom document loader for specific domain
Based on tg-load-sample-documents
"""

import argparse
import os
from trustgraph.api import Api

# Define your own document set here
documents = [
    {
        "id": "https://example.com/doc/custom-1",
        "title": "Custom Document 1",
        "url": "https://example.com/docs/custom1.pdf",
        # Add your document definitions...
    }
]

# Rest of the implementation similar to tg-load-sample-documents
EOF
  
  echo "Custom loader created: load-${domain}-documents.py"
}

# Create custom loaders for different domains
create_custom_loader "medical"
create_custom_loader "legal"
create_custom_loader "technical"
```

## Document Analysis

### Content Analysis
```bash
# Analyze loaded sample documents
analyze_sample_documents() {
  echo "Analyzing sample documents..."
  
  # Get document statistics
  total_docs=$(tg-show-library-documents | grep -c "| id")
  echo "Total documents: $total_docs"
  
  # Analyze by type
  echo "Document types:"
  tg-show-library-documents | \
    grep "| kind" | \
    awk '{print $3}' | \
    sort | uniq -c
  
  # Analyze tags
  echo "Popular tags:"
  tg-show-library-documents | \
    grep "| tags" | \
    sed 's/.*| tags.*| \(.*\) |.*/\1/' | \
    tr ',' '\n' | \
    sed 's/^ *//;s/ *$//' | \
    sort | uniq -c | sort -nr | head -10
  
  # Document sizes (would need additional API)
  echo "Document analysis complete"
}
```

### Query Testing
```bash
# Test sample documents with various queries
test_sample_queries() {
  echo "Testing sample document queries..."
  
  # Define test queries for different domains
  queries=(
    "What caused the Challenger space shuttle accident?"
    "What is Old Norse language?"
    "What are current cybersecurity threats?"
    "How does globalization affect intelligence services?"
    "What are the main security challenges in international relations?"
  )
  
  for query in "${queries[@]}"; do
    echo "Testing query: $query"
    echo "===================="
    
    result=$(tg-invoke-document-rag -q "$query" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
      echo "$result" | head -3
      echo "✓ Query successful"
    else
      echo "✗ Query failed"
    fi
    
    echo ""
  done
}
```

## Error Handling

### Network Issues
```bash
Exception: Connection failed during download
```
**Solution**: Check internet connectivity and retry. Documents are cached locally after first download.

### Insufficient Storage
```bash
Exception: No space left on device
```
**Solution**: Free up disk space. Sample documents total approximately 50-100MB.

### API Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Verify TrustGraph API is running and accessible.

### Processing Failures
```bash
Exception: Document processing failed
```
**Solution**: Check TrustGraph service logs and ensure all components are running.

## Monitoring and Validation

### Loading Progress
```bash
# Monitor sample document loading
monitor_sample_loading() {
  echo "Starting sample document loading with monitoring..."
  
  # Start loading in background
  tg-load-sample-documents &
  load_pid=$!
  
  # Monitor progress
  while kill -0 $load_pid 2>/dev/null; do
    doc_count=$(tg-show-library-documents 2>/dev/null | grep -c "| id" || echo "0")
    echo "Documents loaded so far: $doc_count"
    sleep 10
  done
  
  wait $load_pid
  
  if [ $? -eq 0 ]; then
    final_count=$(tg-show-library-documents | grep -c "| id")
    echo "✓ Loading completed successfully"
    echo "Total documents loaded: $final_count"
  else
    echo "✗ Loading failed"
  fi
}
```

### Validation
```bash
# Validate sample document loading
validate_sample_loading() {
  echo "Validating sample document loading..."
  
  # Expected document count (based on current sample set)
  expected_docs=5
  
  # Check actual count
  actual_docs=$(tg-show-library-documents | grep -c "| id")
  
  if [ "$actual_docs" -eq "$expected_docs" ]; then
    echo "✓ Document count correct: $actual_docs"
  else
    echo "⚠ Document count mismatch: expected $expected_docs, got $actual_docs"
  fi
  
  # Check for expected documents
  expected_titles=(
    "Challenger"
    "Icelandic"
    "Intelligence"
    "Threat Assessment"
    "Vigilant State"
  )
  
  for title in "${expected_titles[@]}"; do
    if tg-show-library-documents | grep -q "$title"; then
      echo "✓ Found document containing: $title"
    else
      echo "✗ Missing document containing: $title"
    fi
  done
  
  echo "Validation complete"
}
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-library-documents`](tg-show-library-documents.md) - List loaded documents
- [`tg-start-library-processing`](tg-start-library-processing.md) - Process loaded documents
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Query processed documents
- [`tg-load-pdf`](tg-load-pdf.md) - Load individual PDF documents

## API Integration

This command uses the [Library API](../apis/api-librarian.md) to add sample documents to TrustGraph's document repository.

## Best Practices

1. **Demo Preparation**: Use for setting up demonstration environments
2. **Testing**: Ideal for testing document processing pipelines
3. **Education**: Excellent for training and educational purposes
4. **Development**: Use in development environments for consistent test data
5. **Benchmarking**: Suitable for performance testing and optimization
6. **Documentation**: Great for documenting TrustGraph capabilities

## Troubleshooting

### Download Failures
```bash
# Check document URLs are accessible
curl -I "https://ntrs.nasa.gov/api/citations/19860015255/downloads/19860015255.pdf"

# Check local cache
ls -la doc-cache/
```

### Processing Issues
```bash
# Check document processing status
tg-show-library-processing

# Verify documents are in library
tg-show-library-documents | grep -E "(Challenger|Icelandic|Intelligence)"
```

### Performance Problems
```bash
# Monitor system resources during loading
top
df -h
```