# tg-dump-msgpack

Reads and analyzes knowledge core files in MessagePack format for diagnostic purposes.

## Synopsis

```bash
tg-dump-msgpack -i INPUT_FILE [options]
```

## Description

The `tg-dump-msgpack` command is a diagnostic utility that reads knowledge core files stored in MessagePack format and outputs their contents in JSON format or provides a summary analysis. This tool is primarily used for debugging, data inspection, and understanding the structure of knowledge cores.

MessagePack is a binary serialization format that TrustGraph uses for efficient storage and transfer of knowledge graph data.

## Options

### Required Arguments

- `-i, --input-file FILE`: Input MessagePack file to read

### Optional Arguments

- `-s, --summary`: Show a summary analysis of the file contents
- `-r, --records`: Dump individual records in JSON format (default behavior)

## Examples

### Dump Records as JSON
```bash
tg-dump-msgpack -i knowledge-core.msgpack
```

### Show Summary Analysis
```bash
tg-dump-msgpack -i knowledge-core.msgpack --summary
```

### Save Output to File
```bash
tg-dump-msgpack -i knowledge-core.msgpack > analysis.json
```

### Analyze Multiple Files
```bash
for file in *.msgpack; do
  echo "=== $file ==="
  tg-dump-msgpack -i "$file" --summary
  echo
done
```

## Output Formats

### Record Output (Default)
With `-r` or `--records` (default behavior), the command outputs each record as a separate JSON object:

```json
["t", {"m": {"m": [{"s": {"v": "uri1"}, "p": {"v": "predicate"}, "o": {"v": "object"}}]}}]
["ge", {"v": [[0.1, 0.2, 0.3, ...]]}]
["de", {"metadata": {...}, "chunks": [...]}]
```

### Summary Output
With `-s` or `--summary`, the command provides an analytical overview:

```
Vector dimension: 384
- NASA Challenger Report
- Technical Documentation
- Safety Engineering Guidelines
```

## Record Types

MessagePack files may contain different types of records:

### Triple Records ("t")
RDF triples representing knowledge graph relationships:
```json
["t", {
  "m": {
    "m": [{
      "s": {"v": "http://example.org/subject"},
      "p": {"v": "http://example.org/predicate"}, 
      "o": {"v": "object value"}
    }]
  }
}]
```

### Graph Embeddings ("ge") 
Vector embeddings for graph entities:
```json
["ge", {
  "v": [[0.1, 0.2, 0.3, 0.4, ...]]
}]
```

### Document Embeddings ("de")
Document chunk embeddings with metadata:
```json
["de", {
  "metadata": {
    "id": "doc-123",
    "user": "trustgraph",
    "collection": "default"
  },
  "chunks": [{
    "chunk": "text content",
    "vectors": [0.1, 0.2, 0.3, ...]
  }]
}]
```

## Use Cases

### Data Inspection
```bash
# Quick peek at file structure
tg-dump-msgpack -i mystery-core.msgpack --summary

# Detailed record analysis
tg-dump-msgpack -i knowledge-core.msgpack | head -20
```

### Debugging Knowledge Cores
```bash
# Check if file contains expected data types
tg-dump-msgpack -i core.msgpack | grep -o '^\["[^"]*"' | sort | uniq -c

# Find specific entities
tg-dump-msgpack -i core.msgpack | grep "NASA"

# Check vector dimensions
tg-dump-msgpack -i core.msgpack --summary | grep "Vector dimension"
```

### Quality Assurance
```bash
# Validate file completeness
validate_msgpack() {
  local file="$1"
  
  echo "Validating: $file"
  
  # Check file exists and is readable
  if [ ! -r "$file" ]; then
    echo "Error: Cannot read file $file"
    return 1
  fi
  
  # Get summary
  summary=$(tg-dump-msgpack -i "$file" --summary 2>/dev/null)
  
  if [ $? -ne 0 ]; then
    echo "Error: Failed to read MessagePack file"
    return 1
  fi
  
  # Check for vector dimension (indicates embeddings present)
  if echo "$summary" | grep -q "Vector dimension:"; then
    dim=$(echo "$summary" | grep "Vector dimension:" | awk '{print $3}')
    echo "✓ Contains embeddings (dimension: $dim)"
  else
    echo "⚠ No embeddings found"
  fi
  
  # Count labels (indicates entities present)
  label_count=$(echo "$summary" | grep "^-" | wc -l)
  echo "✓ Found $label_count labeled entities"
  
  return 0
}

# Validate multiple files
for file in cores/*.msgpack; do
  validate_msgpack "$file"
done
```

