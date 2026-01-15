# TrustGraph OpenAPI Specification

This directory contains the modular OpenAPI 3.1 specification for the TrustGraph REST API Gateway.

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
