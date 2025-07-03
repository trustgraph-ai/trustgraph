# tg-load-turtle

Loads RDF triples from Turtle files into the TrustGraph knowledge graph.

## Synopsis

```bash
tg-load-turtle -i DOCUMENT_ID [options] file1.ttl [file2.ttl ...]
```

## Description

The `tg-load-turtle` command loads RDF triples from Turtle (TTL) format files into TrustGraph's knowledge graph. It parses Turtle files, converts them to TrustGraph's internal triple format, and imports them using WebSocket connections for efficient batch processing.

The command supports retry logic and automatic reconnection to handle network interruptions during large data imports.

## Options

### Required Arguments

- `-i, --document-id ID`: Document ID to associate with the triples
- `files`: One or more Turtle files to load

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `ws://localhost:8088/`)
- `-f, --flow-id ID`: Flow instance ID to use (default: `default`)
- `-U, --user USER`: User ID for triple ownership (default: `trustgraph`)
- `-C, --collection COLLECTION`: Collection to assign triples (default: `default`)

## Examples

### Basic Turtle Loading
```bash
tg-load-turtle -i "doc123" knowledge-base.ttl
```

### Multiple Files
```bash
tg-load-turtle -i "ontology-v1" \
  schema.ttl \
  instances.ttl \
  relationships.ttl
```

### Custom Flow and Collection
```bash
tg-load-turtle \
  -i "research-data" \
  -f "knowledge-import-flow" \
  -U "research-team" \
  -C "research-kg" \
  research-triples.ttl
```

### Load with Custom API URL
```bash
tg-load-turtle \
  -i "production-data" \
  -u "ws://production:8088/" \
  production-ontology.ttl
```

## Turtle Format Support

### Basic Triples
```turtle
@prefix ex: <http://example.org/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Person rdf:type rdfs:Class .
ex:john rdf:type ex:Person .
ex:john ex:name "John Doe" .
ex:john ex:age "30"^^xsd:integer .
```

### Complex Structures
```turtle
@prefix org: <http://example.org/organization/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

org:TechCorp rdf:type foaf:Organization ;
             foaf:name "Technology Corporation" ;
             org:hasEmployee org:john, org:jane ;
             org:foundedYear "2010"^^xsd:gYear .

org:john foaf:name "John Smith" ;
         foaf:mbox <mailto:john@techcorp.com> ;
         org:position "Software Engineer" .
```

### Ontology Loading
```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .

<http://example.org/ontology> rdf:type owl:Ontology ;
                              dc:title "Example Ontology" ;
                              dc:creator "Knowledge Team" .

ex:Vehicle rdf:type owl:Class ;
           rdfs:label "Vehicle" ;
           rdfs:comment "A means of transportation" .

ex:Car rdfs:subClassOf ex:Vehicle .
ex:Truck rdfs:subClassOf ex:Vehicle .
```

## Data Processing

### Triple Conversion
The loader converts Turtle triples to TrustGraph format:
- **URIs**: Converted to URI references with `is_uri=true`
- **Literals**: Converted to literal values with `is_uri=false`
- **Datatypes**: Preserved in literal values

### Batch Processing
- Triples are sent individually via WebSocket
- Each triple includes document metadata
- Automatic retry on connection failures
- Progress tracking for large files

### Error Handling
- Invalid Turtle syntax causes parsing errors
- Network interruptions trigger automatic retry
- Malformed triples are skipped with warnings

## Use Cases

### Ontology Import
```bash
# Load domain ontology
tg-load-turtle -i "healthcare-ontology" \
  -C "ontologies" \
  healthcare-schema.ttl

# Load instance data
tg-load-turtle -i "patient-data" \
  -C "healthcare-data" \
  patient-records.ttl
```

### Knowledge Base Migration
```bash
# Migrate from external knowledge base
tg-load-turtle -i "migration-$(date +%Y%m%d)" \
  -C "migrated-data" \
  exported-knowledge.ttl
```

### Research Data Loading
```bash
# Load research datasets
datasets=("publications" "authors" "citations")
for dataset in "${datasets[@]}"; do
  tg-load-turtle -i "research-$dataset" \
    -C "research-data" \
    "$dataset.ttl"
done
```

### Structured Data Import
```bash
# Load structured data from various sources
tg-load-turtle -i "products" -C "catalog" product-catalog.ttl
tg-load-turtle -i "customers" -C "crm" customer-data.ttl
tg-load-turtle -i "orders" -C "transactions" order-history.ttl
```

