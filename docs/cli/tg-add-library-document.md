# tg-add-library-document

Adds documents to the TrustGraph library with comprehensive metadata support.

## Synopsis

```bash
tg-add-library-document [options] file1 [file2 ...]
```

## Description

The `tg-add-library-document` command adds documents to the TrustGraph library system, which provides persistent document storage with rich metadata management. Unlike direct document loading, the library approach offers better document lifecycle management, metadata preservation, and processing control.

Documents added to the library can later be processed using `tg-start-library-processing` for controlled batch processing operations.

## Options

### Connection & User
- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User identifier (default: `trustgraph`)

### Document Information
- `--name NAME`: Document name/title
- `--description DESCRIPTION`: Document description
- `--id ID`: Custom document identifier (if not specified, uses content hash)
- `--kind MIMETYPE`: Document MIME type (auto-detected if not specified)
- `--tags TAGS`: Comma-separated list of tags

### Copyright Information
- `--copyright-notice NOTICE`: Copyright notice text
- `--copyright-holder HOLDER`: Copyright holder name
- `--copyright-year YEAR`: Copyright year
- `--license LICENSE`: Copyright license

### Publication Information
- `--publication-organization ORG`: Publishing organization name
- `--publication-description DESC`: Publication description
- `--publication-date DATE`: Publication date
- `--publication-url URL`: Publication URL

### Document Source
- `--document-url URL`: Original document source URL
- `--keyword KEYWORDS`: Document keywords (space-separated)

## Arguments

- `file1 [file2 ...]`: One or more files to add to the library

## Examples

### Basic Document Addition
```bash
tg-add-library-document report.pdf
```

### With Complete Metadata
```bash
tg-add-library-document \
  --name "Annual Research Report 2024" \
  --description "Comprehensive analysis of research outcomes" \
  --copyright-holder "Research Institute" \
  --copyright-year "2024" \
  --license "CC BY 4.0" \
  --tags "research,annual,analysis" \
  --keyword "research" "analysis" "2024" \
  annual-report.pdf
```

### Academic Paper
```bash
tg-add-library-document \
  --name "Machine Learning in Healthcare" \
  --description "Study on ML applications in medical diagnosis" \
  --publication-organization "University Medical School" \
  --publication-date "2024-03-15" \
  --copyright-holder "Dr. Jane Smith" \
  --tags "machine-learning,healthcare,medical" \
  --keyword "ML" "healthcare" "diagnosis" \
  ml-healthcare-paper.pdf
```

### Multiple Documents with Shared Metadata
```bash
tg-add-library-document \
  --publication-organization "Tech Company" \
  --copyright-holder "Tech Company Inc." \
  --copyright-year "2024" \
  --license "Proprietary" \
  --tags "documentation,technical" \
  manual-v1.pdf manual-v2.pdf manual-v3.pdf
```

### Custom Document ID
```bash
tg-add-library-document \
  --id "PROJ-2024-001" \
  --name "Project Specification" \
  --description "Technical requirements document" \
  project-spec.docx
```

## Document Processing

1. **File Reading**: Reads document content as binary data
2. **ID Generation**: Creates SHA256 hash-based ID (unless custom ID provided)
3. **Metadata Assembly**: Combines all metadata into structured format
4. **Library Storage**: Stores document and metadata in library system
5. **URI Creation**: Generates TrustGraph document URI

## Document ID Generation

- **Automatic**: SHA256 hash of file content converted to TrustGraph URI
- **Custom**: Use `--id` parameter for specific identifiers
- **Format**: `http://trustgraph.ai/d/[hash-or-custom-id]`

## MIME Type Detection

The system automatically detects document types:
- **PDF**: `application/pdf`
- **Word**: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- **Text**: `text/plain`
- **HTML**: `text/html`

Override with `--kind` parameter if needed.

## Metadata Format

Metadata is stored as RDF triples including:

