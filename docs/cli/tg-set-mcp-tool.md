# tg-set-mcp-tool

## Synopsis

```
tg-set-mcp-tool [OPTIONS] --id ID --tool-url URL [--auth-token TOKEN]
```

## Description

The `tg-set-mcp-tool` command configures and registers MCP (Model Control Protocol) tools in the TrustGraph system. It allows defining MCP tool configurations with id, URL, and optional authentication token. Tools are stored in the 'mcp' configuration group for discovery and execution.

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

- `-i, --id ID`
  - **Required.** MCP tool identifier
  - Used to reference the MCP tool in configurations
  - Must be unique within the MCP tool registry

- `-r, --remote-name NAME`
  - **Optional.** Remote MCP tool name used by the MCP server
  - If not specified, defaults to the value of `--id`
  - Use when the MCP server expects a different tool name

- `--tool-url URL`
  - **Required.** MCP tool URL endpoint
  - Should point to the MCP server endpoint providing the tool functionality
  - Must be a valid URL accessible by the TrustGraph system

- `--auth-token TOKEN`
  - **Optional.** Bearer token for authentication
  - Used to authenticate with secured MCP endpoints
  - Token is sent as `Authorization: Bearer {TOKEN}` header
  - Stored in plaintext in configuration (see Security Considerations)

- `-h, --help`
  - Show help message and exit

## Examples

### Basic MCP Tool Registration

Register a weather service MCP tool:
```bash
tg-set-mcp-tool --id weather --tool-url "http://localhost:3000/weather"
```

### Calculator MCP Tool

Register a calculator MCP tool:
```bash
tg-set-mcp-tool --id calculator --tool-url "http://mcp-tools.example.com/calc"
```

### Remote MCP Service

Register a remote MCP service:
```bash
tg-set-mcp-tool --id document-processor \
                --tool-url "https://api.example.com/mcp/documents"
```

### Secured MCP Tool with Authentication

Register an MCP tool that requires bearer token authentication:
```bash
tg-set-mcp-tool --id secure-tool \
                --tool-url "https://api.example.com/mcp" \
                --auth-token "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### MCP Tool with Remote Name

Register an MCP tool where the server uses a different name:
```bash
tg-set-mcp-tool --id my-weather \
                --remote-name weather_v2 \
                --tool-url "http://weather-server:3000/api"
```

### Custom API URL

Register MCP tool with custom TrustGraph API:
```bash
tg-set-mcp-tool -u http://trustgraph.example.com:8088/ \
                --id custom-mcp --tool-url "http://custom.mcp.com/api"
```

### Local Development Setup

Register MCP tools for local development:
```bash
tg-set-mcp-tool --id dev-tool --tool-url "http://localhost:8080/mcp"
```

### Production Setup with Authentication

Register authenticated MCP tools for production:
```bash
# Using environment variable for token
export MCP_AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
tg-set-mcp-tool --id prod-tool \
                --tool-url "https://prod-mcp.example.com/api" \
                --auth-token "$MCP_AUTH_TOKEN"
