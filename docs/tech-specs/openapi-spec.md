# OpenAPI Specification - Technical Spec

## Goal

Create a comprehensive, modular OpenAPI 3.1 specification for the TrustGraph REST API Gateway that:
- Documents all REST endpoints
- Uses external `$ref` for modularity and maintainability
- Maps directly to the message translator code
- Provides accurate request/response schemas

## Source of Truth

The API is defined by:
- **Message Translators**: `trustgraph-base/trustgraph/messaging/translators/*.py`
- **Dispatcher Manager**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
- **Endpoint Manager**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## Directory Structure

```
openapi/
├── openapi.yaml                          # Main entry point
├── paths/
│   ├── config.yaml                       # Global services
│   ├── flow.yaml
│   ├── librarian.yaml
│   ├── knowledge.yaml
│   ├── collection-management.yaml
│   ├── flow-services/                    # Flow-hosted services
│   │   ├── agent.yaml
│   │   ├── document-rag.yaml
│   │   ├── graph-rag.yaml
│   │   ├── text-completion.yaml
│   │   ├── prompt.yaml
│   │   ├── embeddings.yaml
│   │   ├── mcp-tool.yaml
│   │   ├── triples.yaml
│   │   ├── objects.yaml
│   │   ├── nlp-query.yaml
│   │   ├── structured-query.yaml
│   │   ├── structured-diag.yaml
│   │   ├── graph-embeddings.yaml
│   │   ├── document-embeddings.yaml
│   │   ├── text-load.yaml
│   │   └── document-load.yaml
│   ├── import-export/
│   │   ├── core-import.yaml
│   │   ├── core-export.yaml
│   │   └── flow-import-export.yaml      # WebSocket import/export
│   ├── websocket.yaml
│   └── metrics.yaml
├── components/
│   ├── schemas/
│   │   ├── config/
│   │   ├── flow/
│   │   ├── librarian/
│   │   ├── knowledge/
│   │   ├── collection/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/
│   ├── responses/
│   └── examples/
└── security/
    └── bearerAuth.yaml
```

## Service Mapping

### Global Services (`/api/v1/{kind}`)
- `config` - Configuration management
- `flow` - Flow lifecycle
- `librarian` - Document library
- `knowledge` - Knowledge cores
- `collection-management` - Collection metadata

### Flow-Hosted Services (`/api/v1/flow/{flow}/service/{kind}`)

**Request/Response:**
- `agent`, `text-completion`, `prompt`, `mcp-tool`
- `graph-rag`, `document-rag`
- `embeddings`, `graph-embeddings`, `document-embeddings`
- `triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**Fire-and-Forget:**
- `text-load`, `document-load`

### Import/Export
- `/api/v1/import-core` (POST)
- `/api/v1/export-core` (GET)
- `/api/v1/flow/{flow}/import/{kind}` (WebSocket)
- `/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### Other
- `/api/v1/socket` (WebSocket multiplexed)
- `/api/metrics` (Prometheus)

## Approach

### Phase 1: Setup
1. Create directory structure
2. Create main `openapi.yaml` with metadata, servers, security
3. Create reusable components (errors, common parameters, security schemes)

### Phase 2: Common Schemas
Create shared schemas used across services:
- `RdfValue`, `Triple` - RDF/triple structures
- `ErrorObject` - Error response
- `DocumentMetadata`, `ProcessingMetadata` - Metadata structures
- Common parameters: `FlowId`, `User`, `Collection`

### Phase 3: Global Services
For each global service (config, flow, librarian, knowledge, collection-management):
1. Create path file in `paths/`
2. Create request schema in `components/schemas/{service}/`
3. Create response schema
4. Add examples
5. Reference from main `openapi.yaml`

### Phase 4: Flow-Hosted Services
For each flow-hosted service:
1. Create path file in `paths/flow-services/`
2. Create request/response schemas in `components/schemas/ai-services/`
3. Add streaming flag documentation where applicable
4. Reference from main `openapi.yaml`

### Phase 5: Import/Export & WebSocket
1. Document core import/export endpoints
2. Document WebSocket protocol patterns
3. Document flow-level import/export WebSocket endpoints

### Phase 6: Validation
1. Validate with OpenAPI validator tools
2. Test with Swagger UI
3. Verify all translators are covered

## Field Naming Convention

All JSON fields use **kebab-case**:
- `flow-id`, `blueprint-name`, `doc-limit`, `entity-limit`, etc.

## Creating Schema Files

For each translator in `trustgraph-base/trustgraph/messaging/translators/`:

1. **Read translator `to_pulsar()` method** - Defines request schema
2. **Read translator `from_pulsar()` method** - Defines response schema
3. **Extract field names and types**
4. **Create OpenAPI schema** with:
   - Field names (kebab-case)
   - Types (string, integer, boolean, object, array)
   - Required fields
   - Defaults
   - Descriptions

### Example Mapping Process

```python
# From retrieval.py DocumentRagRequestTranslator
def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
    return DocumentRagQuery(
        query=data["query"],                              # required string
        user=data.get("user", "trustgraph"),             # optional string, default "trustgraph"
        collection=data.get("collection", "default"),     # optional string, default "default"
        doc_limit=int(data.get("doc-limit", 20)),        # optional integer, default 20
        streaming=data.get("streaming", False)            # optional boolean, default false
    )
```

Maps to:

```yaml
# components/schemas/ai-services/DocumentRagRequest.yaml
type: object
required:
  - query
properties:
  query:
    type: string
    description: Search query
  user:
    type: string
    default: trustgraph
  collection:
    type: string
    default: default
  doc-limit:
    type: integer
    default: 20
    description: Maximum number of documents to retrieve
  streaming:
    type: boolean
    default: false
    description: Enable streaming responses
```

## Streaming Responses

Services that support streaming return multiple responses with `end_of_stream` flag:
- `agent`, `text-completion`, `prompt`
- `document-rag`, `graph-rag`

Document this pattern in each service's response schema.

## Error Responses

All services can return:
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

Where `ErrorObject` is:
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## References

- Translators: `trustgraph-base/trustgraph/messaging/translators/`
- Dispatcher mapping: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
- Endpoint routing: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
- Service summary: `API_SERVICES_SUMMARY.md`
