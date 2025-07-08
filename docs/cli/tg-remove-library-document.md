# tg-remove-library-document

Removes a document from the TrustGraph document library.

## Synopsis

```bash
tg-remove-library-document --id DOCUMENT_ID [options]
```

## Description

The `tg-remove-library-document` command permanently removes a document from TrustGraph's document library. This operation deletes the document metadata, content, and any associated processing records.

**⚠️ Warning**: This operation is permanent and cannot be undone. Ensure you have backups if the document data is important.

## Options

### Required Arguments

- `--identifier, --id ID`: Document ID to remove

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User ID (default: `trustgraph`)

## Examples

### Remove Single Document
```bash
tg-remove-library-document --id "doc_123456789"
```

### Remove with Custom User
```bash
tg-remove-library-document --id "doc_987654321" -U "research-team"
```

### Remove with Custom API URL
```bash
tg-remove-library-document --id "doc_555" -u http://staging:8088/
```

## Prerequisites

### Document Must Exist
Verify the document exists before attempting removal:

```bash
# List documents to find the ID
tg-show-library-documents

# Search for specific document
tg-show-library-documents | grep "doc_123456789"
```

### Check for Active Processing
Before removing a document, check if it's currently being processed:

```bash
# Check for active processing jobs
tg-show-flows | grep "processing"

# Stop any active processing first
# tg-stop-library-processing --id "processing_id"
```

## Use Cases

### Cleanup Old Documents
```bash
# Remove outdated documents
old_docs=("doc_old1" "doc_old2" "doc_deprecated")
for doc_id in "${old_docs[@]}"; do
  echo "Removing $doc_id..."
  tg-remove-library-document --id "$doc_id"
done
```

### Remove Test Documents
```bash
# Remove test documents after development
tg-show-library-documents | \
  grep "test\|demo\|sample" | \
  grep "| id" | \
  awk '{print $3}' | \
  while read doc_id; do
    echo "Removing test document: $doc_id"
    tg-remove-library-document --id "$doc_id"
  done
```

### User-Specific Cleanup
```bash
# Remove all documents for a specific user
cleanup_user_documents() {
  local user="$1"
  
  echo "Removing all documents for user: $user"
  
  # Get document IDs for the user
  tg-show-library-documents -U "$user" | \
    grep "| id" | \
    awk '{print $3}' | \
    while read doc_id; do
      echo "Removing document: $doc_id"
      tg-remove-library-document --id "$doc_id" -U "$user"
    done
}

# Usage
cleanup_user_documents "temp-user"
```

### Conditional Removal
```bash
# Remove documents based on criteria
remove_by_criteria() {
  local criteria="$1"
  
  echo "Removing documents matching criteria: $criteria"
  
  tg-show-library-documents | \
    grep -B5 -A5 "$criteria" | \
    grep "| id" | \
    awk '{print $3}' | \
    while read doc_id; do
      # Confirm before removal
      echo -n "Remove document $doc_id? (y/N): "
      read confirm
      if [[ "$confirm" =~ ^[Yy]$ ]]; then
        tg-remove-library-document --id "$doc_id"
        echo "Removed: $doc_id"
      else
        echo "Skipped: $doc_id"
      fi
    done
}

# Remove documents containing "draft" in title
remove_by_criteria "draft"
```

## Safety Procedures

### Backup Before Removal
```bash
# Create backup of document metadata before removal
backup_document() {
  local doc_id="$1"
  local backup_dir="document_backups/$(date +%Y%m%d)"
  
  mkdir -p "$backup_dir"
  
  echo "Backing up document: $doc_id"
  
  # Get document metadata
  tg-show-library-documents | \
    grep -A10 -B2 "$doc_id" > "$backup_dir/$doc_id.metadata"
  
  # Note: Actual document content backup would require additional API
  echo "Backup saved: $backup_dir/$doc_id.metadata"
}

# Backup then remove
safe_remove() {
  local doc_id="$1"
  
  backup_document "$doc_id"
  
  echo "Removing document: $doc_id"
  tg-remove-library-document --id "$doc_id"
  
  echo "Document removed: $doc_id"
}

# Usage
safe_remove "doc_123456789"
```

