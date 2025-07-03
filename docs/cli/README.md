# TrustGraph CLI Documentation

The TrustGraph Command Line Interface (CLI) provides comprehensive command-line access to all TrustGraph services. These tools wrap the REST and WebSocket APIs to provide convenient, scriptable access to TrustGraph functionality.

## Installation

The CLI tools are installed as part of the `trustgraph-cli` package:

```bash
pip install trustgraph-cli
```

## Global Options

Most CLI commands support these common options:

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User identifier (default: `trustgraph`)
- `-C, --collection COLLECTION`: Collection identifier (default: `default`)
- `-f, --flow-id FLOW`: Flow identifier (default: `default`)

## Command Categories

### System Administration & Configuration

**System Setup:**
- [`tg-init-trustgraph`](tg-init-trustgraph.md) - Initialize Pulsar with TrustGraph configuration
- [`tg-init-pulsar-manager`](tg-init-pulsar-manager.md) - Initialize Pulsar manager setup
- [`tg-show-config`](tg-show-config.md) - Display current system configuration

**Token Management:**
- [`tg-set-token-costs`](tg-set-token-costs.md) - Configure model token costs
- [`tg-show-token-costs`](tg-show-token-costs.md) - Display token cost configuration
- [`tg-show-token-rate`](tg-show-token-rate.md) - Show token usage rates

### Flow Management

**Flow Operations:**
- [`tg-start-flow`](tg-start-flow.md) - Start a processing flow
- [`tg-stop-flow`](tg-stop-flow.md) - Stop a running flow
- [`tg-show-flows`](tg-show-flows.md) - List all configured flows
- [`tg-show-flow-state`](tg-show-flow-state.md) - Show current flow states

**Flow Class Management:**
- [`tg-put-flow-class`](tg-put-flow-class.md) - Upload/update flow class definition
- [`tg-get-flow-class`](tg-get-flow-class.md) - Retrieve flow class definition
- [`tg-delete-flow-class`](tg-delete-flow-class.md) - Remove flow class definition
- [`tg-show-flow-classes`](tg-show-flow-classes.md) - List available flow classes

### Knowledge Graph Management

**Knowledge Core Operations:**
- [`tg-load-kg-core`](tg-load-kg-core.md) - Load knowledge core into processing
- [`tg-put-kg-core`](tg-put-kg-core.md) - Store knowledge core in system
- [`tg-get-kg-core`](tg-get-kg-core.md) - Retrieve knowledge core
- [`tg-delete-kg-core`](tg-delete-kg-core.md) - Remove knowledge core
- [`tg-unload-kg-core`](tg-unload-kg-core.md) - Unload knowledge core from processing
- [`tg-show-kg-cores`](tg-show-kg-cores.md) - List available knowledge cores

**Graph Data Operations:**
- [`tg-show-graph`](tg-show-graph.md) - Display graph triples/edges
- [`tg-graph-to-turtle`](tg-graph-to-turtle.md) - Export graph to Turtle format
- [`tg-load-turtle`](tg-load-turtle.md) - Import RDF triples from Turtle files

### Document Processing & Library Management

**Document Loading:**
- [`tg-load-pdf`](tg-load-pdf.md) - Load PDF documents into processing
- [`tg-load-text`](tg-load-text.md) - Load text documents into processing
- [`tg-load-sample-documents`](tg-load-sample-documents.md) - Load sample documents for testing

**Library Management:**
- [`tg-add-library-document`](tg-add-library-document.md) - Add documents to library
- [`tg-remove-library-document`](tg-remove-library-document.md) - Remove documents from library
- [`tg-show-library-documents`](tg-show-library-documents.md) - List library documents
- [`tg-start-library-processing`](tg-start-library-processing.md) - Start library document processing
- [`tg-stop-library-processing`](tg-stop-library-processing.md) - Stop library document processing
- [`tg-show-library-processing`](tg-show-library-processing.md) - Show library processing status

**Document Embeddings:**
- [`tg-load-doc-embeds`](tg-load-doc-embeds.md) - Load document embeddings
- [`tg-save-doc-embeds`](tg-save-doc-embeds.md) - Save document embeddings

### AI Services & Agent Interaction

**Query & Interaction:**
- [`tg-invoke-agent`](tg-invoke-agent.md) - Interactive agent Q&A via WebSocket
- [`tg-invoke-llm`](tg-invoke-llm.md) - Direct LLM text completion
- [`tg-invoke-prompt`](tg-invoke-prompt.md) - Use configured prompt templates
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Document-based RAG queries
- [`tg-invoke-graph-rag`](tg-invoke-graph-rag.md) - Graph-based RAG queries

**Tool & Prompt Management:**
- [`tg-show-tools`](tg-show-tools.md) - List available agent tools
- [`tg-set-prompt`](tg-set-prompt.md) - Configure prompt templates
- [`tg-show-prompts`](tg-show-prompts.md) - List configured prompts

### System Monitoring & Debugging

**System Status:**
- [`tg-show-processor-state`](tg-show-processor-state.md) - Show processing component states

**Debugging:**
- [`tg-dump-msgpack`](tg-dump-msgpack.md) - Dump MessagePack data for debugging

## Quick Start Examples

### Basic Document Processing
```bash
# Start a flow
tg-start-flow --flow-id my-flow --class-name document-processing

# Load a document
tg-load-text --flow-id my-flow --text "Your document content" --title "Test Document"

# Query the knowledge
tg-invoke-graph-rag --flow-id my-flow --query "What is the document about?"
```

### Knowledge Management
```bash
# List available knowledge cores
tg-show-kg-cores

# Load a knowledge core into a flow
tg-load-kg-core --flow-id my-flow --kg-core-id my-knowledge

# Query the knowledge graph
tg-show-graph --limit 100
```

### Flow Management
```bash
# Show available flow classes
tg-show-flow-classes

# Show running flows
tg-show-flows

# Stop a flow
tg-stop-flow --flow-id my-flow
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL for all commands
- `TRUSTGRAPH_USER`: Default user identifier
- `TRUSTGRAPH_COLLECTION`: Default collection identifier

## Authentication

CLI commands inherit authentication from the environment or API configuration. See the main TrustGraph documentation for authentication setup.

## Error Handling

All CLI commands provide:
- Consistent error reporting
- Exit codes (0 for success, non-zero for errors)
- Detailed error messages for troubleshooting
- Retry logic for network operations where appropriate

## Related Documentation

- [TrustGraph API Documentation](../apis/README.md)
- [TrustGraph WebSocket Guide](../apis/websocket.md)
- [TrustGraph Pulsar Guide](../apis/pulsar.md)