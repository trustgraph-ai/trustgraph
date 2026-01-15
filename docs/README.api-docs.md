
# Auto-generating docs

## REST and WebSocket API Documentation

- `specs/build-docs.sh` - Builds the REST and websocket documentation from the
  OpenAPI and AsyncAPI specs.

## Python API Documentation

The Python API documentation is generated from docstrings using `pydoc-markdown`.

### Prerequisites

Install pydoc-markdown:
```bash
pip install pydoc-markdown
```

### Generating Documentation

From the repository root directory:

```bash
cd /path/to/trustgraph
pydoc-markdown docs/pydoc-markdown.yml > docs/python-api.md
```

This generates a single markdown file with complete API documentation.

### Configuration

All docstrings follow Google-style format for optimal markdown rendering:
- Brief one-line summary
- Detailed description
- Args section with parameter descriptions
- Returns section
- Raises section (when applicable)
- Example code blocks

