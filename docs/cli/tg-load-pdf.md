# tg-load-pdf

Loads PDF documents into TrustGraph for processing and analysis.

## Synopsis

```bash
tg-load-pdf [options] file1.pdf [file2.pdf ...]
```

## Description

The `tg-load-pdf` command loads PDF documents into TrustGraph by directing them to the PDF decoder service. The command extracts content, generates document metadata, and makes the documents available for processing by other TrustGraph services.

Each PDF is assigned a unique identifier based on its content hash, and comprehensive metadata can be attached including copyright information, publication details, and keywords.

**Note**: Consider using `tg-add-library-document` followed by `tg-start-library-processing` for more comprehensive document management.

## Options

### Required Arguments

- `files`: One or more PDF files to load

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-f, --flow-id ID`: Flow instance ID to use (default: `default`)
- `-U, --user USER`: User ID for document ownership (default: `trustgraph`)
- `-C, --collection COLLECTION`: Collection to assign document (default: `default`)

### Document Metadata

- `--name NAME`: Document name/title
- `--description DESCRIPTION`: Document description
- `--identifier ID`: Custom document identifier
- `--document-url URL`: Source URL for the document
- `--keyword KEYWORD`: Document keywords (can be specified multiple times)

### Copyright Information

- `--copyright-notice NOTICE`: Copyright notice text
- `--copyright-holder HOLDER`: Copyright holder name
- `--copyright-year YEAR`: Copyright year
- `--license LICENSE`: Copyright license

### Publication Details

- `--publication-organization ORG`: Publishing organization
- `--publication-description DESC`: Publication description
- `--publication-date DATE`: Publication date

## Examples

### Basic PDF Loading
```bash
tg-load-pdf document.pdf
```

### Multiple Files
```bash
tg-load-pdf report1.pdf report2.pdf manual.pdf
```

### With Basic Metadata
```bash
tg-load-pdf \
  --name "Technical Manual" \
  --description "System administration guide" \
  --keyword "technical" --keyword "manual" \
  technical-manual.pdf
```

### Complete Metadata
```bash
tg-load-pdf \
  --name "Annual Report 2023" \
  --description "Company annual financial report" \
  --copyright-holder "Acme Corporation" \
  --copyright-year "2023" \
  --license "All Rights Reserved" \
  --publication-organization "Acme Corporation" \
  --publication-date "2023-12-31" \
  --keyword "financial" --keyword "annual" --keyword "report" \
  annual-report-2023.pdf
```

### Custom Flow and Collection
```bash
tg-load-pdf \
  -f "document-processing-flow" \
  -U "finance-team" \
  -C "financial-documents" \
  --name "Budget Analysis" \
  budget-2024.pdf
```

## Document Processing

### Content Extraction
The PDF loader:
1. Calculates SHA256 hash for unique document ID
2. Extracts text content from PDF
3. Preserves document structure and formatting metadata
4. Generates searchable text index

### Metadata Generation
Document metadata includes:
- **Document ID**: SHA256 hash-based unique identifier
- **Content Hash**: For duplicate detection
- **File Information**: Size, format, creation date
- **Custom Metadata**: User-provided attributes

### Integration with Processing Pipeline
```bash
# Load PDF and start processing
tg-load-pdf research-paper.pdf --name "AI Research Paper"

# Check processing status
tg-show-flows | grep "document-processing"

# Query loaded content
tg-invoke-document-rag -q "What is the main conclusion?" -C "default"
```

## Error Handling

### File Not Found
```bash
Exception: [Errno 2] No such file or directory: 'missing.pdf'
```
**Solution**: Verify file path and ensure PDF exists.

### Invalid PDF Format
```bash
Exception: PDF parsing failed: Invalid PDF structure
```
**Solution**: Verify PDF is not corrupted and is a valid PDF file.

### Permission Errors
```bash
Exception: [Errno 13] Permission denied: 'protected.pdf'
```
**Solution**: Check file permissions and ensure read access.

### Flow Not Found
```bash
Exception: Flow instance 'invalid-flow' not found
```
**Solution**: Verify flow ID exists with `tg-show-flows`.

### API Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Check API URL and ensure TrustGraph is running.

## Advanced Usage

### Batch Processing
```bash
# Process all PDFs in directory
for pdf in *.pdf; do
  echo "Loading $pdf..."
  tg-load-pdf \
    --name "$(basename "$pdf" .pdf)" \
    --collection "research-papers" \
    "$pdf"