## Advanced Usage

### Batch Processing Multiple Files
```bash
# Process all Turtle files in directory
for ttl in *.ttl; do
  doc_id=$(basename "$ttl" .ttl)
  echo "Loading $ttl as document $doc_id..."
  
  tg-load-turtle -i "$doc_id" \
    -C "bulk-import-$(date +%Y%m%d)" \
    "$ttl"
done
```

### Parallel Loading
```bash
# Load multiple files in parallel
ttl_files=(schema.ttl instances.ttl relationships.ttl)
for ttl in "${ttl_files[@]}"; do
  (
    doc_id=$(basename "$ttl" .ttl)
    echo "Loading $ttl in background..."
    tg-load-turtle -i "parallel-$doc_id" \
      -C "parallel-import" \
      "$ttl"
  ) &
done
wait
echo "All files loaded"
```

### Size-Based Processing
```bash
# Handle large files differently
for ttl in *.ttl; do
  size=$(stat -c%s "$ttl")
  doc_id=$(basename "$ttl" .ttl)
  
  if [ $size -lt 10485760 ]; then  # < 10MB
    echo "Processing small file: $ttl"
    tg-load-turtle -i "$doc_id" -C "small-files" "$ttl"
  else
    echo "Processing large file: $ttl"
    # Use dedicated collection for large files
    tg-load-turtle -i "$doc_id" -C "large-files" "$ttl"
  fi
done
```

### Validation and Loading
```bash
# Validate before loading
validate_and_load() {
    local ttl_file="$1"
    local doc_id="$2"
    
    echo "Validating $ttl_file..."
    
    # Check Turtle syntax
    if rapper -q -i turtle "$ttl_file" > /dev/null 2>&1; then
        echo "✓ Valid Turtle syntax"
        
        # Count triples
        triple_count=$(rapper -i turtle -c "$ttl_file" 2>/dev/null)
        echo "  Triples: $triple_count"
        
        # Load if valid
        echo "Loading $ttl_file..."
        tg-load-turtle -i "$doc_id" -C "validated-data" "$ttl_file"
    else
        echo "✗ Invalid Turtle syntax in $ttl_file"
        return 1
    fi
}

# Validate and load all files
for ttl in *.ttl; do
    doc_id=$(basename "$ttl" .ttl)
    validate_and_load "$ttl" "$doc_id"
done
```

## Error Handling

### Invalid Turtle Syntax
```bash
Exception: Turtle parsing failed
```
**Solution**: Validate Turtle syntax with tools like `rapper` or `rdflib`.

### Document ID Required
```bash
Exception: Document ID is required
```
**Solution**: Provide document ID with `-i` option.

### WebSocket Connection Issues
```bash
Exception: WebSocket connection failed
```
**Solution**: Check API URL and ensure TrustGraph WebSocket service is running.

### File Not Found
```bash
Exception: [Errno 2] No such file or directory
```
**Solution**: Verify file paths and ensure Turtle files exist.

### Flow Not Found
```bash
Exception: Flow instance not found
```
**Solution**: Verify flow ID with `tg-show-flows`.

## Monitoring and Verification

### Load Progress Tracking
```bash
# Monitor loading progress
monitor_load() {
    local ttl_file="$1"
    local doc_id="$2"
    
    echo "Starting load: $ttl_file"
    start_time=$(date +%s)
    
    tg-load-turtle -i "$doc_id" -C "monitored" "$ttl_file"
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo "Load completed in ${duration}s"
    
    # Verify data is accessible
    if tg-triples-query -s "http://example.org/test" > /dev/null 2>&1; then
        echo "✓ Data accessible via query"
    else
        echo "✗ Data not accessible"
    fi
}
```

### Data Verification
```bash
# Verify loaded triples
verify_triples() {
    local collection="$1"
    local expected_count="$2"
    
    echo "Verifying triples in collection: $collection"
    
    # Query for triples
    actual_count=$(tg-triples-query -C "$collection" | wc -l)
    
    if [ "$actual_count" -ge "$expected_count" ]; then
        echo "✓ Expected triples found ($actual_count >= $expected_count)"
    else
        echo "✗ Missing triples ($actual_count < $expected_count)"
        return 1
    fi
}
```

