# tg-delete-tool

## Synopsis

```
tg-delete-tool [OPTIONS] --id ID
```

## Description

The `tg-delete-tool` command deletes tools from the TrustGraph system. It removes tool configurations by ID from the agent configuration and updates the tool index accordingly. Once deleted, tools are no longer available for agent use.

This command is useful for:
- Removing obsolete or deprecated tools
- Cleaning up tool configurations
- Managing tool registry maintenance
- Updating tool deployments by removing old versions

The command removes both the tool from the tool index and deletes the complete tool configuration from the TrustGraph API.

## Options

- `-u, --api-url URL`
  - TrustGraph API URL for configuration management
  - Default: `http://localhost:8088/` (or `TRUSTGRAPH_URL` environment variable)
  - Should point to a running TrustGraph API instance

- `--id ID`
  - **Required.** Tool ID to delete
  - Must match an existing tool ID in the registry
  - Tool will be completely removed from the system

- `-h, --help`
  - Show help message and exit

## Examples

### Basic Tool Deletion

Delete a weather tool:
```bash
tg-delete-tool --id weather
```

### Calculator Tool Deletion

Delete a calculator tool:
```bash
tg-delete-tool --id calculator
```

### Custom API URL

Delete a tool from a specific TrustGraph instance:
```bash
tg-delete-tool --api-url http://trustgraph.example.com:8088/ --id custom-tool
```

### Batch Tool Deletion

Delete multiple tools in a script:
```bash
#!/bin/bash
# Delete obsolete tools
tg-delete-tool --id old-search
tg-delete-tool --id deprecated-calc
tg-delete-tool --id unused-tool
```

### Conditional Deletion

Delete a tool only if it exists:
```bash
#!/bin/bash
# Check if tool exists before deletion
if tg-show-tools | grep -q "test-tool"; then
    tg-delete-tool --id test-tool
    echo "Tool deleted"
else
    echo "Tool not found"
fi
```

## Deletion Process

The deletion process involves two steps:

1. **Index Update**: Remove the tool ID from the tool index
2. **Configuration Removal**: Delete the tool configuration data

Both operations must succeed for the deletion to be complete.

## Error Handling

The command handles various error conditions:

- **Tool not found**: If the specified tool ID doesn't exist
- **Missing configuration**: If tool is in index but configuration is missing
- **API connection errors**: If the TrustGraph API is unavailable
- **Partial deletion**: If index update or configuration removal fails

Common error scenarios:
```bash
# Tool not found
tg-delete-tool --id nonexistent-tool
# Output: Tool 'nonexistent-tool' not found in tool index.

# Missing required field
tg-delete-tool
# Output: Exception: Must specify --id for tool to delete

# API connection error
tg-delete-tool --api-url http://invalid-host:8088/ --id tool1
# Output: Exception: [Connection error details]
```

## Verification

The command provides feedback on the deletion process:

- **Success**: `Tool 'tool-id' deleted successfully.`
- **Not found**: `Tool 'tool-id' not found in tool index.`
- **Configuration missing**: `Tool configuration for 'tool-id' not found.`
- **Error**: `Error deleting tool 'tool-id': [error details]`

## Advanced Usage

### Safe Deletion with Verification

Verify tool exists before deletion:
```bash
#!/bin/bash
TOOL_ID="weather"

# Check if tool exists
if tg-show-tools | grep -q "^$TOOL_ID:"; then
    echo "Deleting tool: $TOOL_ID"
    tg-delete-tool --id "$TOOL_ID"
    
    # Verify deletion
    if ! tg-show-tools | grep -q "^$TOOL_ID:"; then
        echo "Tool successfully deleted"
    else
        echo "Tool deletion failed"
    fi
else
    echo "Tool $TOOL_ID not found"
fi
```

### Backup Before Deletion

