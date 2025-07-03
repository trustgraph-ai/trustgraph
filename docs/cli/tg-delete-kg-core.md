# tg-delete-kg-core

Permanently removes a knowledge core from the TrustGraph system.

## Synopsis

```bash
tg-delete-kg-core --id CORE_ID [options]
```

## Description

The `tg-delete-kg-core` command permanently removes a stored knowledge core from the TrustGraph system. This operation is irreversible and will delete all RDF triples, graph embeddings, and metadata associated with the specified knowledge core.

**Warning**: This operation permanently deletes data. Ensure you have backups if the knowledge core might be needed in the future.

## Options

### Required Arguments

- `--id, --identifier CORE_ID`: Identifier of the knowledge core to delete

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-U, --user USER`: User identifier (default: `trustgraph`)

## Examples

### Delete Specific Knowledge Core
```bash
tg-delete-kg-core --id "old-research-data"
```

### Delete with Specific User
```bash
tg-delete-kg-core --id "test-knowledge" -U developer
```

### Using Custom API URL
```bash
tg-delete-kg-core --id "obsolete-core" -u http://production:8088/
```

## Prerequisites

### Knowledge Core Must Exist
Verify the knowledge core exists before deletion:

```bash
# Check available knowledge cores
tg-show-kg-cores

# Ensure the core exists
tg-show-kg-cores | grep "target-core-id"
```

### Backup Important Data
Create backups before deletion:

```bash
# Export knowledge core before deletion
tg-get-kg-core --id "important-core" -o backup.msgpack

# Then proceed with deletion
tg-delete-kg-core --id "important-core"
```

## Safety Considerations

### Unload from Flows First
Unload the knowledge core from any active flows:

```bash
# Check which flows might be using the core
tg-show-flows

# Unload from active flows
tg-unload-kg-core --id "target-core" --flow-id "active-flow"

# Then delete the core
tg-delete-kg-core --id "target-core"
```

### Verify Dependencies
Check if other systems depend on the knowledge core:

```bash
# Search for references in flow configurations
tg-show-config | grep "target-core"

# Check processing history
tg-show-library-processing | grep "target-core"
```

## Deletion Process

1. **Validation**: Verifies knowledge core exists and user has permission
2. **Dependency Check**: Ensures core is not actively loaded in flows
3. **Data Removal**: Permanently deletes RDF triples and graph embeddings
4. **Metadata Cleanup**: Removes all associated metadata and references
5. **Index Updates**: Updates system indexes to reflect deletion

## Output

Successful deletion typically produces no output:

```bash
# Delete core (no output expected on success)
tg-delete-kg-core --id "test-core"

# Verify deletion
tg-show-kg-cores | grep "test-core"
# Should return no results
```

## Error Handling

### Knowledge Core Not Found
```bash
Exception: Knowledge core 'invalid-core' not found
```
**Solution**: Check available cores with `tg-show-kg-cores` and verify the core ID.

### Permission Denied
```bash
Exception: Access denied to knowledge core
```
**Solution**: Verify user permissions and ownership of the knowledge core.

### Core In Use
```bash
Exception: Knowledge core is currently loaded in active flows
```
**Solution**: Unload the core from all flows before deletion using `tg-unload-kg-core`.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

## Deletion Verification

### Confirm Deletion
```bash
# Verify core no longer exists
tg-show-kg-cores | grep "deleted-core-id"

# Should return no results if successfully deleted
echo $?  # Should be 1 (not found)
```

### Check Flow Impact
```bash
# Verify flows are not affected
tg-show-flows

# Test that queries still work for remaining knowledge
tg-invoke-graph-rag -q "test query" -f remaining-flow
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-kg-cores`](tg-show-kg-cores.md) - List available knowledge cores
- [`tg-get-kg-core`](tg-get-kg-core.md) - Export knowledge core for backup
- [`tg-unload-kg-core`](tg-unload-kg-core.md) - Unload core from flows
- [`tg-put-kg-core`](tg-put-kg-core.md) - Store new knowledge cores

## API Integration

This command uses the [Knowledge API](../apis/api-knowledge.md) with the `delete-kg-core` operation to permanently remove knowledge cores.

## Use Cases

### Development Cleanup
```bash
# Remove test knowledge cores
tg-delete-kg-core --id "test-data-v1" -U developer
tg-delete-kg-core --id "experimental-core" -U developer
```

### Version Management
```bash
# Remove obsolete versions after upgrading
tg-get-kg-core --id "knowledge-v1" -o backup-v1.msgpack
tg-delete-kg-core --id "knowledge-v1"
# Keep only knowledge-v2
```

### Storage Cleanup
```bash
# Clean up unused knowledge cores
for core in $(tg-show-kg-cores | grep "temp-"); do
    echo "Deleting temporary core: $core"
    tg-delete-kg-core --id "$core"
done
```

### Error Recovery
```bash
# Remove corrupted knowledge cores
tg-delete-kg-core --id "corrupted-core-2024"
tg-put-kg-core --id "restored-core-2024" -i restored-backup.msgpack
```

## Safe Deletion Workflow

### Standard Procedure
```bash
# 1. Backup the knowledge core
tg-get-kg-core --id "target-core" -o "backup-$(date +%Y%m%d).msgpack"

# 2. Unload from active flows
tg-unload-kg-core --id "target-core" --flow-id "production-flow"

# 3. Verify no dependencies
tg-show-config | grep "target-core"

# 4. Perform deletion
tg-delete-kg-core --id "target-core"

# 5. Verify deletion
tg-show-kg-cores | grep "target-core"
```

### Bulk Deletion
```bash
# Delete multiple cores safely
cores_to_delete=("old-core-1" "old-core-2" "test-core")

for core in "${cores_to_delete[@]}"; do
    echo "Processing $core..."
    
    # Backup
    tg-get-kg-core --id "$core" -o "backup-$core-$(date +%Y%m%d).msgpack"
    
    # Delete
    tg-delete-kg-core --id "$core"
    
    # Verify
    if tg-show-kg-cores | grep -q "$core"; then
        echo "ERROR: $core still exists after deletion"
    else
        echo "SUCCESS: $core deleted"
    fi
done
```

## Best Practices

1. **Always Backup**: Export knowledge cores before deletion
2. **Check Dependencies**: Verify no flows are using the core
3. **Staged Deletion**: Delete test/development cores before production
4. **Verification**: Confirm deletion completed successfully
5. **Documentation**: Record why cores were deleted for audit purposes
6. **Access Control**: Ensure only authorized users can delete cores

## Recovery Options

### If Accidentally Deleted
```bash
# Restore from backup if available
tg-put-kg-core --id "restored-core" -i backup.msgpack

# Reload into flows if needed
tg-load-kg-core --id "restored-core" --flow-id "production-flow"
```

### Audit Trail
```bash
# Keep records of deletions
echo "$(date): Deleted knowledge core 'old-core' - reason: obsolete version" >> deletion-log.txt
```

## System Impact

### Storage Recovery
- Disk space is freed immediately
- Database indexes are updated
- System performance may improve

### Service Continuity
- Running flows continue to operate
- Other knowledge cores remain unaffected
- New knowledge cores can use the same ID

## Troubleshooting

### Deletion Fails
```bash
# Check if core is loaded in flows
tg-show-flows | grep -A 10 "knowledge"

# Force unload if necessary
tg-unload-kg-core --id "stuck-core" --flow-id "problem-flow"

# Retry deletion
tg-delete-kg-core --id "stuck-core"
```

### Partial Deletion
```bash
# If core still appears in listings
tg-show-kg-cores | grep "partially-deleted"

# Contact system administrator if deletion appears incomplete
```