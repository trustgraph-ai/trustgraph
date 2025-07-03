# tg-graph-to-turtle

Exports knowledge graph data to Turtle (TTL) format for backup, analysis, or migration.

## Synopsis

```bash
tg-graph-to-turtle [options]
```

## Description

The `tg-graph-to-turtle` command connects to TrustGraph's triple query service and exports all graph triples in Turtle format. This is useful for creating backups, analyzing graph structure, migrating data, or integrating with external RDF tools.

The command queries up to 10,000 triples and outputs them in standard Turtle format to stdout, while also saving to an `output.ttl` file.

## Options

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-f, --flow-id ID`: Flow instance ID to use (default: `default`)
- `-U, --user USER`: User ID for data scope (default: `trustgraph`)
- `-C, --collection COLLECTION`: Collection to export (default: `default`)

## Examples

### Basic Export
```bash
tg-graph-to-turtle
```

### Export to File
```bash
tg-graph-to-turtle > knowledge-graph.ttl
```

### Export Specific Collection
```bash
tg-graph-to-turtle -C "research-data" > research-graph.ttl
```

### Export with Custom Flow
```bash
tg-graph-to-turtle -f "production-flow" -U "admin" > production-graph.ttl
```

## Output Format

The command generates Turtle format with proper RDF syntax:

```turtle
@prefix ns1: <http://example.org/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ns1:Person rdf:type rdfs:Class .
ns1:john rdf:type ns1:Person ;
         ns1:name "John Doe" ;
         ns1:age "30" .
ns1:jane rdf:type ns1:Person ;
         ns1:name "Jane Smith" ;
         ns1:department "Engineering" .
```

### Output Destinations

1. **stdout**: Standard output for piping or display
2. **output.ttl**: Automatically created file in current directory

## Use Cases

### Data Backup
```bash
# Create timestamped backups
timestamp=$(date +%Y%m%d_%H%M%S)
tg-graph-to-turtle > "backup_${timestamp}.ttl"

# Backup specific collections
collections=("research" "products" "customers")
for collection in "${collections[@]}"; do
  tg-graph-to-turtle -C "$collection" > "backup_${collection}_${timestamp}.ttl"
done
```

### Data Migration
```bash
# Export from source environment
tg-graph-to-turtle -u "http://source:8088/" > source-data.ttl

# Import to target environment
tg-load-turtle -i "migration-$(date +%Y%m%d)" \
  -u "ws://target:8088/" \
  source-data.ttl
```

### Graph Analysis
```bash
# Export for analysis
tg-graph-to-turtle > analysis-data.ttl

# Analyze with external tools
rapper -i turtle -o ntriples analysis-data.ttl | wc -l  # Count triples
grep -c "rdf:type" analysis-data.ttl  # Count type assertions
```

### Integration with External Tools
```bash
# Export for Apache Jena
tg-graph-to-turtle > jena-input.ttl
tdb2.tdbloader --loc=tdb-database jena-input.ttl

# Export for Virtuoso
tg-graph-to-turtle > virtuoso-data.ttl
isql-v -U dba -P password < load-script.sql
```

## Advanced Usage

### Incremental Exports
```bash
# Export with timestamps for incremental backups
last_export_file="last_export_timestamp.txt"
current_time=$(date +%Y%m%d_%H%M%S)

if [ -f "$last_export_file" ]; then
  last_export=$(cat "$last_export_file")
  echo "Last export: $last_export"
fi

echo "Current export: $current_time"
tg-graph-to-turtle > "incremental_${current_time}.ttl"
echo "$current_time" > "$last_export_file"
```

### Multi-Collection Export
```bash
# Export all collections to separate files
export_all_collections() {
  local output_dir="graph_exports_$(date +%Y%m%d)"
  mkdir -p "$output_dir"
  
  echo "Exporting all collections to $output_dir"
  
  # Get list of collections (this would need to be implemented)
  # For now, use known collections
  collections=("default" "research" "products" "documents")
  
  for collection in "${collections[@]}"; do
    echo "Exporting collection: $collection"
    tg-graph-to-turtle -C "$collection" > "$output_dir/${collection}.ttl"
    
    # Verify export
    if [ -s "$output_dir/${collection}.ttl" ]; then
      triple_count=$(grep -c "\." "$output_dir/${collection}.ttl")
      echo "  Exported $triple_count triples"
    else
      echo "  No data exported"
    fi
  done
}

