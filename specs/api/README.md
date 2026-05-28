# TrustGraph OpenAPI Specification

This directory contains the modular OpenAPI 3.1 specification for the TrustGraph REST API Gateway.

## Authentication

Clients authenticate by passing an opaque bearer token in the
`Authorization` header.  The gateway resolves the token to an
authenticated identity and an associated workspace.  Tokens are
obtained via the IAM service (e.g. `tg-login` or `tg-create-api-key`).

## Service Tiers

API services are organized into three tiers based on their scoping:

### Global services

These services are not scoped to a workspace.  They manage
system-wide resources.

- **IAM** — user management, authentication, API key lifecycle

### Workspace-scoped services

These services operate within the workspace associated with the
authenticated token.  The workspace is resolved by the gateway from
the bearer token — it is not passed as an explicit parameter.

- **Config** — configuration management (prompts, token costs, etc.)
- **Librarian** — document library management
- **Knowledge** — knowledge graph core management
- **Collection Management** — collection metadata
- **Flow** — flow lifecycle and blueprint management

### Flow-scoped services

These services require a `flow` parameter identifying the processing
flow to use, in addition to the workspace context from the token.

- **Agent** — agentic AI interactions
- **Document RAG** — retrieval-augmented generation over documents
- **Graph RAG** — retrieval-augmented generation over knowledge graphs
- **Text Completion** — LLM text completion
- **Prompt** — prompt template expansion
- **Embeddings** — vector embedding generation
- **SPARQL Query** — SPARQL queries against the knowledge graph
- **Graph Embeddings** — knowledge graph embedding queries
- **Document Embeddings** — document embedding queries
- **Structured Query** — structured data queries
- **Row Embeddings** — structured data embedding queries
- **Rows Query** — row-level data queries
- **Triples Query** — knowledge graph triple queries

## Structure

```
specs/api/
├── openapi.yaml              # Main entry point
├── paths/                    # Endpoint definitions
│   ├── config.yaml
│   ├── flow.yaml
│   ├── flow-services/        # Flow-hosted services
│   └── import-export/
├── components/
│   ├── schemas/              # Request/response schemas
│   │   ├── config/
│   │   ├── flow/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/           # Reusable parameters
│   ├── responses/            # Reusable responses
│   └── examples/             # Example payloads
└── security/                 # Security schemes
    └── bearerAuth.yaml
```

## Viewing the Spec

### Swagger UI

```bash
# Install swagger-ui
npm install -g swagger-ui-watcher

# View in browser
swagger-ui-watcher specs/api/openapi.yaml
```

### Redoc

```bash
# Install redoc-cli
npm install -g redoc-cli

# Generate static HTML
redoc-cli bundle specs/api/openapi.yaml -o api-docs.html

# View
open api-docs.html
```

### Online Validators

Upload `openapi.yaml` to:
- https://editor.swagger.io/
- https://redocly.com/redoc/

## Validation

```bash
# Install openapi-spec-validator
pip install openapi-spec-validator

# Validate
openapi-spec-validator specs/api/openapi.yaml
```

## Development

When adding a new service:

1. Create schema files in `components/schemas/{service}/`
2. Create path file in `paths/` or `paths/flow-services/`
3. Add examples if needed
4. Reference from `openapi.yaml`
5. Validate

## References

- [OpenAPI 3.1 Specification](https://spec.openapis.org/oas/v3.1.0)
- [TrustGraph Tech Spec](../../docs/tech-specs/openapi-spec.md)
- [API Services Summary](../../API_SERVICES_SUMMARY.md)
