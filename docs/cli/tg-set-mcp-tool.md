# tg-set-mcp-tool

## Synopsis

```
tg-set-mcp-tool [OPTIONS] --name NAME --tool-url URL
```

## Description

The `tg-set-mcp-tool` command configures and registers MCP (Model Control Protocol) tools in the TrustGraph system. It allows defining MCP tool configurations with name and URL. Tools are stored in the 'mcp' configuration group for discovery and execution.

This command is useful for:
- Registering MCP tool endpoints for agent use
- Configuring external MCP server connections
- Managing MCP tool registry for agent workflows
- Integrating third-party MCP tools into TrustGraph

The command stores MCP tool configurations in the 'mcp' configuration group, separate from regular agent tools.

## Options

- `-u, --api-url URL`
  - TrustGraph API URL for configuration storage
  - Default: `http://localhost:8088/` (or `TRUSTGRAPH_URL` environment variable)
  - Should point to a running TrustGraph API instance

- `--name NAME`
  - **Required.** MCP tool name identifier
  - Used to reference the MCP tool in configurations
  - Must be unique within the MCP tool registry

- `--tool-url URL`
  - **Required.** MCP tool URL endpoint
  - Should point to the MCP server endpoint providing the tool functionality
  - Must be a valid URL accessible by the TrustGraph system

- `-h, --help`
  - Show help message and exit

## Examples

### Basic MCP Tool Registration

Register a weather service MCP tool:
```bash
tg-set-mcp-tool --name weather --tool-url "http://localhost:3000/weather"
```

### Calculator MCP Tool

Register a calculator MCP tool:
```bash
tg-set-mcp-tool --name calculator --tool-url "http://mcp-tools.example.com/calc"
```

### Remote MCP Service

Register a remote MCP service:
```bash
tg-set-mcp-tool --name document-processor \
                --tool-url "https://api.example.com/mcp/documents"
```

### Custom API URL

Register MCP tool with custom TrustGraph API:
```bash
tg-set-mcp-tool -u http://trustgraph.example.com:8088/ \
                --name custom-mcp --tool-url "http://custom.mcp.com/api"
```

### Local Development Setup

Register MCP tools for local development:
```bash
tg-set-mcp-tool --name dev-tool --tool-url "http://localhost:8080/mcp"
```

## MCP Tool Configuration

MCP tools are configured with minimal metadata:

- **name**: Unique identifier for the tool
- **url**: Endpoint URL for the MCP server

The configuration is stored as JSON in the 'mcp' configuration group:
```json
{
  "name": "weather",
  "url": "http://localhost:3000/weather"
}
```

## Advanced Usage

### Updating Existing MCP Tools

Update an existing MCP tool configuration:
```bash
# Update MCP tool URL
tg-set-mcp-tool --name weather --tool-url "http://new-weather-server:3000/api"
```

### Batch MCP Tool Registration

Register multiple MCP tools in a script:
```bash
#!/bin/bash
# Register a suite of MCP tools
tg-set-mcp-tool --name search --tool-url "http://search-mcp:3000/api"
tg-set-mcp-tool --name translate --tool-url "http://translate-mcp:3000/api"
tg-set-mcp-tool --name summarize --tool-url "http://summarize-mcp:3000/api"
```

### Environment-Specific Configuration

Configure MCP tools for different environments:
```bash
# Development environment
export TRUSTGRAPH_URL="http://dev.trustgraph.com:8088/"
tg-set-mcp-tool --name dev-mcp --tool-url "http://dev.mcp.com/api"

# Production environment
export TRUSTGRAPH_URL="http://prod.trustgraph.com:8088/"
tg-set-mcp-tool --name prod-mcp --tool-url "http://prod.mcp.com/api"
```

### MCP Tool Validation

Verify MCP tool registration:
```bash
# Register MCP tool and verify
tg-set-mcp-tool --name test-mcp --tool-url "http://test.mcp.com/api"

# Check if MCP tool was registered
tg-show-mcp-tools | grep test-mcp
```

## Error Handling