export_all_collections
```

### Filtered Export
```bash
# Export specific types of triples
export_filtered() {
  local filter_type="$1"
  local output_file="$2"
  
  echo "Exporting $filter_type triples to $output_file"
  
  # Export all data first
  tg-graph-to-turtle > temp_full_export.ttl
  
  # Filter based on type
  case "$filter_type" in
    "classes")
      grep "rdf:type.*Class" temp_full_export.ttl > "$output_file"
      ;;
    "instances")
      grep -v "rdf:type.*Class" temp_full_export.ttl > "$output_file"
      ;;
    "properties")
      grep "rdf:type.*Property" temp_full_export.ttl > "$output_file"
      ;;
    *)
      echo "Unknown filter type: $filter_type"
      return 1
      ;;
  esac
  
  rm temp_full_export.ttl
}

# Usage
export_filtered "classes" "schema-classes.ttl"
export_filtered "instances" "instance-data.ttl"
```

### Compression and Packaging
```bash
# Export and compress
export_compressed() {
  local collection="$1"
  local timestamp=$(date +%Y%m%d_%H%M%S)
  local filename="${collection}_${timestamp}"
  
  echo "Exporting and compressing collection: $collection"
  
  # Export to temporary file
  tg-graph-to-turtle -C "$collection" > "${filename}.ttl"
  
  # Compress
  gzip "${filename}.ttl"
  
  # Create metadata
  cat > "${filename}.meta" << EOF
Collection: $collection
Export Date: $(date)
Compressed Size: $(stat -c%s "${filename}.ttl.gz") bytes
MD5: $(md5sum "${filename}.ttl.gz" | cut -d' ' -f1)
EOF
  
  echo "Export complete: ${filename}.ttl.gz"
}

# Export multiple collections compressed
collections=("research" "products" "customers")
for collection in "${collections[@]}"; do
  export_compressed "$collection"
done
```

### Validation and Quality Checks
```bash
# Export with validation
export_with_validation() {
  local output_file="$1"
  
  echo "Exporting with validation to $output_file"
  
  # Export
  tg-graph-to-turtle > "$output_file"
  
  # Validate Turtle syntax
  if rapper -q -i turtle "$output_file" > /dev/null 2>&1; then
    echo "✓ Valid Turtle syntax"
  else
    echo "✗ Invalid Turtle syntax"
    return 1
  fi
  
  # Count triples
  triple_count=$(rapper -i turtle -c "$output_file" 2>/dev/null)
  echo "Total triples: $triple_count"
  
  # Check for common issues
  if grep -q "^@prefix" "$output_file"; then
    echo "✓ Prefixes found"
  else
    echo "⚠ No prefixes found"
  fi
  
  # Check for URIs with spaces (malformed)
  malformed_uris=$(grep -c " " "$output_file" || echo "0")
  if [ "$malformed_uris" -gt 0 ]; then
    echo "⚠ Found $malformed_uris lines with spaces (potential malformed URIs)"
  fi
}

# Validate export
export_with_validation "validated-export.ttl"
```

## Performance Optimization

### Streaming Export
```bash
# Handle large datasets with streaming
stream_export() {
  local collection="$1"
  local chunk_size="$2"
  local output_prefix="$3"
  
  echo "Streaming export of collection: $collection"
  
  # Export to temporary file
  tg-graph-to-turtle -C "$collection" > temp_export.ttl
  
  # Split into chunks
  split -l "$chunk_size" temp_export.ttl "${output_prefix}_"
  
  # Add .ttl extension and validate each chunk
  for chunk in ${output_prefix}_*; do
    mv "$chunk" "$chunk.ttl"
    
    # Validate chunk
    if rapper -q -i turtle "$chunk.ttl" > /dev/null 2>&1; then
      echo "✓ Valid chunk: $chunk.ttl"
    else
      echo "✗ Invalid chunk: $chunk.ttl"
    fi
  done
  
  rm temp_export.ttl
}

