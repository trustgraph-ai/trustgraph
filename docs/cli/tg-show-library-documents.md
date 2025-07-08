# tg-show-library-documents

Lists all documents stored in the TrustGraph document library with their metadata.

## Synopsis

```bash
tg-show-library-documents [options]
```

## Description

The `tg-show-library-documents` command displays all documents currently stored in TrustGraph's document library. For each document, it shows comprehensive metadata including ID, timestamp, title, document type, comments, and associated tags.

The document library serves as a centralized repository for managing documents before and after processing through TrustGraph workflows.

## Options

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User ID to filter documents (default: `trustgraph`)

## Examples

### List All Documents
```bash
tg-show-library-documents
```

### List Documents for Specific User
```bash
tg-show-library-documents -U "research-team"
```

### Using Custom API URL
```bash
tg-show-library-documents -u http://production:8088/
```

## Output Format

The command displays each document in a formatted table:

```
+-------+----------------------------------+
| id    | doc_123456789                    |
| time  | 2023-12-15 10:30:45             |
| title | Technical Manual v2.1           |
| kind  | PDF                              |
| note  | Updated installation procedures  |
| tags  | technical, manual, v2.1          |
+-------+----------------------------------+

+-------+----------------------------------+
| id    | doc_987654321                    |
| time  | 2023-12-14 15:22:10             |
| title | Q4 Financial Report              |
| kind  | PDF                              |
| note  | Quarterly analysis and metrics   |
| tags  | finance, quarterly, 2023         |
+-------+----------------------------------+
```

### Document Properties

- **id**: Unique document identifier
- **time**: Upload/creation timestamp
- **title**: Document title or name
- **kind**: Document type (PDF, DOCX, TXT, etc.)
- **note**: Comments or description
- **tags**: Comma-separated list of tags

### Empty Results

If no documents exist:
```
No documents.
```

## Use Cases

### Document Inventory
```bash
# Get complete document inventory
tg-show-library-documents > document-inventory.txt

# Count total documents
tg-show-library-documents | grep -c "| id"
```

### Document Discovery
```bash
# Find documents by title pattern
tg-show-library-documents | grep -i "manual"

# Find documents by type
tg-show-library-documents | grep "| kind.*PDF"

# Find recent documents
tg-show-library-documents | grep "2023-12"
```

### User-Specific Queries
```bash
# List documents by different users
users=("research-team" "finance-dept" "legal-team")
for user in "${users[@]}"; do
  echo "Documents for $user:"
  tg-show-library-documents -U "$user"
  echo "---"
done
```

### Document Management
```bash
# Extract document IDs for processing
tg-show-library-documents | \
  grep "| id" | \
  awk '{print $3}' > document-ids.txt

# Find documents by tags
tg-show-library-documents | \
  grep -A5 -B5 "research" | \
  grep "| id" | \
  awk '{print $3}'
```

## Advanced Usage

### Document Analysis
```bash
# Analyze document distribution by type
analyze_document_types() {
  echo "Document Type Distribution:"
  echo "=========================="
  
  tg-show-library-documents | \
    grep "| kind" | \
    awk '{print $3}' | \
    sort | uniq -c | sort -nr
}

analyze_document_types
```

### Document Age Analysis
```bash
# Find old documents
find_old_documents() {
  local days_old="$1"
  
  echo "Documents older than $days_old days:"
  echo "===================================="
  
  cutoff_date=$(date -d "$days_old days ago" +"%Y-%m-%d")
  
  tg-show-library-documents | \
    grep "| time" | \
    while read -r line; do
      doc_date=$(echo "$line" | awk '{print $3}')
      if [[ "$doc_date" < "$cutoff_date" ]]; then
        echo "$line"
      fi
    done
}

# Find documents older than 30 days
find_old_documents 30
```

### Tag Analysis
```bash
# Analyze tag usage
analyze_tags() {
  echo "Tag Usage Analysis:"
  echo "=================="
  
  tg-show-library-documents | \
    grep "| tags" | \
    sed 's/| tags.*| \(.*\) |/\1/' | \
    tr ',' '\n' | \
    sed 's/^ *//;s/ *$//' | \
    sort | uniq -c | sort -nr
}

analyze_tags
```

### Document Search
```bash
# Search documents by multiple criteria
search_documents() {
  local query="$1"
  
  echo "Searching for: $query"
  echo "===================="
  
  tg-show-library-documents | \
    grep -i -A6 -B6 "$query" | \
    grep -E "^\+|^\|"
}

# Search for specific terms
search_documents "financial"
search_documents "manual"
```

### User Document Summary
```bash
# Generate user document summary
user_summary() {
  local user="$1"
  
  echo "Document Summary for User: $user"
  echo "================================"
  
  docs=$(tg-show-library-documents -U "$user")
  
  if [[ "$docs" == "No documents." ]]; then
    echo "No documents found for user: $user"
    return
  fi
  
  # Count documents
  doc_count=$(echo "$docs" | grep -c "| id")
  echo "Total documents: $doc_count"
  
  # Count by type
  echo -e "\nBy type:"
  echo "$docs" | \
    grep "| kind" | \
    awk '{print $3}' | \
    sort | uniq -c | sort -nr
  
  # Recent documents
  echo -e "\nRecent documents (last 7 days):"
  recent_date=$(date -d "7 days ago" +"%Y-%m-%d")
  echo "$docs" | \
    grep "| time" | \
    awk -v cutoff="$recent_date" '$3 >= cutoff {print $0}'
}

# Generate summary for specific user
user_summary "research-team"
```

