# tg-delete-mcp-tool

## Synopsis

```
tg-delete-mcp-tool [OPTIONS] --name NAME
```

## Description

The `tg-delete-mcp-tool` command deletes MCP (Model Control Protocol) tools from the TrustGraph system. It removes MCP tool configurations by name from the 'mcp' configuration group. Once deleted, MCP tools are no longer available for agent use.

This command is useful for:
- Removing obsolete or deprecated MCP tools
- Cleaning up MCP tool configurations
- Managing MCP tool registry maintenance
- Updating MCP tool deployments by removing old versions

The command removes MCP tool configurations from the 'mcp' configuration group in the TrustGraph API.

## Options

- `-u, --api-url URL`
  - TrustGraph API URL for configuration management
  - Default: `http://localhost:8088/` (or `TRUSTGRAPH_URL` environment variable)
  - Should point to a running TrustGraph API instance

- `--name NAME`
  - **Required.** MCP tool name to delete
  - Must match an existing MCP tool name in the registry
  - MCP tool will be completely removed from the system

- `-h, --help`
  - Show help message and exit

## Examples

### Basic MCP Tool Deletion

Delete a weather MCP tool:
```bash
tg-delete-mcp-tool --name weather
```

### Calculator MCP Tool Deletion

Delete a calculator MCP tool:
```bash
tg-delete-mcp-tool --name calculator
```

### Custom API URL

Delete an MCP tool from a specific TrustGraph instance:
```bash
tg-delete-mcp-tool --api-url http://trustgraph.example.com:8088/ --name custom-mcp
```

### Batch MCP Tool Deletion

Delete multiple MCP tools in a script:
```bash
#!/bin/bash
# Delete obsolete MCP tools
tg-delete-mcp-tool --name old-search
tg-delete-mcp-tool --name deprecated-calc
tg-delete-mcp-tool --name unused-mcp
```

### Conditional Deletion

Delete an MCP tool only if it exists:
```bash
#!/bin/bash
# Check if MCP tool exists before deletion
if tg-show-mcp-tools | grep -q "test-mcp"; then
    tg-delete-mcp-tool --name test-mcp
    echo "MCP tool deleted"
else
    echo "MCP tool not found"
fi
```

## Deletion Process

The deletion process involves:

1. **Existence Check**: Verify the MCP tool exists in the configuration
2. **Configuration Removal**: Delete the MCP tool configuration from the 'mcp' group

The command performs validation before deletion to ensure the tool exists.

## Error Handling

The command handles various error conditions:

- **Tool not found**: If the specified MCP tool name doesn't exist
- **API connection errors**: If the TrustGraph API is unavailable
- **Configuration errors**: If the MCP tool configuration cannot be removed

Common error scenarios:
```bash
# MCP tool not found
tg-delete-mcp-tool --name nonexistent-mcp
# Output: MCP tool 'nonexistent-mcp' not found.

# Missing required field
tg-delete-mcp-tool
# Output: Exception: Must specify --name for MCP tool to delete

# API connection error
tg-delete-mcp-tool --api-url http://invalid-host:8088/ --name tool1
# Output: Exception: [Connection error details]
```

## Verification

The command provides feedback on the deletion process:

- **Success**: `MCP tool 'tool-name' deleted successfully.`
- **Not found**: `MCP tool 'tool-name' not found.`
- **Error**: `Error deleting MCP tool 'tool-name': [error details]`

## Advanced Usage

### Safe Deletion with Verification

Verify MCP tool exists before deletion:
```bash
#!/bin/bash
MCP_NAME="weather"

# Check if MCP tool exists
if tg-show-mcp-tools | grep -q "^$MCP_NAME"; then
    echo "Deleting MCP tool: $MCP_NAME"
    tg-delete-mcp-tool --name "$MCP_NAME"
    
    # Verify deletion
    if ! tg-show-mcp-tools | grep -q "^$MCP_NAME"; then
        echo "MCP tool successfully deleted"
    else
        echo "MCP tool deletion failed"
    fi
else
    echo "MCP tool $MCP_NAME not found"
fi
```

### Backup Before Deletion

Backup MCP tool configuration before deletion:
```bash
#!/bin/bash
MCP_NAME="important-mcp"

# Export MCP tool configuration
echo "Backing up MCP tool configuration..."
tg-show-mcp-tools | grep -A 10 "^$MCP_NAME" > "${MCP_NAME}_backup.txt"

# Delete MCP tool
echo "Deleting MCP tool..."
tg-delete-mcp-tool --name "$MCP_NAME"

echo "MCP tool deleted, backup saved to ${MCP_NAME}_backup.txt"
```

### Cleanup Script

Clean up multiple MCP tools based on patterns:
```bash
#!/bin/bash
# Delete all test MCP tools
echo "Cleaning up test MCP tools..."

# Get list of test MCP tools
TEST_MCPS=$(tg-show-mcp-tools | grep "^test-" | cut -d: -f1)

for mcp in $TEST_MCPS; do
    echo "Deleting $mcp..."
    tg-delete-mcp-tool --name "$mcp"
done

echo "Cleanup complete"
```

### Environment-Specific Deletion