### Verification Script
```bash
#!/bin/bash
# safe-remove-document.sh
doc_id="$1"
user="${2:-trustgraph}"

if [ -z "$doc_id" ]; then
    echo "Usage: $0 <document-id> [user]"
    exit 1
fi

echo "Safety checks for removing document: $doc_id"

# Check if document exists
if ! tg-show-library-documents -U "$user" | grep -q "$doc_id"; then
    echo "ERROR: Document '$doc_id' not found for user '$user'"
    exit 1
fi

# Show document details
echo "Document details:"
tg-show-library-documents -U "$user" | grep -A10 -B2 "$doc_id"

# Check for active processing
echo "Checking for active processing..."
active_processing=$(tg-show-flows | grep -c "processing.*$doc_id" || echo "0")
if [ "$active_processing" -gt 0 ]; then
    echo "WARNING: Document has $active_processing active processing jobs"
    echo "Consider stopping processing first"
fi

# Confirm removal
echo ""
read -p "Are you sure you want to remove this document? (y/N): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    echo "Removing document..."
    tg-remove-library-document --id "$doc_id" -U "$user"
    
    # Verify removal
    if ! tg-show-library-documents -U "$user" | grep -q "$doc_id"; then
        echo "Document removed successfully"
    else
        echo "ERROR: Document still exists after removal"
        exit 1
    fi
else
    echo "Removal cancelled"
fi
```

### Bulk Removal with Confirmation
```bash
# Remove multiple documents with individual confirmation
bulk_remove_with_confirmation() {
  local doc_list="$1"
  
  if [ ! -f "$doc_list" ]; then
    echo "Usage: $0 <file-with-document-ids>"
    return 1
  fi
  
  echo "Bulk removal with confirmation"
  echo "Document list: $doc_list"
  echo "=============================="
  
  while IFS= read -r doc_id; do
    if [ -n "$doc_id" ]; then
      # Show document info
      echo -e "\nDocument ID: $doc_id"
      tg-show-library-documents | grep -A5 -B1 "$doc_id" | grep -E "title|note|tags"
      
      # Confirm removal
      echo -n "Remove this document? (y/N/q): "
      read confirm
      
      case "$confirm" in
        y|Y)
          tg-remove-library-document --id "$doc_id"
          echo "Removed: $doc_id"
          ;;
        q|Q)
          echo "Quitting bulk removal"
          break
          ;;
        *)
          echo "Skipped: $doc_id"
          ;;
      esac
    fi
  done < "$doc_list"
}

# Create list of documents to remove
echo -e "doc_123\ndoc_456\ndoc_789" > remove_list.txt
bulk_remove_with_confirmation "remove_list.txt"
```

## Advanced Usage

### Age-Based Removal
```bash
# Remove documents older than specified days
remove_old_documents() {
  local days_old="$1"
  local dry_run="${2:-false}"
  
  if [ -z "$days_old" ]; then
    echo "Usage: remove_old_documents <days> [dry_run]"
    return 1
  fi
  
  cutoff_date=$(date -d "$days_old days ago" +"%Y-%m-%d")
  echo "Removing documents older than $cutoff_date"
  
  tg-show-library-documents | \
    awk -v cutoff="$cutoff_date" -v dry="$dry_run" '
    /^\| id/ { id = $3 }
    /^\| time/ { 
      if ($3 < cutoff) {
        if (dry == "true") {
          print "Would remove: " id " (date: " $3 ")"
        } else {
          system("tg-remove-library-document --id " id)
          print "Removed: " id " (date: " $3 ")"
        }
      }
    }'
}

# Dry run first
remove_old_documents 90 true

# Actually remove
remove_old_documents 90 false
```

### Size-Based Cleanup
```bash
# Remove documents based on collection size limits
cleanup_by_collection_size() {
  local max_docs="$1"
  
  echo "Maintaining maximum $max_docs documents per user"
  
  # Get unique users
  users=$(tg-show-library-documents | grep "| id" | awk '{print $3}' | sort | uniq)
  
  for user in $users; do
    echo "Checking user: $user"
    
    # Count documents for user
    doc_count=$(tg-show-library-documents -U "$user" | grep -c "| id")
    
    if [ "$doc_count" -gt "$max_docs" ]; then
      excess=$((doc_count - max_docs))
      echo "User $user has $doc_count documents (removing $excess oldest)"
      
      # Get oldest documents (by time)
      tg-show-library-documents -U "$user" | \
        awk '
        /^\| id/ { id = $3 }
        /^\| time/ { print $3 " " id }
        ' | \
        sort | \
        head -n "$excess" | \
        while read date doc_id; do
          echo "Removing old document: $doc_id ($date)"
          tg-remove-library-document --id "$doc_id" -U "$user"
        done
    else
      echo "User $user has $doc_count documents (within limit)"
    fi
  done
}

# Maintain maximum 100 documents per user
cleanup_by_collection_size 100
```