Backup tool configuration before deletion:
```bash
#!/bin/bash
TOOL_ID="important-tool"

# Export tool configuration
echo "Backing up tool configuration..."
tg-show-tools | grep -A 20 "^$TOOL_ID:" > "${TOOL_ID}_backup.txt"

# Delete tool
echo "Deleting tool..."
tg-delete-tool --id "$TOOL_ID"

echo "Tool deleted, backup saved to ${TOOL_ID}_backup.txt"
```

### Cleanup Script

Clean up multiple tools based on patterns:
```bash
#!/bin/bash
# Delete all test tools
echo "Cleaning up test tools..."

# Get list of test tools
TEST_TOOLS=$(tg-show-tools | grep "^test-" | cut -d: -f1)

for tool in $TEST_TOOLS; do
    echo "Deleting $tool..."
    tg-delete-tool --id "$tool"
done

echo "Cleanup complete"
```

### Environment-Specific Deletion

Delete tools from specific environments:
```bash
#!/bin/bash
# Delete development tools from production
export TRUSTGRAPH_URL="http://prod.trustgraph.com:8088/"

DEV_TOOLS=("dev-tool" "debug-tool" "test-helper")

for tool in "${DEV_TOOLS[@]}"; do
    echo "Removing development tool: $tool"
    tg-delete-tool --id "$tool"
done
```

## Integration with Other Commands

### With Tool Management

List and delete tools:
```bash
# List all tools
tg-show-tools

# Delete specific tool
tg-delete-tool --id unwanted-tool

# Verify deletion
tg-show-tools | grep unwanted-tool
```

### With Configuration Management

Manage tool configurations:
```bash
# View current configuration
tg-show-config

# Delete tool
tg-delete-tool --id old-tool

# View updated configuration
tg-show-config
```

### With Agent Workflows

Ensure agents don't use deleted tools:
```bash
# Delete tool
tg-delete-tool --id deprecated-tool

# Check agent configuration
tg-show-config | grep deprecated-tool
```

## Best Practices

1. **Verification**: Always verify tool exists before deletion
2. **Backup**: Backup important tool configurations before deletion
3. **Dependencies**: Check for tool dependencies before deletion
4. **Testing**: Test system functionality after tool deletion
5. **Documentation**: Document reasons for tool deletion
6. **Gradual Removal**: Remove tools gradually in production environments
7. **Monitoring**: Monitor for errors after tool deletion

## Troubleshooting

### Tool Not Found

If tool deletion reports "not found":
1. Verify the tool ID is correct
2. Check tool exists with `tg-show-tools`
3. Ensure you're connected to the correct TrustGraph instance
4. Check for case sensitivity in tool ID

### Partial Deletion

If deletion partially fails:
1. Check TrustGraph API connectivity
2. Verify API permissions
3. Check for configuration corruption
4. Retry the deletion operation
5. Manual cleanup may be required

### Permission Errors

If deletion fails due to permissions:
1. Verify API access credentials
2. Check TrustGraph API permissions
3. Ensure proper authentication
4. Contact system administrator if needed

## Recovery

### Restore Deleted Tool

If a tool was accidentally deleted:
1. Use backup configuration if available
2. Re-register the tool with `tg-set-tool`
3. Restore from version control if tool definitions are tracked
4. Contact system administrator for recovery options

### Verify System State

After deletion, verify system state:
```bash
# Check tool index consistency
tg-show-tools

# Verify no orphaned configurations
tg-show-config | grep "tool\."

# Test agent functionality
tg-invoke-agent --prompt "Test prompt"
```

## Related Commands

- [`tg-show-tools`](tg-show-tools.md) - Display registered tools
- [`tg-set-tool`](tg-set-tool.md) - Configure and register tools
- [`tg-delete-mcp-tool`](tg-delete-mcp-tool.md) - Delete MCP tools
- [`tg-show-config`](tg-show-config.md) - View system configuration

## See Also

- TrustGraph Tool Management Guide
- Agent Configuration Documentation
- System Administration Manual