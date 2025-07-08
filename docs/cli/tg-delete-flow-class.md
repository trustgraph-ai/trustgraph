# tg-delete-flow-class

Permanently deletes a flow class definition from TrustGraph.

## Synopsis

```bash
tg-delete-flow-class -n CLASS_NAME [options]
```

## Description

The `tg-delete-flow-class` command permanently removes a flow class definition from TrustGraph. This operation cannot be undone, so use with caution.

**⚠️ Warning**: Deleting a flow class that has active flow instances may cause those instances to become unusable. Always check for active flows before deletion.

## Options

### Required Arguments

- `-n, --class-name CLASS_NAME`: Name of the flow class to delete

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Delete a Flow Class
```bash
tg-delete-flow-class -n "old-test-flow"
```

### Delete with Custom API URL
```bash
tg-delete-flow-class -n "deprecated-flow" -u http://staging:8088/
```

### Safe Deletion Workflow
```bash
# 1. Check if flow class exists
tg-show-flow-classes | grep "target-flow"

# 2. Backup the flow class first
tg-get-flow-class -n "target-flow" > backup-target-flow.json

# 3. Check for active flow instances
tg-show-flows | grep "target-flow"

# 4. Delete the flow class
tg-delete-flow-class -n "target-flow"

# 5. Verify deletion
tg-show-flow-classes | grep "target-flow" || echo "Flow class deleted successfully"
```

## Prerequisites

### Flow Class Must Exist
Verify the flow class exists before attempting deletion:

```bash
# List all flow classes
tg-show-flow-classes

# Check specific flow class
tg-show-flow-classes | grep "target-class"
```

### Check for Active Flow Instances
Before deleting a flow class, check if any flow instances are using it:

```bash
# List all active flows
tg-show-flows

# Look for instances using the flow class
tg-show-flows | grep "target-class"
```

## Error Handling

### Flow Class Not Found
```bash
Exception: Flow class 'nonexistent-class' not found
```
**Solution**: Verify the flow class exists with `tg-show-flow-classes`.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Access denied to delete flow class
```
**Solution**: Verify user permissions for flow class management.

### Active Flow Instances
```bash
Exception: Cannot delete flow class with active instances
```
**Solution**: Stop all flow instances using this class before deletion.

## Use Cases

### Cleanup Development Classes
```bash
# Delete test and development flow classes
test_classes=("test-flow-v1" "dev-experiment" "prototype-flow")
for class in "${test_classes[@]}"; do
    echo "Deleting $class..."
    tg-delete-flow-class -n "$class"
done
```

### Migration Cleanup
```bash
# After migrating to new flow classes, remove old ones
old_classes=("legacy-flow" "deprecated-processor" "old-pipeline")
for class in "${old_classes[@]}"; do
    # Backup first
    tg-get-flow-class -n "$class" > "backup-$class.json" 2>/dev/null
    
    # Delete
    tg-delete-flow-class -n "$class"
    echo "Deleted $class"
done
```

### Conditional Deletion
```bash
# Delete flow class only if no active instances exist
flow_class="target-flow"
active_instances=$(tg-show-flows | grep "$flow_class" | wc -l)

if [ $active_instances -eq 0 ]; then
    echo "No active instances found, deleting flow class..."
    tg-delete-flow-class -n "$flow_class"
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

echo "Backing up flow class: $flow_class"
tg-get-flow-class -n "$flow_class" > "$backup_dir/$flow_class.json"

if [ $? -eq 0 ]; then
    echo "Backup created: $backup_dir/$flow_class.json"
    echo "Proceeding with deletion..."
    tg-delete-flow-class -n "$flow_class"
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
    echo "Usage: $0 <flow-class-name>"
    exit 1
fi

echo "Safety checks for deleting flow class: $flow_class"

# Check if flow class exists
if ! tg-show-flow-classes | grep -q "$flow_class"; then
    echo "ERROR: Flow class '$flow_class' not found"
    exit 1
fi

# Check for active instances
active_count=$(tg-show-flows | grep "$flow_class" | wc -l)
if [ $active_count -gt 0 ]; then
    echo "ERROR: Found $active_count active instances using this flow class"
    echo "Active instances:"
    tg-show-flows | grep "$flow_class"
    exit 1
fi

# Create backup
backup_file="backup-$flow_class-$(date +%Y%m%d-%H%M%S).json"
echo "Creating backup: $backup_file"
tg-get-flow-class -n "$flow_class" > "$backup_file"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create backup"
    exit 1
fi

# Confirm deletion
echo "Ready to delete flow class: $flow_class"
echo "Backup saved as: $backup_file"
read -p "Are you sure you want to delete this flow class? (y/N): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    echo "Deleting flow class..."
    tg-delete-flow-class -n "$flow_class"
    
    # Verify deletion
    if ! tg-show-flow-classes | grep -q "$flow_class"; then
        echo "Flow class deleted successfully"
    else
        echo "ERROR: Flow class still exists after deletion"
        exit 1
    fi
else
    echo "Deletion cancelled"
    rm "$backup_file"
fi
```

## Integration with Other Commands

### Complete Flow Class Lifecycle
```bash
# 1. List existing flow classes
tg-show-flow-classes

# 2. Get flow class details
tg-get-flow-class -n "target-flow"

# 3. Check for active instances
tg-show-flows | grep "target-flow"

# 4. Stop active instances if needed
tg-stop-flow -i "instance-id"

# 5. Create backup
tg-get-flow-class -n "target-flow" > backup.json

# 6. Delete flow class
tg-delete-flow-class -n "target-flow"

# 7. Verify deletion
tg-show-flow-classes | grep "target-flow"
```

### Bulk Deletion with Validation
```bash
# Delete multiple flow classes safely
classes_to_delete=("old-flow1" "old-flow2" "test-flow")

for class in "${classes_to_delete[@]}"; do
    echo "Processing $class..."
    
    # Check if exists
    if ! tg-show-flow-classes | grep -q "$class"; then
        echo "  $class not found, skipping"
        continue
    fi
    
    # Check for active instances
    if tg-show-flows | grep -q "$class"; then
        echo "  $class has active instances, skipping"
        continue
    fi
    
    # Backup and delete
    tg-get-flow-class -n "$class" > "backup-$class.json"
    tg-delete-flow-class -n "$class"
    echo "  $class deleted"
done
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-flow-classes`](tg-show-flow-classes.md) - List available flow classes
- [`tg-get-flow-class`](tg-get-flow-class.md) - Retrieve flow class definitions
- [`tg-put-flow-class`](tg-put-flow-class.md) - Create/update flow class definitions
- [`tg-show-flows`](tg-show-flows.md) - List active flow instances
- [`tg-stop-flow`](tg-stop-flow.md) - Stop flow instances

## API Integration

This command uses the [Flow API](../apis/api-flow.md) with the `delete-class` operation to remove flow class definitions.

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
tg-show-flow-classes | grep "deleted-class"

# Verify API connectivity
tg-show-flow-classes > /dev/null && echo "API accessible"
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