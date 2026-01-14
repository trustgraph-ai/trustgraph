# tg-show-config

Displays the current TrustGraph system configuration.

## Synopsis

```bash
tg-show-config [options]
```

## Description

The `tg-show-config` command retrieves and displays the complete TrustGraph system configuration in JSON format. This includes flow definitions, service configurations, and other system settings stored in the configuration service.

This is particularly useful for:
- Understanding the current system setup
- Debugging configuration issues
- Finding queue names for Pulsar integration
- Verifying flow definitions and interfaces

## Options

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Display Complete Configuration
```bash
tg-show-config
```

### Using Custom API URL
```bash
tg-show-config -u http://production:8088/
```

## Output Format

The command outputs the configuration version followed by the complete configuration in JSON format:

```
Version: 42
{
    "flows": {
        "default": {
            "blueprint-name": "document-rag+graph-rag",
            "description": "Default processing flow",
            "interfaces": {
                "agent": {
                    "request": "non-persistent://tg/request/agent:default",
                    "response": "non-persistent://tg/response/agent:default"
                },
                "graph-rag": {
                    "request": "non-persistent://tg/request/graph-rag:document-rag+graph-rag",
                    "response": "non-persistent://tg/response/graph-rag:document-rag+graph-rag"
                },
                "text-load": "persistent://tg/flow/text-document-load:default",
                ...
            }
        }
    },
    "prompts": {
        "system": "You are a helpful AI assistant...",
        "graph-rag": "Answer the question using the provided context..."
    },
    "token-costs": {
        "gpt-4": {
            "prompt": 0.03,
            "completion": 0.06
        }
    },
    ...
}
```

## Configuration Sections

### Flow Definitions
Flow configurations showing:
- **blueprint-name**: The flow blueprint being used
- **description**: Human-readable flow description  
- **interfaces**: Pulsar queue names for each service

### Prompt Templates
System and service-specific prompt templates used by AI services.

### Token Costs
Model pricing information for cost tracking and billing.

### Service Settings
Various service-specific configuration parameters.

## Finding Queue Names

The configuration output is essential for discovering Pulsar queue names:

### Flow-Hosted Services
Look in the `flows` section under `interfaces`:

```json
"graph-rag": {
    "request": "non-persistent://tg/request/graph-rag:document-rag+graph-rag",
    "response": "non-persistent://tg/response/graph-rag:document-rag+graph-rag"
}
```

### Fire-and-Forget Services
Some services only have input queues:

```json
"text-load": "persistent://tg/flow/text-document-load:default"
```

## Error Handling

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Verify the API URL and ensure TrustGraph is running.

### Authentication Errors
```bash
Exception: Unauthorized
```
**Solution**: Check authentication credentials and permissions.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-put-flow-blueprint`](tg-put-flow-blueprint.md) - Update flow blueprint definitions
- [`tg-show-flows`](tg-show-flows.md) - List active flows
- [`tg-set-prompt`](tg-set-prompt.md) - Configure prompt templates
- [`tg-set-token-costs`](tg-set-token-costs.md) - Configure token costs

## API Integration

This command uses the [Config API](../apis/api-config.md) with the `config` operation to retrieve the complete system configuration.

**API Call:**
```json
{
    "operation": "config"
}
```

## Use Cases

### Development and Debugging
- Verify flow configurations are correct
- Check that services have proper queue assignments
- Debug configuration-related issues

### System Administration
- Monitor configuration changes over time
- Document current system setup
- Prepare for system migrations

### Integration Development
- Discover Pulsar queue names for direct integration
- Understand service interfaces and capabilities
- Verify API endpoint configurations

### Troubleshooting
- Check if flows are properly configured
- Verify prompt templates are set correctly
- Confirm token cost configurations