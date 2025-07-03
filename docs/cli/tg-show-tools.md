# tg-show-tools

## Synopsis

```
tg-show-tools [OPTIONS]
```

## Description

The `tg-show-tools` command displays the current agent tool configuration from TrustGraph. It retrieves and presents detailed information about all available tools that agents can use, including their descriptions, arguments, and parameter types.

This command is useful for:
- Understanding available agent tools and their capabilities
- Debugging agent tool configuration issues
- Documenting the current tool set
- Verifying tool definitions and argument specifications

The command queries the TrustGraph API to fetch the tool index and individual tool definitions, then presents them in a formatted table for easy reading.

## Options

- `-u, --api-url URL`
  - TrustGraph API URL to query for tool configuration
  - Default: `http://localhost:8088/` (or `TRUSTGRAPH_URL` environment variable)
  - Should point to a running TrustGraph API instance

- `-h, --help`
  - Show help message and exit

## Examples

### Basic Usage

Display all available agent tools using the default API URL:
```bash
tg-show-tools
```

### Custom API URL

Display tools from a specific TrustGraph instance:
```bash
tg-show-tools -u http://trustgraph.example.com:8088/
```

### Remote Instance

Query tools from a remote TrustGraph deployment:
```bash
tg-show-tools --api-url http://10.0.1.100:8088/
```

### Using Environment Variable

Set the API URL via environment variable:
```bash
export TRUSTGRAPH_URL=http://production.trustgraph.com:8088/
tg-show-tools
```

## Output Format

The command displays each tool in a detailed table format:
```
web-search:
+-------------+----------------------------------------------------------------------+
| id          | web-search                                                           |
+-------------+----------------------------------------------------------------------+
| name        | Web Search                                                           |
+-------------+----------------------------------------------------------------------+
| description | Search the web for information using a search engine                |
+-------------+----------------------------------------------------------------------+
| arg 0       | query: string                                                        |
|             | The search query to execute                                          |
+-------------+----------------------------------------------------------------------+
| arg 1       | max_results: integer                                                 |
|             | Maximum number of search results to return                           |
+-------------+----------------------------------------------------------------------+

file-read:
+-------------+----------------------------------------------------------------------+
| id          | file-read                                                            |
+-------------+----------------------------------------------------------------------+
| name        | File Reader                                                          |
+-------------+----------------------------------------------------------------------+
| description | Read contents of a file from the filesystem                         |
+-------------+----------------------------------------------------------------------+
| arg 0       | path: string                                                         |
|             | Path to the file to read                                             |
+-------------+----------------------------------------------------------------------+
```

For each tool, the output includes:
- **id**: Unique identifier for the tool
- **name**: Human-readable name of the tool
- **description**: Detailed description of what the tool does
- **arg N**: Arguments the tool accepts, with name, type, and description

## Advanced Usage

### Tool Inventory

Create a complete inventory of available tools:
```bash
#!/bin/bash
echo "=== TrustGraph Agent Tools Inventory ==="
echo "Generated on: $(date)"
echo
tg-show-tools > tools_inventory.txt
echo "Inventory saved to tools_inventory.txt"
```

### Tool Comparison

Compare tools across different environments:
```bash
#!/bin/bash
echo "=== Development Tools ==="
tg-show-tools -u http://dev.trustgraph.com:8088/ > dev_tools.txt
echo
echo "=== Production Tools ==="
tg-show-tools -u http://prod.trustgraph.com:8088/ > prod_tools.txt
echo
diff dev_tools.txt prod_tools.txt
```

### Tool Documentation

Generate documentation for agent tools:
```bash
#!/bin/bash
echo "# Available Agent Tools" > AGENT_TOOLS.md
echo "" >> AGENT_TOOLS.md
echo "Generated on: $(date)" >> AGENT_TOOLS.md
echo "" >> AGENT_TOOLS.md
tg-show-tools >> AGENT_TOOLS.md
```

### Tool Configuration Validation

Validate tool configuration after updates:
```bash
#!/bin/bash
echo "Validating tool configuration..."
if tg-show-tools > /dev/null 2>&1; then
    echo "✓ Tool configuration is valid"
    tool_count=$(tg-show-tools | grep -c "^[a-zA-Z].*:$")
    echo "✓ Found $tool_count tools"
else
    echo "✗ Tool configuration validation failed"
    exit 1
fi
```

## Error Handling

The command handles various error conditions:

- **API connection errors**: If the TrustGraph API is unavailable
- **Authentication errors**: If API access is denied
- **Invalid configuration**: If tool configuration is malformed
- **Network timeouts**: If API requests time out

Common error scenarios:
```bash
# API not available
tg-show-tools -u http://invalid-host:8088/
# Output: Exception: [Connection error details]

# Invalid API URL
tg-show-tools --api-url "not-a-url"
# Output: Exception: [URL parsing error]

# Configuration not found
# Output: Exception: [Configuration retrieval error]
```

## Integration with Other Commands

### With Agent Configuration

Display tools alongside agent configuration:
```bash
echo "=== Agent Tools ==="
tg-show-tools
echo
echo "=== Agent Configuration ==="
tg-show-config
```

### With Flow Analysis

Understand tools used in flows:
```bash
echo "=== Available Tools ==="
tg-show-tools
echo
echo "=== Active Flows ==="
tg-show-flows
```

### With Prompt Analysis

Analyze tool usage in prompts:
```bash
echo "=== Agent Tools ==="
tg-show-tools | grep -E "^[a-zA-Z].*:$"
echo
echo "=== Available Prompts ==="
tg-show-prompts
```

## Best Practices

1. **Regular Documentation**: Keep tool documentation updated
2. **Version Control**: Track tool configuration changes
3. **Testing**: Test tool functionality after configuration changes
4. **Security**: Review tool permissions and capabilities
5. **Monitoring**: Monitor tool usage and performance

## Troubleshooting

### No Tools Displayed

If no tools are shown:
1. Verify the TrustGraph API is running and accessible
2. Check that tool configuration has been properly loaded
3. Ensure the API URL is correct
4. Verify network connectivity

### Incomplete Tool Information

If tool information is missing or incomplete:
1. Check the tool configuration files
2. Verify the tool index is properly maintained
3. Ensure tool definitions are valid JSON
4. Check for configuration loading errors

### Tool Configuration Errors

If tools are not working as expected:
1. Validate tool definitions against the schema
2. Check for missing or invalid arguments
3. Verify tool implementation is available
4. Review agent logs for tool execution errors

## Tool Management

### Adding New Tools

After adding new tools to the system:
```bash
# Verify the new tool appears
tg-show-tools | grep "new-tool-name"

# Test the tool configuration
tg-show-tools > current_tools.txt
```

### Removing Tools

After removing tools:
```bash
# Verify the tool is no longer listed
tg-show-tools | grep -v "removed-tool-name"

# Update tool documentation
tg-show-tools > updated_tools.txt
```

## Related Commands

- [`tg-show-config`](tg-show-config.md) - Show TrustGraph configuration
- [`tg-show-prompts`](tg-show-prompts.md) - Display available prompts
- [`tg-show-flows`](tg-show-flows.md) - Show active flows
- [`tg-invoke-agent`](tg-invoke-agent.md) - Invoke agent with tools

## See Also

- TrustGraph Agent Documentation
- Tool Configuration Guide
- Agent API Reference