### Document Export
```bash
# Export document metadata to CSV
export_to_csv() {
  local output_file="$1"
  
  echo "id,time,title,kind,note,tags" > "$output_file"
  
  tg-show-library-documents | \
    awk '
    BEGIN { record="" }
    /^\+/ { 
      if (record != "") {
        print record
        record=""
      }
    }
    /^\| id/ { gsub(/^\| id *\| /, ""); gsub(/ *\|$/, ""); record=$0"," }
    /^\| time/ { gsub(/^\| time *\| /, ""); gsub(/ *\|$/, ""); record=record$0"," }
    /^\| title/ { gsub(/^\| title *\| /, ""); gsub(/ *\|$/, ""); record=record$0"," }
    /^\| kind/ { gsub(/^\| kind *\| /, ""); gsub(/ *\|$/, ""); record=record$0"," }
    /^\| note/ { gsub(/^\| note *\| /, ""); gsub(/ *\|$/, ""); record=record$0"," }
    /^\| tags/ { gsub(/^\| tags *\| /, ""); gsub(/ *\|$/, ""); record=record$0 }
    END { if (record != "") print record }
    ' >> "$output_file"
  
  echo "Exported to: $output_file"
}

# Export to CSV
export_to_csv "documents.csv"
```

### Document Monitoring
```bash
# Monitor document library changes
monitor_documents() {
  local interval="$1"
  local log_file="document_changes.log"
  
  echo "Monitoring document library (interval: ${interval}s)"
  echo "Log file: $log_file"
  
  # Get initial state
  tg-show-library-documents > last_state.tmp
  
  while true; do
    sleep "$interval"
    
    # Get current state
    tg-show-library-documents > current_state.tmp
    
    # Compare states
    if ! diff -q last_state.tmp current_state.tmp > /dev/null; then
      timestamp=$(date)
      echo "[$timestamp] Document library changed" >> "$log_file"
      
      # Log differences
      diff last_state.tmp current_state.tmp >> "$log_file"
      echo "---" >> "$log_file"
      
      # Update last state
      mv current_state.tmp last_state.tmp
      
      echo "[$timestamp] Changes detected and logged"
    else
      rm current_state.tmp
    fi
  done
}

# Monitor every 60 seconds
monitor_documents 60
```

### Bulk Operations Helper
```bash
# Generate commands for bulk operations
generate_bulk_commands() {
  local operation="$1"
  
  case "$operation" in
    "remove-old")
      echo "# Commands to remove old documents:"
      cutoff_date=$(date -d "90 days ago" +"%Y-%m-%d")
      tg-show-library-documents | \
        grep -B1 "| time.*$cutoff_date" | \
        grep "| id" | \
        awk '{print "tg-remove-library-document --id " $3}'
      ;;
    "process-unprocessed")
      echo "# Commands to process documents:"
      tg-show-library-documents | \
        grep "| id" | \
        awk '{print "tg-start-library-processing -d " $3 " --id proc-" $3}'
      ;;
    *)
      echo "Unknown operation: $operation"
      echo "Available: remove-old, process-unprocessed"
      ;;
  esac
}

# Generate removal commands for old documents
generate_bulk_commands "remove-old"
```

## Integration with Other Commands

### Document Processing Workflow
```bash
# Complete document workflow
process_document_workflow() {
  echo "Document Library Workflow"
  echo "========================"
  
  # 1. List current documents
  echo "Current documents:"
  tg-show-library-documents
  
  # 2. Add new document (example)
  # tg-add-library-document --file new-doc.pdf --title "New Document"
  
  # 3. Start processing
  # tg-start-library-processing -d doc_id --id proc_id
  
  # 4. Monitor processing
  # tg-show-flows | grep processing
  
  # 5. Verify completion
  echo "Documents after processing:"
  tg-show-library-documents
}
```

### Document Lifecycle Management
```bash
# Manage document lifecycle
lifecycle_management() {
  echo "Document Lifecycle Management"
  echo "============================"
  
  # Get all documents
  tg-show-library-documents | \
    grep "| id" | \
    awk '{print $3}' | \
    while read doc_id; do
      echo "Processing document: $doc_id"
      
      # Check if already processed
      if tg-invoke-document-rag -q "test" 2>/dev/null | grep -q "$doc_id"; then
        echo "  Already processed"
      else
        echo "  Starting processing..."
        # tg-start-library-processing -d "$doc_id" --id "proc-$doc_id"
      fi
    done
}
```

## Error Handling

### Connection Issues
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
**Solution**: Check user ID spelling and ensure user exists.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-add-library-document`](tg-add-library-document.md) - Add documents to library
- [`tg-remove-library-document`](tg-remove-library-document.md) - Remove documents from library
- [`tg-start-library-processing`](tg-start-library-processing.md) - Start document processing
- [`tg-stop-library-processing`](tg-stop-library-processing.md) - Stop document processing
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Query processed documents

## API Integration

This command uses the [Library API](../apis/api-librarian.md) to retrieve document metadata and listings.

## Best Practices

1. **Regular Monitoring**: Check library contents regularly
2. **User Organization**: Use different users for different document categories
3. **Tag Consistency**: Maintain consistent tagging schemes
4. **Cleanup**: Regularly remove outdated documents
5. **Backup**: Export document metadata for backup purposes
6. **Access Control**: Use appropriate user permissions
7. **Documentation**: Maintain good document titles and descriptions

## Troubleshooting

### No Documents Shown
```bash
# Check if documents exist for different users
tg-show-library-documents -U "different-user"

# Verify API connectivity
curl -s "$TRUSTGRAPH_URL/api/v1/library/documents" > /dev/null
echo "API response: $?"
```

### Formatting Issues
```bash
# If output is garbled, check terminal width
export COLUMNS=120
tg-show-library-documents
```

### Slow Response
```bash
# For large document libraries, consider filtering by user
tg-show-library-documents -U "specific-user"

# Check system resources
free -h
ps aux | grep trustgraph
```