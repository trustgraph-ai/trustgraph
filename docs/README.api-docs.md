
# Auto-generating docs

## REST and WebSocket API Documentation

- `specs/build-docs.sh` - Builds the REST and websocket documentation from the
  OpenAPI and AsyncAPI specs.

## Python API Documentation

The Python API documentation is generated from docstrings using a custom Python script that introspects the `trustgraph.api` package.

### Prerequisites

The trustgraph package must be importable. If you're working in a development environment:

```bash
cd trustgraph-base
pip install -e .
```

### Generating Documentation

From the docs directory:

```bash
cd docs
python3 generate-api-docs.py > python-api.md
```

This generates a single markdown file with complete API documentation showing:
- Installation and quick start guide
- Import statements for each class/type
- Full docstrings with examples
- Table of contents organized by category

### Documentation Style

All docstrings follow Google-style format:
- Brief one-line summary
- Detailed description
- Args section with parameter descriptions
- Returns section
- Raises section (when applicable)
- Example code blocks with proper syntax highlighting

The generated documentation shows the public API exactly as users import it from `trustgraph.api`, without exposing internal module structure.