Delete MCP tools from specific environments:
```bash
#!/bin/bash
# Delete development MCP tools from production
export TRUSTGRAPH_URL="http://prod.trustgraph.com:8088/"

DEV_MCPS=("dev-mcp" "debug-mcp" "test-helper")

for mcp in "${DEV_MCPS[@]}"; do
    echo "Removing development MCP tool: $mcp"
    tg-delete-mcp-tool --name "$mcp"
done
```

### MCP Service Shutdown

Remove MCP tools when services are decommissioned:
```bash
#!/bin/bash
# Remove MCP tools for decommissioned service
SERVICE_NAME="old-service"

# Find MCP tools for this service
MCP_TOOLS=$(tg-show-mcp-tools | grep "$SERVICE_NAME" | cut -d: -f1)

for tool in $MCP_TOOLS; do
    echo "Removing MCP tool for decommissioned service: $tool"
    tg-delete-mcp-tool --name "$tool"
done
```

## Integration with Other Commands

### With MCP Tool Management

List and delete MCP tools:
```bash
# List all MCP tools
tg-show-mcp-tools

# Delete specific MCP tool
tg-delete-mcp-tool --name unwanted-mcp

# Verify deletion
tg-show-mcp-tools | grep unwanted-mcp
```

### With Configuration Management

Manage MCP tool configurations:
```bash
# View current configuration
tg-show-config

# Delete MCP tool
tg-delete-mcp-tool --name old-mcp

# View updated configuration
tg-show-config
```

### With MCP Tool Invocation

Ensure MCP tools can't be invoked after deletion:
```bash
# Delete MCP tool
tg-delete-mcp-tool --name deprecated-mcp

# Verify tool is no longer available
tg-invoke-mcp-tool --name deprecated-mcp
# Should fail with tool not found error
```

## Best Practices

1. **Verification**: Always verify MCP tool exists before deletion
2. **Backup**: Backup important MCP tool configurations before deletion
3. **Dependencies**: Check for MCP tool dependencies before deletion
4. **Service Coordination**: Coordinate with MCP service owners before deletion
5. **Testing**: Test system functionality after MCP tool deletion
6. **Documentation**: Document reasons for MCP tool deletion
7. **Gradual Removal**: Remove MCP tools gradually in production environments
8. **Monitoring**: Monitor for errors after MCP tool deletion

## Troubleshooting

### MCP Tool Not Found

If MCP tool deletion reports "not found":
1. Verify the MCP tool name is correct
2. Check MCP tool exists with `tg-show-mcp-tools`
3. Ensure you're connected to the correct TrustGraph instance
4. Check for case sensitivity in MCP tool name

### Deletion Errors

If deletion fails:
1. Check TrustGraph API connectivity
2. Verify API permissions
3. Check for configuration corruption
4. Retry the deletion operation
5. Check MCP service status

### Permission Errors

If deletion fails due to permissions:
1. Verify API access credentials
2. Check TrustGraph API permissions
3. Ensure proper authentication
4. Contact system administrator if needed

## Recovery

### Restore Deleted MCP Tool

If an MCP tool was accidentally deleted:
1. Use backup configuration if available
2. Re-register the MCP tool with `tg-set-mcp-tool`
3. Restore from version control if MCP tool definitions are tracked
4. Contact system administrator for recovery options

### Verify System State

After deletion, verify system state:
```bash
# Check MCP tool registry
tg-show-mcp-tools

# Verify no orphaned configurations
tg-show-config | grep "mcp\."

# Test MCP tool functionality
tg-invoke-mcp-tool --name remaining-tool
```

## MCP Tool Lifecycle

### Development to Production

Manage MCP tool lifecycle:
```bash
#!/bin/bash
# Promote MCP tool from dev to production

# Remove development version
tg-delete-mcp-tool --name dev-tool

# Add production version
tg-set-mcp-tool --name prod-tool --tool-url "http://prod.mcp.com/api"
```

### Version Management

Manage MCP tool versions:
```bash
#!/bin/bash
# Update MCP tool to new version

# Remove old version
tg-delete-mcp-tool --name tool-v1

# Add new version
tg-set-mcp-tool --name tool-v2 --tool-url "http://new.mcp.com/api"
```

## Security Considerations

When deleting MCP tools:

1. **Access Control**: Ensure proper authorization for deletion
2. **Audit Trail**: Log MCP tool deletions for security auditing
3. **Impact Assessment**: Assess security impact of tool removal
4. **Credential Cleanup**: Remove associated credentials if applicable
5. **Network Security**: Update firewall rules if MCP endpoints are no longer needed

## Related Commands

- [`tg-show-mcp-tools`](tg-show-mcp-tools.md) - Display registered MCP tools
- [`tg-set-mcp-tool`](tg-set-mcp-tool.md) - Configure and register MCP tools
- [`tg-invoke-mcp-tool`](tg-invoke-mcp-tool.md) - Execute MCP tools
- [`tg-delete-tool`](tg-delete-tool.md) - Delete regular agent tools

## See Also

- MCP Protocol Documentation
- TrustGraph MCP Integration Guide
- MCP Tool Management Manual