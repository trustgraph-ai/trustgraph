# tg-delete-flow-blueprint

Permanently deletes a flow blueprint definition from TrustGraph.

## Synopsis

```bash
tg-delete-flow-blueprint -n CLASS_NAME [options]
```

## Description

The `tg-delete-flow-blueprint` command permanently removes a flow blueprint definition from TrustGraph. This operation cannot be undone, so use with caution.

**⚠️ Warning**: Deleting a flow blueprint that has active flow instances may cause those instances to become unusable. Always check for active flows before deletion.

## Options

### Required Arguments

- `-n, --blueprint-name CLASS_NAME`: Name of the flow blueprint to delete

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Delete a Flow Blueprint
```bash
tg-delete-flow-blueprint -n "old-test-flow"
```

### Delete with Custom API URL
```bash
tg-delete-flow-blueprint -n "deprecated-flow" -u http://staging:8088/
```

### Safe Deletion Workflow
```bash
# 1. Check if flow blueprint exists
tg-show-flow-blueprints | grep "target-flow"

# 2. Backup the flow blueprint first
tg-get-flow-blueprint -n "target-flow" > backup-target-flow.json

# 3. Check for active flow instances
tg-show-flows | grep "target-flow"

# 4. Delete the flow blueprint
tg-delete-flow-blueprint -n "target-flow"

# 5. Verify deletion
tg-show-flow-blueprints | grep "target-flow" || echo "Flow blueprint deleted successfully"
```

## Prerequisites

### Flow Blueprint Must Exist
Verify the flow blueprint exists before attempting deletion:

```bash
# List all flow blueprintes
tg-show-flow-blueprints

# Check specific flow blueprint
tg-show-flow-blueprints | grep "target-class"
```

### Check for Active Flow Instances
Before deleting a flow blueprint, check if any flow instances are using it:

```bash
# List all active flows
tg-show-flows

# Look for instances using the flow blueprint
tg-show-flows | grep "target-class"
```

## Error Handling

### Flow Blueprint Not Found
```bash
Exception: Flow blueprint 'nonexistent-class' not found
```
**Solution**: Verify the flow blueprint exists with `tg-show-flow-blueprints`.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Access denied to delete flow blueprint
```
**Solution**: Verify user permissions for flow blueprint management.

### Active Flow Instances
```bash
Exception: Cannot delete flow blueprint with active instances
```
**Solution**: Stop all flow instances using this class before deletion.

## Use Cases

### Cleanup Development Classes
```bash
# Delete test and development flow blueprintes
test_classes=("test-flow-v1" "dev-experiment" "prototype-flow")
for class in "${test_classes[@]}"; do
    echo "Deleting $class..."
    tg-delete-flow-blueprint -n "$class"
done
```

### Migration Cleanup
```bash
# After migrating to new flow blueprintes, remove old ones
old_classes=("legacy-flow" "deprecated-processor" "old-pipeline")
for class in "${old_classes[@]}"; do
    # Backup first
    tg-get-flow-blueprint -n "$class" > "backup-$class.json" 2>/dev/null
    
    # Delete
    tg-delete-flow-blueprint -n "$class"
    echo "Deleted $class"
done
```

### Conditional Deletion
```bash
# Delete flow blueprint only if no active instances exist
flow_class="target-flow"
active_instances=$(tg-show-flows | grep "$flow_class" | wc -l)

if [ $active_instances -eq 0 ]; then
    echo "No active instances found, deleting flow blueprint..."
    tg-delete-flow-blueprint -n "$flow_class"
else
    echo "Warning: $active_instances active instances found. Cannot delete."
    tg-show-flows | grep "$flow_class"
fi
```

## Safety Considerations

### Always Backup First
```bash
# Create backup before deletion
flow_class="important-flow"
backup_dir="flow-class-backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"

echo "Backing up flow blueprint: $flow_class"
tg-get-flow-blueprint -n "$flow_class" > "$backup_dir/$flow_class.json"

if [ $? -eq 0 ]; then
    echo "Backup created: $backup_dir/$flow_class.json"
    echo "Proceeding with deletion..."
    tg-delete-flow-blueprint -n "$flow_class"
else
    echo "Backup failed. Aborting deletion."
    exit 1
fi
```

### Verification Script
```bash
#!/bin/bash
# safe-delete-flow-class.sh
flow_class="$1"

if [ -z "$flow_class" ]; then
    echo "Usage: $0 <flow-blueprint-name>"
    exit 1
