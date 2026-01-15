# TrustGraph API Specifications

This directory contains formal specifications for the TrustGraph API Gateway.

## Directory Structure

```
specs/
├── api/              # OpenAPI 3.1.0 specification for REST API
│   ├── openapi.yaml  # Main entry point
│   ├── paths/        # Endpoint definitions
│   ├── components/   # Reusable schemas, responses, parameters
│   └── security/     # Security scheme definitions
│
├── websocket/        # AsyncAPI 3.0.0 specification for WebSocket API
│   ├── asyncapi.yaml # Main entry point
│   ├── channels/     # Channel definitions
│   ├── components/   # Message and schema definitions
│   └── STREAMING.md  # Streaming patterns documentation
│
└── README.md         # This file
```

## Specifications

### REST API (OpenAPI 3.1.0)

Location: `specs/api/openapi.yaml`

The REST API specification documents:
- **5 Global Services**: config, flow, librarian, knowledge, collection-management
- **16 Flow-Hosted Services**: agent, RAG, embeddings, queries, loading, tools
- **Import/Export**: Bulk data operations
- **Metrics**: Prometheus monitoring

**Features**:
- Modular structure with $ref to external files
- Comprehensive request/response schemas
- Authentication via Bearer tokens
- Field naming in kebab-case

### WebSocket API (AsyncAPI 3.0.0)

Location: `specs/websocket/asyncapi.yaml`

The WebSocket API specification documents:
- Multiplexed async communication protocol
- Request/response message envelopes with ID correlation
- All services accessible via single WebSocket connection
- Streaming response patterns

**Features**:
- References REST API schemas (single source of truth)
- Message-based routing (service + optional flow parameters)
- Comprehensive streaming documentation
- Full async/multiplexing behavior

## Building Documentation

### Prerequisites

```bash
npm install -g @redocly/cli @asyncapi/cli
```

Or use npx (no installation required).

### Generate REST API Documentation

**Using Redocly (HTML)**:
```bash
cd specs/api
npx @redocly/cli build-docs openapi.yaml -o ../../docs/api.html
```

**Preview in browser**:
```bash
cd specs/api
npx @redocly/cli preview-docs openapi.yaml
```
Opens interactive documentation at http://localhost:8080

**Validate**:
```bash
cd specs/api
npx @redocly/cli lint openapi.yaml
```

### Generate WebSocket API Documentation

**Using AsyncAPI (HTML)**:
```bash
cd specs/websocket
npx -p @asyncapi/cli asyncapi generate fromTemplate asyncapi.yaml @asyncapi/html-template@3.0.0 -o ../../docs/websocket --force-write
```

Note: The generator must run from the `specs/websocket` directory to properly resolve relative `$ref` paths to OpenAPI schemas.

**Validate**:
```bash
cd specs/websocket
npx @asyncapi/cli validate asyncapi.yaml
```

### Build All Documentation

Use the provided build script:
```bash
./specs/build-docs.sh
```

This generates:
- `docs/api.html` - REST API documentation
- `docs/websocket/index.html` - WebSocket API documentation

## Viewing Documentation

After building:

**REST API**:
```bash
xdg-open docs/api.html
# or
firefox docs/api.html
```

**WebSocket API**:
```bash
xdg-open docs/websocket/index.html
# or
firefox docs/websocket/index.html
```

## Schema Reuse

The WebSocket API specification **references** the REST API schemas using relative paths:

```yaml
# In specs/websocket/components/messages/requests/AgentRequest.yaml
request:
  $ref: '../../../../api/components/schemas/agent/AgentRequest.yaml'
```

This ensures:
- **Single source of truth** for all schemas
- **Consistency** between REST and WebSocket APIs
- **Easy maintenance** - update schemas in one place

## Validation Status

Both specifications are validated and error-free:

- ✅ **OpenAPI**: Validated with Redocly CLI
- ✅ **AsyncAPI**: Validated with AsyncAPI CLI

## Maintenance

### Adding a New Service

1. **Create schemas** in `specs/api/components/schemas/{service-name}/`
   - `{ServiceName}Request.yaml`
   - `{ServiceName}Response.yaml`

2. **Create path definition** in `specs/api/paths/` or `specs/api/paths/flow/`

3. **Add path to main spec** in `specs/api/openapi.yaml`

4. **Create WebSocket message** in `specs/websocket/components/messages/requests/`
   - Reference the OpenAPI request schema

5. **Add to ServiceRequest** message in `specs/websocket/components/messages/ServiceRequest.yaml`

6. **Validate both specs**:
   ```bash
   cd specs/api && npx @redocly/cli lint openapi.yaml
   cd specs/websocket && npx @asyncapi/cli validate asyncapi.yaml
   ```

### Modifying an Existing Service

1. **Update schema** in `specs/api/components/schemas/{service-name}/`

2. **Changes automatically apply** to WebSocket spec via $ref

3. **Validate both specs** to ensure consistency

## Tools and Resources

**OpenAPI Tools**:
- [Redocly CLI](https://redocly.com/docs/cli/) - Linting, docs generation
- [Swagger Editor](https://editor.swagger.io/) - Online editor
- [OpenAPI Generator](https://openapi-generator.tech/) - Client/server code generation

**AsyncAPI Tools**:
- [AsyncAPI CLI](https://www.asyncapi.com/tools/cli) - Validation, docs generation
- [AsyncAPI Studio](https://studio.asyncapi.com/) - Online editor
- [AsyncAPI Generator](https://www.asyncapi.com/tools/generator) - Template-based generation

**Online Validators**:
- OpenAPI: https://editor.swagger.io/
- AsyncAPI: https://studio.asyncapi.com/

## API Version

Current version: **1.8.0**

Version is specified in both:
- `specs/api/openapi.yaml` → `info.version`
- `specs/websocket/asyncapi.yaml` → `info.version`

Update both when releasing a new API version.