# Stream large collection
stream_export "large-collection" 1000 "chunk"
```

### Parallel Processing
```bash
# Export multiple collections in parallel
parallel_export() {
  local collections=("$@")
  local timestamp=$(date +%Y%m%d_%H%M%S)
  
  echo "Exporting ${#collections[@]} collections in parallel"
  
  for collection in "${collections[@]}"; do
    (
      echo "Exporting $collection..."
      tg-graph-to-turtle -C "$collection" > "${collection}_${timestamp}.ttl"
      echo "✓ Completed: $collection"
    ) &
  done
  
  wait
  echo "All exports completed"
}

# Export collections in parallel
parallel_export "research" "products" "customers" "documents"
```

## Integration Scripts

### Automated Backup System
```bash
#!/bin/bash
# automated-backup.sh
backup_dir="graph_backups"
retention_days=30

echo "Starting automated graph backup..."

# Create backup directory
mkdir -p "$backup_dir"

# Export with timestamp
timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="$backup_dir/graph_backup_${timestamp}.ttl"

echo "Exporting to: $backup_file"
tg-graph-to-turtle > "$backup_file"

# Compress
gzip "$backup_file"
echo "Compressed: ${backup_file}.gz"

# Clean old backups
find "$backup_dir" -name "*.ttl.gz" -mtime +$retention_days -delete
echo "Cleaned backups older than $retention_days days"

# Verify backup
if [ -f "${backup_file}.gz" ]; then
  size=$(stat -c%s "${backup_file}.gz")
  echo "Backup completed: ${size} bytes"
else
  echo "Backup failed!"
  exit 1
fi
```

### Data Sync Script
```bash
#!/bin/bash
# sync-graphs.sh
source_url="$1"
target_url="$2"
collection="$3"

if [ -z "$source_url" ] || [ -z "$target_url" ] || [ -z "$collection" ]; then
  echo "Usage: $0 <source-url> <target-url> <collection>"
  exit 1
fi

echo "Syncing collection '$collection' from $source_url to $target_url"

# Export from source
temp_file="sync_temp_$(date +%s).ttl"
tg-graph-to-turtle -u "$source_url" -C "$collection" > "$temp_file"

# Validate export
if [ ! -s "$temp_file" ]; then
  echo "No data exported from source"
  exit 1
fi

# Load to target
doc_id="sync-$(date +%Y%m%d-%H%M%S)"
if tg-load-turtle -i "$doc_id" -u "$target_url" -C "$collection" "$temp_file"; then
  echo "Sync completed successfully"
else
  echo "Sync failed"
  exit 1
fi

# Cleanup
rm "$temp_file"
```

## Error Handling

### Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Check API URL and ensure TrustGraph is running.

### Flow Not Found
```bash
Exception: Flow instance not found
```
**Solution**: Verify flow ID with `tg-show-flows`.

### Permission Errors
```bash
Exception: Access denied
```
**Solution**: Check user permissions for the specified collection.

### Empty Output
```bash
# No triples exported
```
**Solution**: Verify collection contains data and user has access.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-load-turtle`](tg-load-turtle.md) - Import Turtle files
- [`tg-triples-query`](tg-triples-query.md) - Query graph triples
- [`tg-show-flows`](tg-show-flows.md) - List available flows
- [`tg-get-kg-core`](tg-get-kg-core.md) - Export knowledge cores

## API Integration

This command uses the [Triples Query API](../apis/api-triples-query.md) to retrieve graph data and convert it to Turtle format.

## Best Practices

1. **Regular Backups**: Schedule regular exports for data protection
2. **Validation**: Always validate exported Turtle files
3. **Compression**: Compress large exports for storage efficiency
4. **Monitoring**: Track export sizes and success rates
5. **Documentation**: Document export procedures and retention policies
6. **Security**: Ensure sensitive data is properly protected in exports
7. **Version Control**: Consider versioning exported schemas

## Troubleshooting

### Large Dataset Issues
```bash
# Check query limits
grep -c "\." output.ttl  # Count exported triples
# Default limit is 10,000 triples

# For larger datasets, consider using tg-get-kg-core
tg-get-kg-core -n "collection-name" > large-export.msgpack
```

### Malformed URIs
```bash
# Check for URIs with spaces
grep " " output.ttl | head -5

# Clean URIs if needed
sed 's/ /%20/g' output.ttl > cleaned-output.ttl
```

### Memory Issues
```bash
# Monitor memory usage during export
free -h
# Consider splitting exports for large datasets
```