### Dublin Core Properties
- `dc:title`: Document name
- `dc:description`: Document description
- `dc:creator`: Copyright holder
- `dc:date`: Publication date
- `dc:rights`: Copyright notice
- `dc:license`: License information
- `dc:subject`: Keywords and tags

### Organization Information
- `foaf:Organization`: Publisher details
- `foaf:name`: Organization name
- `vcard:hasURL`: Organization website

### Document Properties
- `bibo:doi`: DOI if applicable
- `bibo:url`: Document source URL

## Output

For each successfully added document:
```bash
report.pdf: Loaded successfully.
```

For failures:
```bash
invalid.pdf: Failed: File not found
```

## Error Handling

### File Errors
```bash
document.pdf: Failed: No such file or directory
```
**Solution**: Verify file path exists and is readable.

### Permission Errors
```bash
document.pdf: Failed: Permission denied
```
**Solution**: Check file permissions and user access rights.

### Connection Errors
```bash
document.pdf: Failed: Connection refused
```
**Solution**: Verify API URL and ensure TrustGraph is running.

### Library Errors
```bash
document.pdf: Failed: Document already exists
```
**Solution**: Use different ID or update existing document.

## Library Management Workflow

### 1. Add Documents
```bash
tg-add-library-document research-paper.pdf
```

### 2. Verify Addition
```bash
tg-show-library-documents
```

### 3. Start Processing
```bash
tg-start-library-processing --flow-id research-flow
```

### 4. Monitor Processing
```bash
tg-show-library-processing
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-library-documents`](tg-show-library-documents.md) - List library documents
- [`tg-remove-library-document`](tg-remove-library-document.md) - Remove documents from library
- [`tg-start-library-processing`](tg-start-library-processing.md) - Process library documents
- [`tg-stop-library-processing`](tg-stop-library-processing.md) - Stop library processing
- [`tg-show-library-processing`](tg-show-library-processing.md) - Show processing status

## API Integration

This command uses the [Librarian API](../apis/api-librarian.md) with the `add-document` operation to store documents with metadata.

## Use Cases

### Research Document Management
```bash
tg-add-library-document \
  --name "Climate Change Analysis" \
  --publication-organization "Climate Research Institute" \
  --tags "climate,research,environment" \
  climate-study.pdf
```

### Corporate Documentation
```bash
tg-add-library-document \
  --name "Product Manual v2.1" \
  --copyright-holder "Acme Corporation" \
  --license "Proprietary" \
  --tags "manual,product,v2.1" \
  product-manual.pdf
```

### Legal Document Archive
```bash
tg-add-library-document \
  --name "Contract Template" \
  --description "Standard service agreement template" \
  --copyright-holder "Legal Department" \
  --tags "legal,contract,template" \
  contract-template.docx
```

### Academic Paper Collection
```bash
tg-add-library-document \
  --publication-organization "IEEE" \
  --copyright-year "2024" \
  --tags "academic,ieee,conference" \
  paper1.pdf paper2.pdf paper3.pdf
```

## Best Practices

1. **Consistent Metadata**: Use standardized metadata fields for better organization
2. **Meaningful Tags**: Add relevant tags for document discovery
3. **Copyright Information**: Include complete copyright details for legal compliance
4. **Batch Operations**: Process related documents together with shared metadata
5. **Version Control**: Use clear naming and tagging for document versions
6. **Library Organization**: Use collections and user assignments for multi-tenant systems

## Advantages over Direct Loading

### Library Benefits
- **Persistent Storage**: Documents preserved in library system
- **Metadata Management**: Rich metadata storage and querying
- **Processing Control**: Controlled batch processing with start/stop
- **Document Lifecycle**: Full document management capabilities
- **Search and Discovery**: Better document organization and retrieval

### When to Use Library vs Direct Loading
- **Use Library**: For document management, metadata preservation, controlled processing
- **Use Direct Loading**: For immediate processing, simple workflows, temporary documents