```

## MCP Tool Configuration

MCP tools are configured with the following metadata:

- **id**: Unique identifier for the tool (configuration key)
- **remote-name**: Name used by the MCP server (optional, defaults to id)
- **url**: Endpoint URL for the MCP server
- **auth-token**: Bearer token for authentication (optional)

The configuration is stored as JSON in the 'mcp' configuration group:

**Basic configuration:**
```json
{
  "remote-name": "weather",
  "url": "http://localhost:3000/weather"
}
```

**Configuration with authentication:**
```json
{
  "remote-name": "secure-tool",
  "url": "https://api.example.com/mcp",
  "auth-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Advanced Usage

### Updating Existing MCP Tools

Update an existing MCP tool configuration:
```bash
# Update MCP tool URL
tg-set-mcp-tool --id weather --tool-url "http://new-weather-server:3000/api"

# Add authentication to existing tool
tg-set-mcp-tool --id weather \
                --tool-url "http://weather-server:3000/api" \
                --auth-token "new-token-here"

# Remove authentication (by setting tool without auth-token)
tg-set-mcp-tool --id weather --tool-url "http://weather-server:3000/api"
```

### Batch MCP Tool Registration

Register multiple MCP tools in a script:
```bash
#!/bin/bash
# Register a suite of MCP tools
tg-set-mcp-tool --id search --tool-url "http://search-mcp:3000/api"
tg-set-mcp-tool --id translate --tool-url "http://translate-mcp:3000/api"
tg-set-mcp-tool --id summarize --tool-url "http://summarize-mcp:3000/api"

# Register secured tools with authentication
tg-set-mcp-tool --id secure-search \
                --tool-url "https://secure-search:3000/api" \
                --auth-token "$SEARCH_TOKEN"
tg-set-mcp-tool --id secure-translate \
                --tool-url "https://secure-translate:3000/api" \
                --auth-token "$TRANSLATE_TOKEN"
```

### Environment-Specific Configuration

Configure MCP tools for different environments:
```bash
# Development environment (no auth)
export TRUSTGRAPH_URL="http://dev.trustgraph.com:8088/"
tg-set-mcp-tool --id dev-mcp --tool-url "http://dev.mcp.com/api"

# Production environment (with auth)
export TRUSTGRAPH_URL="http://prod.trustgraph.com:8088/"
export PROD_MCP_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
tg-set-mcp-tool --id prod-mcp \
                --tool-url "https://prod.mcp.com/api" \
                --auth-token "$PROD_MCP_TOKEN"
```

### MCP Tool Validation

Verify MCP tool registration:
```bash
# Register MCP tool and verify
tg-set-mcp-tool --id test-mcp --tool-url "http://test.mcp.com/api"

# Check if MCP tool was registered and view auth status
tg-show-mcp-tools
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
tg-set-mcp-tool --id tool1
# Output: Exception: Must specify --tool-url for MCP tool

# Missing id
tg-set-mcp-tool --tool-url "http://example.com/mcp"
# Output: Exception: Must specify --id for MCP tool

# Invalid API URL
tg-set-mcp-tool -u "invalid-url" --id tool1 --tool-url "http://mcp.com"
# Output: Exception: [API connection error]
```

## Integration with Other Commands

### With MCP Tool Management

View registered MCP tools:
```bash
# Register MCP tool
tg-set-mcp-tool --id new-mcp --tool-url "http://new.mcp.com/api"

# View all MCP tools (shows auth status)
tg-show-mcp-tools
```

### With Agent Workflows

Use MCP tools in agent workflows:
```bash
# Register MCP tool with authentication
tg-set-mcp-tool --id weather \
                --tool-url "https://weather.mcp.com/api" \
                --auth-token "$WEATHER_TOKEN"

# Invoke MCP tool directly (auth handled automatically)
tg-invoke-mcp-tool --name weather --parameters '{"location": "London"}'
```

### With Configuration Management

MCP tools integrate with configuration management:
```bash
# Register MCP tool
tg-set-mcp-tool --id config-mcp --tool-url "http://config.mcp.com/api"

# View all MCP tool configurations
tg-show-mcp-tools
```

## Best Practices

1. **Clear Naming**: Use descriptive, unique MCP tool identifiers
2. **Reliable URLs**: Ensure MCP endpoints are stable and accessible
3. **Use HTTPS**: Always use HTTPS URLs when authentication is required
4. **Secure Tokens**: Store auth tokens in environment variables, not in scripts
5. **Token Rotation**: Regularly rotate authentication tokens
6. **Health Checks**: Verify MCP endpoints are operational before registration
7. **Documentation**: Document MCP tool capabilities and usage
8. **Error Handling**: Implement proper error handling for MCP endpoints
9. **Monitoring**: Monitor MCP tool availability and performance
10. **Access Control**: Restrict access to configuration system containing tokens

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
2. **Network Security**: Always use HTTPS for authenticated endpoints
3. **Token Storage**: Auth tokens are stored in plaintext in the configuration system
   - Ensure proper access control on the configuration storage
   - Use short-lived tokens when possible
   - Implement token rotation policies
4. **Token Transmission**: Use HTTPS to prevent token interception
5. **Access Control**: Implement proper authentication for MCP endpoints
6. **Token Exposure**:
   - Use environment variables to pass tokens to the command
   - Don't hardcode tokens in scripts or commit them to version control
   - The `tg-show-mcp-tools` command masks token values for security
7. **Input Validation**: Validate all inputs to MCP tools
8. **Error Handling**: Don't expose sensitive information in error messages
9. **Least Privilege**: Grant tokens minimum required permissions
10. **Audit Logging**: Monitor configuration changes for security events

### Authentication Best Practices

When using the `--auth-token` parameter:

- **Store tokens securely**: Use environment variables or secrets management systems
- **Use HTTPS**: Always use HTTPS URLs when providing authentication tokens
- **Rotate regularly**: Implement a token rotation schedule
- **Monitor usage**: Track which services are accessing authenticated endpoints
- **Revoke on compromise**: Have a process to quickly revoke and rotate compromised tokens

Example secure workflow:
```bash
# Store token in environment variable (not in script)
export MCP_TOKEN=$(cat /secure/path/to/token)

# Use HTTPS for authenticated endpoints
tg-set-mcp-tool --id secure-service \
                --tool-url "https://secure.example.com/mcp" \
                --auth-token "$MCP_TOKEN"

# Clear token from environment after use
unset MCP_TOKEN
```

## Related Commands

- [`tg-show-mcp-tools`](tg-show-mcp-tools.md) - Display registered MCP tools
- [`tg-delete-mcp-tool`](tg-delete-mcp-tool.md) - Remove MCP tool configurations
- [`tg-invoke-mcp-tool`](tg-invoke-mcp-tool.md) - Execute MCP tools
- [`tg-set-tool`](tg-set-tool.md) - Configure regular agent tools

## See Also

- MCP Protocol Documentation
- TrustGraph MCP Integration Guide
- Agent Tool Configuration Guide