### Pattern-Based Removal
```bash
# Remove documents matching specific patterns
remove_by_pattern() {
  local pattern="$1"
  local field="${2:-title}"
  
  echo "Removing documents with '$pattern' in $field"
  
  tg-show-library-documents | \
    awk -v pattern="$pattern" -v field="$field" '
    /^\| id/ { id = $3 }
    /^\| title/ && field=="title" { if ($0 ~ pattern) print id }
    /^\| note/ && field=="note" { if ($0 ~ pattern) print id }
    /^\| tags/ && field=="tags" { if ($0 ~ pattern) print id }
    ' | \
    while read doc_id; do
      echo "Removing document: $doc_id"
      tg-remove-library-document --id "$doc_id"
    done
}

# Remove all test documents
remove_by_pattern "test" "title"
remove_by_pattern "temp" "tags"
```

## Error Handling

### Document Not Found
```bash
Exception: Document not found
```
**Solution**: Verify document ID exists with `tg-show-library-documents`.

### Permission Errors
```bash
Exception: Access denied
```
**Solution**: Check user permissions and document ownership.

### Active Processing
```bash
Exception: Cannot remove document with active processing
```
**Solution**: Stop processing with `tg-stop-library-processing` before removal.

### API Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Check API URL and ensure TrustGraph is running.

## Monitoring and Logging

### Removal Logging
```bash
# Log all removals
logged_remove() {
  local doc_id="$1"
  local log_file="document_removals.log"
  
  timestamp=$(date)
  echo "[$timestamp] Removing document: $doc_id" >> "$log_file"
  
  # Get document info before removal
  tg-show-library-documents | \
    grep -A5 -B1 "$doc_id" >> "$log_file"
  
  # Remove document
  if tg-remove-library-document --id "$doc_id"; then
    echo "[$timestamp] Successfully removed: $doc_id" >> "$log_file"
  else
    echo "[$timestamp] Failed to remove: $doc_id" >> "$log_file"
  fi
  
  echo "---" >> "$log_file"
}

# Usage
logged_remove "doc_123456789"
```

### Audit Trail
```bash
# Create audit trail for removals
create_removal_audit() {
  local doc_id="$1"
  local reason="$2"
  local audit_file="removal_audit.csv"
  
  # Create header if file doesn't exist
  if [ ! -f "$audit_file" ]; then
    echo "timestamp,document_id,user,reason,status" > "$audit_file"
  fi
  
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  user=$(whoami)
  
  # Attempt removal
  if tg-remove-library-document --id "$doc_id"; then
    status="success"
  else
    status="failed"
  fi
  
  # Log to audit file
  echo "$timestamp,$doc_id,$user,$reason,$status" >> "$audit_file"
}

# Usage
create_removal_audit "doc_123" "Outdated content"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-library-documents`](tg-show-library-documents.md) - List library documents
- [`tg-add-library-document`](tg-add-library-document.md) - Add documents to library
- [`tg-start-library-processing`](tg-start-library-processing.md) - Start document processing
- [`tg-stop-library-processing`](tg-stop-library-processing.md) - Stop document processing

## API Integration

This command uses the [Library API](../apis/api-librarian.md) to remove documents from the document repository.

## Best Practices

1. **Always Backup**: Create backups before removing important documents
2. **Verification**: Verify document existence before removal attempts
3. **Processing Check**: Ensure no active processing before removal
4. **Audit Trail**: Maintain logs of all removal operations
5. **Confirmation**: Use interactive confirmation for bulk operations
6. **Testing**: Test removal procedures in non-production environments
7. **Access Control**: Ensure appropriate permissions for removal operations

## Troubleshooting

### Document Still Exists After Removal
```bash
# Verify removal
tg-show-library-documents | grep "document-id"

# Check for caching issues
# Wait a moment and try again

# Verify API connectivity
curl -s "$TRUSTGRAPH_URL/api/v1/library/documents" > /dev/null
```

### Permission Issues
```bash
# Check user permissions
tg-show-library-documents -U "your-user" | grep "document-id"

# Verify user ownership of document
```

### Cannot Remove Due to References
```bash
# Check for document references in processing jobs
tg-show-flows | grep "document-id"

# Stop any referencing processes first
```