done
```

### Organized Loading
```bash
# Load with structured metadata
categories=("technical" "financial" "legal")
for category in "${categories[@]}"; do
  for pdf in "$category"/*.pdf; do
    if [ -f "$pdf" ]; then
      tg-load-pdf \
        --collection "$category-documents" \
        --keyword "$category" \
        --name "$(basename "$pdf" .pdf)" \
        "$pdf"
    fi
  done
done
```

### CSV-Driven Loading
```bash
# Load PDFs with metadata from CSV
# Format: filename,title,description,keywords
while IFS=',' read -r filename title description keywords; do
  if [ -f "$filename" ]; then
    echo "Loading $filename..."
    
    # Convert comma-separated keywords to multiple --keyword args
    keyword_args=""
    IFS='|' read -ra KEYWORDS <<< "$keywords"
    for kw in "${KEYWORDS[@]}"; do
      keyword_args="$keyword_args --keyword \"$kw\""
    done
    
    eval "tg-load-pdf \
      --name \"$title\" \
      --description \"$description\" \
      $keyword_args \
      \"$filename\""
  fi
done < documents.csv
```

### Publication Processing
```bash
# Load academic papers with publication details
load_academic_paper() {
    local file="$1"
    local title="$2"
    local authors="$3"
    local journal="$4"
    local year="$5"
    
    tg-load-pdf \
      --name "$title" \
      --description "Academic paper: $title" \
      --copyright-holder "$authors" \
      --copyright-year "$year" \
      --publication-organization "$journal" \
      --publication-date "$year-01-01" \
      --keyword "academic" --keyword "research" \
      "$file"
}

# Usage
load_academic_paper "ai-paper.pdf" "AI in Healthcare" "Smith et al." "AI Journal" "2023"
```

## Monitoring and Validation

### Load Status Checking
```bash
# Check document loading progress
check_load_status() {
    local file="$1"
    local expected_name="$2"
    
    echo "Checking load status for: $file"
    
    # Check if document appears in library
    if tg-show-library-documents | grep -q "$expected_name"; then
        echo "✓ Document loaded successfully"
    else
        echo "✗ Document not found in library"
        return 1
    fi
}

# Monitor batch loading
for pdf in *.pdf; do
    name=$(basename "$pdf" .pdf)
    check_load_status "$pdf" "$name"
done
```

### Content Verification
```bash
# Verify PDF content is accessible
verify_pdf_content() {
    local pdf_name="$1"
    local test_query="$2"
    
    echo "Verifying content for: $pdf_name"
    
    # Try to query the document
    result=$(tg-invoke-document-rag -q "$test_query" -C "default" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$result" ]; then
        echo "✓ Content accessible via RAG"
    else
        echo "✗ Content not accessible"
        return 1
    fi
}

# Verify loaded documents
verify_pdf_content "Technical Manual" "What is the installation process?"
```

## Performance Optimization

### Parallel Loading
```bash
# Load multiple PDFs in parallel
pdf_files=(document1.pdf document2.pdf document3.pdf)
for pdf in "${pdf_files[@]}"; do
    (
        echo "Loading $pdf in background..."
        tg-load-pdf \
          --name "$(basename "$pdf" .pdf)" \
          --collection "batch-$(date +%Y%m%d)" \
          "$pdf"
    ) &
done
wait
echo "All PDFs loaded"
```

### Size-Based Processing
```bash
# Process files based on size
for pdf in *.pdf; do
    size=$(stat -c%s "$pdf")
    if [ $size -lt 10485760 ]; then  # < 10MB
        echo "Processing small file: $pdf"
        tg-load-pdf --collection "small-docs" "$pdf"
    else
        echo "Processing large file: $pdf"
        tg-load-pdf --collection "large-docs" "$pdf"
    fi
done
```

## Document Organization

### Collection Management
```bash
# Organize by document type
organize_by_type() {
    local pdf="$1"
    local filename=$(basename "$pdf" .pdf)
    
    case "$filename" in
        *manual*|*guide*) collection="manuals" ;;
        *report*|*analysis*) collection="reports" ;;
        *spec*|*specification*) collection="specifications" ;;
        *legal*|*contract*) collection="legal" ;;
        *) collection="general" ;;
    esac
    
    tg-load-pdf \
      --collection "$collection" \
      --name "$filename" \
      "$pdf"
}

# Process all PDFs
for pdf in *.pdf; do
    organize_by_type "$pdf"
done
```

### Metadata Standardization
```bash
# Apply consistent metadata standards
standardize_metadata() {
    local pdf="$1"
    local dept="$2"
    local year="$3"
    
    local name=$(basename "$pdf" .pdf)
    local collection="$dept-$(date +%Y)"
    
    tg-load-pdf \
      --name "$name" \
      --description "$dept document from $year" \
      --copyright-holder "Company Name" \
      --copyright-year "$year" \
      --collection "$collection" \
      --keyword "$dept" --keyword "$year" \
      "$pdf"
}

# Usage
standardize_metadata "finance-report.pdf" "finance" "2023"
```

## Integration with Other Services

### Library Integration
```bash
# Alternative approach using library services
load_via_library() {
    local pdf="$1"
    local name="$2"
    
    # Add to library first
    tg-add-library-document \
      --name "$name" \
      --file "$pdf" \
      --collection "documents"
    
    # Start processing
    tg-start-library-processing \
      --collection "documents"
}
```

### Workflow Integration
```bash
# Complete document workflow
process_document_workflow() {
    local pdf="$1"
    local name="$2"
    
    echo "Starting document workflow for: $name"
    
    # 1. Load PDF
    tg-load-pdf --name "$name" "$pdf"
    
    # 2. Wait for processing
    sleep 5
    
    # 3. Verify availability
    if tg-show-library-documents | grep -q "$name"; then
        echo "Document available in library"
        
        # 4. Test RAG functionality
        tg-invoke-document-rag -q "What is this document about?"
        
        # 5. Extract key information
        tg-invoke-prompt extract-key-points \
          text="Document: $name" \
          format="bullet_points"
    else
        echo "Document processing failed"
    fi
}
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-add-library-document`](tg-add-library-document.md) - Add documents to library
- [`tg-start-library-processing`](tg-start-library-processing.md) - Process library documents
- [`tg-show-library-documents`](tg-show-library-documents.md) - List library documents
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Query document content
- [`tg-show-flows`](tg-show-flows.md) - Monitor processing flows

## API Integration

This command uses the document loading API to process PDF files and make them available for text extraction, search, and analysis.

## Best Practices

1. **Metadata Completeness**: Provide comprehensive metadata for better organization
2. **Collection Organization**: Use logical collections for document categorization
3. **Error Handling**: Implement robust error handling for batch operations
4. **Performance**: Consider file sizes and processing capacity
5. **Monitoring**: Verify successful loading and processing
6. **Security**: Ensure sensitive documents are properly protected
7. **Backup**: Maintain backups of source PDFs

## Troubleshooting

### PDF Processing Issues
```bash
# Check PDF validity
file document.pdf
pdfinfo document.pdf

# Try alternative PDF processors
qpdf --check document.pdf
```

### Memory Issues
```bash
# For large PDFs, monitor memory usage
free -h
# Consider processing large files separately
```

### Content Extraction Problems
```bash
# Verify PDF contains extractable text
pdftotext document.pdf test-output.txt
cat test-output.txt | head -20
```