### Content Analysis
```bash
# Analyze loaded content
analyze_turtle_content() {
    local ttl_file="$1"
    
    echo "Analyzing content: $ttl_file"
    
    # Extract prefixes
    echo "Prefixes:"
    grep "^@prefix" "$ttl_file" | head -5
    
    # Count statements
    statement_count=$(grep -c "\." "$ttl_file")
    echo "Statements: $statement_count"
    
    # Extract subjects
    echo "Sample subjects:"
    grep -o "^[^[:space:]]*" "$ttl_file" | grep -v "^@" | sort | uniq | head -5
}
```

## Performance Optimization

### Connection Pooling
```bash
# Reuse WebSocket connections for multiple files
load_batch_optimized() {
    local collection="$1"
    shift
    local files=("$@")
    
    echo "Loading ${#files[@]} files to collection: $collection"
    
    # Process files in batches to reuse connections
    for ((i=0; i<${#files[@]}; i+=5)); do
        batch=("${files[@]:$i:5}")
        
        echo "Processing batch $((i/5 + 1))..."
        for ttl in "${batch[@]}"; do
            doc_id=$(basename "$ttl" .ttl)
            tg-load-turtle -i "$doc_id" -C "$collection" "$ttl" &
        done
        wait
    done
}
```

### Memory Management
```bash
# Handle large files with memory monitoring
load_with_memory_check() {
    local ttl_file="$1"
    local doc_id="$2"
    
    # Check available memory
    available=$(free -m | awk 'NR==2{print $7}')
    if [ "$available" -lt 1000 ]; then
        echo "Warning: Low memory ($available MB). Consider splitting file."
    fi
    
    # Monitor memory during load
    tg-load-turtle -i "$doc_id" -C "memory-monitored" "$ttl_file" &
    load_pid=$!
    
    while kill -0 $load_pid 2>/dev/null; do
        memory_usage=$(ps -p $load_pid -o rss= | awk '{print $1/1024}')
        echo "Memory usage: ${memory_usage}MB"
        sleep 5
    done
}
```

## Data Preparation

### Turtle File Preparation
```bash
# Clean and prepare Turtle files
prepare_turtle() {
    local input_file="$1"
    local output_file="$2"
    
    echo "Preparing $input_file -> $output_file"
    
    # Remove comments and empty lines
    sed '/^#/d; /^$/d' "$input_file" > "$output_file"
    
    # Validate output
    if rapper -q -i turtle "$output_file" > /dev/null 2>&1; then
        echo "✓ Prepared file is valid"
    else
        echo "✗ Prepared file is invalid"
        return 1
    fi
}
```

### Data Splitting
```bash
# Split large Turtle files
split_turtle() {
    local input_file="$1"
    local lines_per_file="$2"
    
    echo "Splitting $input_file into chunks of $lines_per_file lines"
    
    # Split file
    split -l "$lines_per_file" "$input_file" "$(basename "$input_file" .ttl)_part_"
    
    # Add .ttl extension to parts
    for part in $(basename "$input_file" .ttl)_part_*; do
        mv "$part" "$part.ttl"
    done
}
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL (WebSocket format)

## Related Commands

- [`tg-triples-query`](tg-triples-query.md) - Query loaded triples
- [`tg-graph-to-turtle`](tg-graph-to-turtle.md) - Export graph to Turtle format
- [`tg-show-flows`](tg-show-flows.md) - Monitor processing flows
- [`tg-load-pdf`](tg-load-pdf.md) - Load document content

## API Integration

This command uses TrustGraph's WebSocket-based triple import API for efficient batch loading of RDF data.

## Best Practices

1. **Validation**: Always validate Turtle syntax before loading
2. **Document IDs**: Use meaningful, unique document identifiers
3. **Collections**: Organize triples into logical collections
4. **Error Handling**: Implement retry logic for network issues
5. **Performance**: Consider file sizes and system resources
6. **Monitoring**: Track loading progress and verify results
7. **Backup**: Maintain backups of source Turtle files

## Troubleshooting

### WebSocket Connection Issues
```bash
# Test WebSocket connectivity
wscat -c ws://localhost:8088/api/v1/flow/default/import/triples

# Check WebSocket service status
tg-show-flows | grep -i websocket
```

### Parsing Errors
```bash
# Validate Turtle syntax
rapper -i turtle -q file.ttl

# Check for common issues
grep -n "^[[:space:]]*@prefix" file.ttl  # Check prefixes
grep -n "\.$" file.ttl | head -5  # Check statement terminators
```

### Memory Issues
```bash
# Monitor memory usage
free -h
ps aux | grep tg-load-turtle

# Split large files if needed
split -l 10000 large-file.ttl chunk_
```