### Data Migration
```bash
# Convert MessagePack to JSON for processing
convert_to_json() {
  local input="$1"
  local output="$2"
  
  echo "Converting $input to $output..."
  tg-dump-msgpack -i "$input" > "$output"
  
  # Add array wrapper for valid JSON array
  sed -i '1i[' "$output"
  sed -i '$a]' "$output"
  sed -i 's/$/,/' "$output"
  sed -i '$s/,$//' "$output"
  
  echo "Conversion complete"
}

convert_to_json "knowledge.msgpack" "knowledge.json"
```

### Analysis and Reporting
```bash
# Generate comprehensive analysis report
analyze_msgpack() {
  local file="$1"
  local report_file="${file%.msgpack}_analysis.txt"
  
  echo "MessagePack Analysis Report" > "$report_file"
  echo "File: $file" >> "$report_file"
  echo "Generated: $(date)" >> "$report_file"
  echo "=============================" >> "$report_file"
  echo "" >> "$report_file"
  
  # Summary information
  echo "Summary:" >> "$report_file"
  tg-dump-msgpack -i "$file" --summary >> "$report_file"
  echo "" >> "$report_file"
  
  # Record type analysis
  echo "Record Type Distribution:" >> "$report_file"
  tg-dump-msgpack -i "$file" | \
    grep -o '^\["[^"]*"' | \
    sort | uniq -c | \
    awk '{print "  " $2 ": " $1 " records"}' >> "$report_file"
  echo "" >> "$report_file"
  
  # File statistics
  file_size=$(stat -c%s "$file")
  echo "File Statistics:" >> "$report_file"
  echo "  Size: $file_size bytes" >> "$report_file"
  echo "  Size (human): $(numfmt --to=iec-i --suffix=B $file_size)" >> "$report_file"
  
  echo "Analysis saved to: $report_file"
}

# Analyze all MessagePack files
for file in *.msgpack; do
  analyze_msgpack "$file"
done
```

### Comparative Analysis
```bash
# Compare two knowledge cores
compare_msgpack() {
  local file1="$1"
  local file2="$2"
  
  echo "Comparing MessagePack files:"
  echo "File 1: $file1"
  echo "File 2: $file2"
  echo "=========================="
  
  # Compare summaries
  echo "Summary comparison:"
  echo "File 1:"
  tg-dump-msgpack -i "$file1" --summary | sed 's/^/  /'
  echo ""
  echo "File 2:"
  tg-dump-msgpack -i "$file2" --summary | sed 's/^/  /'
  echo ""
  
  # Compare record counts
  echo "Record type comparison:"
  echo "File 1:"
  tg-dump-msgpack -i "$file1" | \
    grep -o '^\["[^"]*"' | \
    sort | uniq -c | \
    awk '{print "  " $2 ": " $1}' | \
    sort
  
  echo "File 2:"
  tg-dump-msgpack -i "$file2" | \
    grep -o '^\["[^"]*"' | \
    sort | uniq -c | \
    awk '{print "  " $2 ": " $1}' | \
    sort
}

compare_msgpack "core1.msgpack" "core2.msgpack"
```

## Advanced Usage

### Large File Processing
```bash
# Process large files in chunks
process_large_msgpack() {
  local file="$1"
  local chunk_size=1000
  
  echo "Processing large file: $file"
  
  # Count total records first
  total_records=$(tg-dump-msgpack -i "$file" | wc -l)
  echo "Total records: $total_records"
  
  # Process in chunks
  tg-dump-msgpack -i "$file" | \
    split -l $chunk_size - "chunk_"
  
  echo "Split into chunks of $chunk_size records each"
  
  # Process each chunk
  for chunk in chunk_*; do
    echo "Processing $chunk..."
    # Add your processing logic here
    wc -l "$chunk"
  done
  
  # Clean up
  rm chunk_*
}
```