The command handles various error conditions:

- **Missing required arguments**: Both name and tool-url must be provided
- **Invalid URLs**: Tool URLs must be valid and accessible
- **API connection errors**: If the TrustGraph API is unavailable
- **Configuration errors**: If MCP tool data cannot be stored

Common error scenarios:
```bash
# Missing required field
tg-set-mcp-tool --name tool1
# Output: Exception: Must specify --tool-url for MCP tool

# Missing name
tg-set-mcp-tool --tool-url "http://example.com/mcp"
# Output: Exception: Must specify --name for MCP tool

# Invalid API URL
tg-set-mcp-tool -u "invalid-url" --name tool1 --tool-url "http://mcp.com"
# Output: Exception: [API connection error]
```

## Integration with Other Commands

### With MCP Tool Management

View registered MCP tools:
```bash
# Register MCP tool
tg-set-mcp-tool --name new-mcp --tool-url "http://new.mcp.com/api"

# View all MCP tools
tg-show-mcp-tools
```

### With Agent Workflows

Use MCP tools in agent workflows:
```bash
# Register MCP tool
tg-set-mcp-tool --name weather --tool-url "http://weather.mcp.com/api"

# Invoke MCP tool directly
tg-invoke-mcp-tool --name weather --input "location=London"
```

### With Configuration Management

MCP tools integrate with configuration management:
```bash
# Register MCP tool
tg-set-mcp-tool --name config-mcp --tool-url "http://config.mcp.com/api"

# View configuration including MCP tools
tg-show-config
```

## Best Practices

1. **Clear Naming**: Use descriptive, unique MCP tool names
2. **Reliable URLs**: Ensure MCP endpoints are stable and accessible
3. **Health Checks**: Verify MCP endpoints are operational before registration
4. **Documentation**: Document MCP tool capabilities and usage
5. **Error Handling**: Implement proper error handling for MCP endpoints
6. **Security**: Use secure URLs (HTTPS) when possible
7. **Monitoring**: Monitor MCP tool availability and performance

## Troubleshooting

### MCP Tool Not Appearing

If a registered MCP tool doesn't appear in listings:
1. Verify the MCP tool was registered successfully
2. Check MCP tool registry with `tg-show-mcp-tools`
3. Ensure the API URL is correct
4. Verify TrustGraph API is running

### MCP Tool Registration Errors

If MCP tool registration fails:
1. Check all required arguments are provided
2. Verify the tool URL is accessible
3. Ensure the MCP endpoint is operational
4. Check API connectivity
5. Review error messages for specific issues

### MCP Tool Connectivity Issues

If MCP tools aren't working as expected:
1. Verify MCP endpoint is accessible from TrustGraph
2. Check MCP server logs for errors
3. Ensure MCP protocol compatibility
4. Review network connectivity and firewall rules
5. Test MCP endpoint directly

## MCP Protocol

The Model Control Protocol (MCP) is a standardized interface for AI model tools:

- **Standardized API**: Consistent interface across different tools
- **Extensible**: Support for complex tool interactions
- **Stateful**: Can maintain state across multiple interactions
- **Secure**: Built-in security and authentication mechanisms

## Security Considerations

When registering MCP tools:

1. **URL Validation**: Ensure URLs are legitimate and secure
2. **Network Security**: Use HTTPS when possible
3. **Access Control**: Implement proper authentication for MCP endpoints
4. **Input Validation**: Validate all inputs to MCP tools
5. **Error Handling**: Don't expose sensitive information in error messages

## Related Commands

- [`tg-show-mcp-tools`](tg-show-mcp-tools.md) - Display registered MCP tools
- [`tg-delete-mcp-tool`](tg-delete-mcp-tool.md) - Remove MCP tool configurations
- [`tg-invoke-mcp-tool`](tg-invoke-mcp-tool.md) - Execute MCP tools
- [`tg-set-tool`](tg-set-tool.md) - Configure regular agent tools

## See Also

- MCP Protocol Documentation
- TrustGraph MCP Integration Guide
- Agent Tool Configuration Guide