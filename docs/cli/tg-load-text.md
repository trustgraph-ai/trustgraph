# tg-load-text

Loads text documents into TrustGraph processing pipelines with rich metadata support.

## Synopsis

```bash
tg-load-text [options] file1 [file2 ...]
```

## Description

The `tg-load-text` command loads text documents into TrustGraph for processing. It creates a SHA256 hash-based document ID and supports comprehensive metadata including copyright information, publication details, and keywords.

**Note**: Consider using `tg-add-library-document` followed by `tg-start-library-processing` for better document management and processing control.

## Options

### Connection & Flow
- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-f, --flow-id FLOW`: Flow ID for processing (default: `default`)
- `-U, --user USER`: User identifier (default: `trustgraph`)
- `-C, --collection COLLECTION`: Collection identifier (default: `default`)

### Document Metadata
- `--name NAME`: Document name/title
- `--description DESCRIPTION`: Document description
- `--document-url URL`: Document source URL

### Copyright Information
- `--copyright-notice NOTICE`: Copyright notice text
- `--copyright-holder HOLDER`: Copyright holder name
- `--copyright-year YEAR`: Copyright year
- `--license LICENSE`: Copyright license

### Publication Information
- `--publication-organization ORG`: Publishing organization
- `--publication-description DESC`: Publication description
- `--publication-date DATE`: Publication date

### Keywords
- `--keyword KEYWORD [KEYWORD ...]`: Document keywords (can specify multiple)

## Arguments

- `file1 [file2 ...]`: One or more text files to load

## Examples

### Basic Document Loading
```bash
tg-load-text document.txt
```

### Loading with Metadata
```bash
tg-load-text \
  --name "Research Paper on AI" \
  --description "Comprehensive study of machine learning algorithms" \
  --keyword "AI" "machine learning" "research" \
  research-paper.txt
```

### Complete Metadata Example
```bash
tg-load-text \
  --name "TrustGraph Documentation" \
  --description "Complete user guide for TrustGraph system" \
  --copyright-holder "TrustGraph Project" \
  --copyright-year "2024" \
  --license "MIT" \
  --publication-organization "TrustGraph Foundation" \
  --publication-date "2024-01-15" \
  --keyword "documentation" "guide" "tutorial" \
  --flow-id research-flow \
  trustgraph-guide.txt
```

### Multiple Files
```bash
tg-load-text chapter1.txt chapter2.txt chapter3.txt
```

### Custom Flow and Collection
```bash
tg-load-text \
  --flow-id medical-research \
  --user researcher \
  --collection medical-papers \
  medical-study.txt
```

## Output

For each file processed, the command outputs:

### Success
```
document.txt: Loaded successfully.
```

### Failure
```
document.txt: Failed: Connection refused
```

## Document Processing

1. **File Reading**: Reads the text file content
2. **Hash Generation**: Creates SHA256 hash for unique document ID
3. **URI Creation**: Converts hash to document URI format
4. **Metadata Assembly**: Combines all metadata into RDF triples
5. **API Submission**: Sends to TrustGraph via Text Load API

## Document ID Generation

Documents are assigned IDs based on their content hash:
- SHA256 hash of file content
- Converted to TrustGraph document URI format
- Example: `http://trustgraph.ai/d/abc123...`

## Metadata Format

The metadata is stored as RDF triples including:

### Standard Properties
- `dc:title`: Document name
- `dc:description`: Document description  
- `dc:creator`: Copyright holder
- `dc:date`: Publication date
- `dc:rights`: Copyright notice
- `dc:license`: License information

### Keywords
- `dc:subject`: Each keyword as separate triple

### Organization Information
- `foaf:Organization`: Publication organization details

## Error Handling

### File Errors
```bash
document.txt: Failed: No such file or directory
```
**Solution**: Verify the file path exists and is readable.

### Connection Errors
```bash
document.txt: Failed: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Flow Errors
```bash
document.txt: Failed: Invalid flow
```
**Solution**: Verify the flow exists and is running using `tg-show-flows`.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-add-library-document`](tg-add-library-document.md) - Add documents to library (recommended)
- [`tg-load-pdf`](tg-load-pdf.md) - Load PDF documents
- [`tg-show-library-documents`](tg-show-library-documents.md) - List loaded documents
- [`tg-start-library-processing`](tg-start-library-processing.md) - Start document processing

## API Integration

This command uses the [Text Load API](../apis/api-text-load.md) to submit documents for processing. The text content is base64-encoded for transmission.

## Use Cases

### Academic Research
```bash
tg-load-text \
  --name "Climate Change Impact Study" \
  --publication-organization "University Research Center" \
  --keyword "climate" "research" "environment" \
  climate-study.txt
```

### Corporate Documentation
```bash
tg-load-text \
  --name "Product Manual" \
  --copyright-holder "Acme Corp" \
  --license "Proprietary" \
  --keyword "manual" "product" "guide" \
  product-manual.txt
```

### Technical Documentation
```bash
tg-load-text \
  --name "API Reference" \
  --description "Complete API documentation" \
  --keyword "API" "reference" "technical" \
  api-docs.txt
```

## Best Practices

1. **Use Descriptive Names**: Provide clear document names and descriptions
2. **Add Keywords**: Include relevant keywords for better searchability
3. **Complete Metadata**: Fill in copyright and publication information
4. **Batch Processing**: Load multiple related files together
5. **Use Collections**: Organize documents by topic or project using collections