### Data Extraction
```bash
# Extract specific data types
extract_triples() {
  local file="$1"
  local output="triples.json"
  
  echo "Extracting triples from $file..."
  tg-dump-msgpack -i "$file" | \
    grep '^\["t"' > "$output"
  
  echo "Triples saved to: $output"
}

extract_embeddings() {
  local file="$1"
  local output="embeddings.json"
  
  echo "Extracting embeddings from $file..."
  tg-dump-msgpack -i "$file" | \
    grep -E '^\["(ge|de)"' > "$output"
  
  echo "Embeddings saved to: $output"
}

# Extract all data types
extract_triples "knowledge.msgpack"
extract_embeddings "knowledge.msgpack"
```

### Integration with Other Tools
```bash
# Convert MessagePack to formats for other tools
msgpack_to_turtle() {
  local input="$1"
  local output="$2"
  
  echo "Converting MessagePack to Turtle format..."
  
  # Extract triples and convert to Turtle
  tg-dump-msgpack -i "$input" | \
    grep '^\["t"' | \
    jq -r '.[1].m.m[] | 
      "<" + .s.v + "> <" + .p.v + "> " + 
      (if .o.e then "<" + .o.v + ">" else "\"" + .o.v + "\"" end) + " ."' \
    > "$output"
  
  echo "Turtle format saved to: $output"
}

msgpack_to_turtle "knowledge.msgpack" "knowledge.ttl"
```

## Error Handling

### File Not Found
```bash
Exception: [Errno 2] No such file or directory: 'missing.msgpack'
```
**Solution**: Check file path and ensure the file exists.

### Invalid MessagePack Format
```bash
Exception: Unpack failed
```
**Solution**: Verify the file is a valid MessagePack file and not corrupted.

### Memory Issues with Large Files
```bash
MemoryError: Unable to allocate memory
```
**Solution**: Process large files in chunks or use streaming approaches.

### Permission Errors
```bash
Exception: [Errno 13] Permission denied
```
**Solution**: Check file permissions and ensure read access.

## Performance Considerations

### File Size Optimization
```bash
# Check file compression efficiency
check_compression() {
  local file="$1"
  
  original_size=$(stat -c%s "$file")
  
  # Test compression
  gzip -c "$file" > "${file}.gz"
  compressed_size=$(stat -c%s "${file}.gz")
  
  ratio=$(echo "scale=2; $compressed_size * 100 / $original_size" | bc)
  
  echo "Original: $(numfmt --to=iec-i --suffix=B $original_size)"
  echo "Compressed: $(numfmt --to=iec-i --suffix=B $compressed_size)"
  echo "Compression ratio: ${ratio}%"
  
  rm "${file}.gz"
}
```

### Processing Speed
```bash
# Time processing operations
time_msgpack_ops() {
  local file="$1"
  
  echo "Timing MessagePack operations for: $file"
  
  # Time summary generation
  echo "Summary generation:"
  time tg-dump-msgpack -i "$file" --summary > /dev/null
  
  # Time full dump
  echo "Full record dump:"
  time tg-dump-msgpack -i "$file" > /dev/null
}
```

## Related Commands

- [`tg-get-kg-core`](tg-get-kg-core.md) - Export knowledge cores to MessagePack
- [`tg-load-kg-core`](tg-load-kg-core.md) - Load MessagePack knowledge cores
- [`tg-save-doc-embeds`](tg-save-doc-embeds.md) - Save document embeddings to MessagePack

## Best Practices

1. **File Validation**: Always validate MessagePack files before processing
2. **Memory Management**: Be cautious with large files to avoid memory issues
3. **Backup**: Keep backups of original MessagePack files before analysis
4. **Incremental Processing**: Process large files incrementally when possible
5. **Documentation**: Document the structure and content of your MessagePack files
6. **Version Control**: Track changes in MessagePack file formats over time

## Troubleshooting

### Corrupted Files
```bash
# Test file integrity
if tg-dump-msgpack -i "test.msgpack" --summary > /dev/null 2>&1; then
  echo "File appears valid"
else
  echo "File may be corrupted"
fi
```

### Empty or Incomplete Files
```bash
# Check for empty files
if [ ! -s "test.msgpack" ]; then
  echo "File is empty"
fi

# Check record count
record_count=$(tg-dump-msgpack -i "test.msgpack" 2>/dev/null | wc -l)
echo "Records found: $record_count"
```

### Format Issues
```bash
# Validate JSON output
tg-dump-msgpack -i "test.msgpack" | head -1 | jq . > /dev/null
if [ $? -eq 0 ]; then
  echo "JSON output is valid"
else
  echo "JSON output may be malformed"
fi
```