fi

echo "Safety checks for deleting flow blueprint: $flow_class"

# Check if flow blueprint exists
if ! tg-show-flow-blueprints | grep -q "$flow_class"; then
    echo "ERROR: Flow blueprint '$flow_class' not found"
    exit 1
fi

# Check for active instances
active_count=$(tg-show-flows | grep "$flow_class" | wc -l)
if [ $active_count -gt 0 ]; then
    echo "ERROR: Found $active_count active instances using this flow blueprint"
    echo "Active instances:"
    tg-show-flows | grep "$flow_class"
    exit 1
fi

# Create backup
backup_file="backup-$flow_class-$(date +%Y%m%d-%H%M%S).json"
echo "Creating backup: $backup_file"
tg-get-flow-blueprint -n "$flow_class" > "$backup_file"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create backup"
    exit 1
fi

# Confirm deletion
echo "Ready to delete flow blueprint: $flow_class"
echo "Backup saved as: $backup_file"
read -p "Are you sure you want to delete this flow blueprint? (y/N): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    echo "Deleting flow blueprint..."
    tg-delete-flow-blueprint -n "$flow_class"
    
    # Verify deletion
    if ! tg-show-flow-blueprints | grep -q "$flow_class"; then
        echo "Flow blueprint deleted successfully"
    else
        echo "ERROR: Flow blueprint still exists after deletion"
        exit 1
    fi
else
    echo "Deletion cancelled"
    rm "$backup_file"
fi
```

## Integration with Other Commands

### Complete Flow Blueprint Lifecycle
```bash
# 1. List existing flow blueprintes
tg-show-flow-blueprints

# 2. Get flow blueprint details
tg-get-flow-blueprint -n "target-flow"

# 3. Check for active instances
tg-show-flows | grep "target-flow"

# 4. Stop active instances if needed
tg-stop-flow -i "instance-id"

# 5. Create backup
tg-get-flow-blueprint -n "target-flow" > backup.json

# 6. Delete flow blueprint
tg-delete-flow-blueprint -n "target-flow"

# 7. Verify deletion
tg-show-flow-blueprints | grep "target-flow"
```

### Bulk Deletion with Validation
```bash
# Delete multiple flow blueprintes safely
classes_to_delete=("old-flow1" "old-flow2" "test-flow")

for class in "${classes_to_delete[@]}"; do
    echo "Processing $class..."
    
    # Check if exists
    if ! tg-show-flow-blueprints | grep -q "$class"; then
        echo "  $class not found, skipping"
        continue
    fi
    
    # Check for active instances
    if tg-show-flows | grep -q "$class"; then
        echo "  $class has active instances, skipping"
        continue
    fi
    
    # Backup and delete
    tg-get-flow-blueprint -n "$class" > "backup-$class.json"
    tg-delete-flow-blueprint -n "$class"
    echo "  $class deleted"
done
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-flow-blueprints`](tg-show-flow-blueprints.md) - List available flow blueprintes
- [`tg-get-flow-blueprint`](tg-get-flow-blueprint.md) - Retrieve flow blueprint definitions
- [`tg-put-flow-blueprint`](tg-put-flow-blueprint.md) - Create/update flow blueprint definitions
- [`tg-show-flows`](tg-show-flows.md) - List active flow instances
- [`tg-stop-flow`](tg-stop-flow.md) - Stop flow instances

## API Integration

This command uses the [Flow API](../apis/api-flow.md) with the `delete-class` operation to remove flow blueprint definitions.

## Best Practices

1. **Always Backup**: Create backups before deletion
2. **Check Dependencies**: Verify no active flow instances exist
3. **Confirmation**: Use interactive confirmation for important deletions
4. **Logging**: Log deletion operations for audit trails
5. **Permissions**: Ensure appropriate access controls for deletion operations
6. **Testing**: Test deletion procedures in non-production environments first

## Troubleshooting

### Command Succeeds but Class Still Exists
```bash
# Check if deletion actually occurred
tg-show-flow-blueprints | grep "deleted-class"

# Verify API connectivity
tg-show-flow-blueprints > /dev/null && echo "API accessible"
```

### Permissions Issues
```bash
# Verify user has deletion permissions
# Contact system administrator if access denied
```

### Network Connectivity
```bash
# Test API connectivity
curl -s "$TRUSTGRAPH_URL/api/v1/flow/classes" > /dev/null
echo "API response: $?"
```