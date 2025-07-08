# tg-get-kg-core

Exports a knowledge core from TrustGraph to a MessagePack file.

## Synopsis

```bash
tg-get-kg-core --id CORE_ID -o OUTPUT_FILE [options]
```

## Description

The `tg-get-kg-core` command retrieves a stored knowledge core from TrustGraph and exports it to a MessagePack format file. This allows you to backup knowledge cores, transfer them between systems, or examine their contents offline.

The exported file contains both RDF triples and graph embeddings in a compact binary format that can later be imported using `tg-put-kg-core`.

## Options

### Required Arguments

- `--id, --identifier CORE_ID`: Identifier of the knowledge core to export
- `-o, --output OUTPUT_FILE`: Path for the output MessagePack file

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `ws://localhost:8088/`)
- `-U, --user USER`: User identifier (default: `trustgraph`)

## Examples

### Basic Knowledge Core Export
```bash
tg-get-kg-core --id "research-knowledge" -o research-backup.msgpack
```

### Export with Specific User
```bash
tg-get-kg-core \
  --id "medical-knowledge" \
  -o medical-backup.msgpack \
  -U medical-team
```

### Export with Timestamped Filename
```bash
tg-get-kg-core \
  --id "production-core" \
  -o "production-backup-$(date +%Y%m%d-%H%M%S).msgpack"
```

### Using Custom API URL
```bash
tg-get-kg-core \
  --id "remote-core" \
  -o remote-backup.msgpack \
  -u ws://production:8088/
```

## Prerequisites

### Knowledge Core Must Exist
Verify the knowledge core exists:

```bash
# Check available knowledge cores
tg-show-kg-cores

# Verify specific core exists
tg-show-kg-cores | grep "target-core-id"
```

### Output Directory Must Be Writable
Ensure the output directory exists and is writable:

```bash
# Create backup directory if needed
mkdir -p backups

# Export to backup directory
tg-get-kg-core --id "my-core" -o backups/my-core-backup.msgpack
```

## Export Process

1. **Connection**: Establishes WebSocket connection to Knowledge API
2. **Request**: Sends get-kg-core request with core ID and user
3. **Streaming**: Receives data in chunks via WebSocket
4. **Processing**: Converts response data to MessagePack format
5. **Writing**: Writes binary data to output file
6. **Summary**: Reports statistics on exported data

## Output Format

The exported MessagePack file contains structured data with two types of messages:

### Triple Messages (`"t"`)
Contains RDF triples (facts and relationships):
```python
("t", {
    "m": {  # metadata
        "i": "core-id",
        "m": [],  # metadata triples
        "u": "user",
        "c": "collection"
    },
    "t": [  # triples array
        {
            "s": {"value": "subject", "is_uri": true},
            "p": {"value": "predicate", "is_uri": true},
            "o": {"value": "object", "is_uri": false}
        }
    ]
})
```

### Graph Embedding Messages (`"ge"`)
Contains vector embeddings for entities:
```python
("ge", {
    "m": {  # metadata
        "i": "core-id",
        "m": [],  # metadata triples
        "u": "user",
        "c": "collection"
    },
    "e": [  # entities array
        {
            "e": {"value": "entity", "is_uri": true},
            "v": [[0.1, 0.2, 0.3]]  # vectors
        }
    ]
})
```

## Output Statistics

The command reports the number of messages exported:

```bash
Got: 150 triple, 75 GE messages.
```

Where:
- **triple**: Number of RDF triple message chunks exported
- **GE**: Number of graph embedding message chunks exported

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
**Solution**: Verify user permissions for the specified knowledge core.

### File Permission Errors
```bash
Exception: Permission denied: output.msgpack
```
**Solution**: Check write permissions for the output directory and filename.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Disk Space Errors
```bash
Exception: No space left on device
```
**Solution**: Free up disk space or use a different output location.

## File Management

### Backup Organization
```bash
# Create organized backup structure
mkdir -p backups/{daily,weekly,monthly}

# Daily backup
tg-get-kg-core --id "prod-core" -o "backups/daily/prod-$(date +%Y%m%d).msgpack"

# Weekly backup
tg-get-kg-core --id "prod-core" -o "backups/weekly/prod-week-$(date +%V).msgpack"
```

### Compression
```bash
# Export and compress for storage
tg-get-kg-core --id "large-core" -o large-core.msgpack
gzip large-core.msgpack

# Results in large-core.msgpack.gz
```

## File Verification

### Check File Size
```bash
# Export and verify
tg-get-kg-core --id "my-core" -o my-core.msgpack
ls -lh my-core.msgpack

# Typical sizes: small cores (KB-MB), large cores (MB-GB)
```

### Validate Export
```bash
# Test the exported file by importing to different ID
tg-put-kg-core --id "test-import" -i my-core.msgpack
tg-show-kg-cores | grep "test-import"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL (automatically converted to WebSocket format)

## Related Commands

- [`tg-put-kg-core`](tg-put-kg-core.md) - Import knowledge core from MessagePack file
- [`tg-show-kg-cores`](tg-show-kg-cores.md) - List available knowledge cores
- [`tg-delete-kg-core`](tg-delete-kg-core.md) - Delete knowledge cores
- [`tg-dump-msgpack`](tg-dump-msgpack.md) - Examine MessagePack file contents

## API Integration

This command uses the [Knowledge API](../apis/api-knowledge.md) via WebSocket connection with `get-kg-core` operations to retrieve knowledge data.

## Use Cases

### Regular Backups
```bash
#!/bin/bash
# Daily backup script
cores=("production-core" "research-core" "customer-data")
backup_dir="backups/$(date +%Y%m%d)"
mkdir -p "$backup_dir"

for core in "${cores[@]}"; do
    echo "Backing up $core..."
    tg-get-kg-core --id "$core" -o "$backup_dir/$core.msgpack"
done
```

### Migration Between Environments
```bash
# Export from development
tg-get-kg-core --id "dev-knowledge" -o dev-export.msgpack

# Import to staging
tg-put-kg-core --id "staging-knowledge" -i dev-export.msgpack
```

### Knowledge Core Versioning
```bash
# Create versioned backups
version="v$(date +%Y%m%d)"
tg-get-kg-core --id "main-knowledge" -o "knowledge-$version.msgpack"

# Tag with git or other version control
git add "knowledge-$version.msgpack"
git commit -m "Knowledge core backup $version"
```

### Data Analysis
```bash
# Export for offline analysis
tg-get-kg-core --id "analytics-data" -o analytics.msgpack

# Process with custom tools
python analyze_knowledge.py analytics.msgpack
```

### Disaster Recovery
```bash
# Create comprehensive backup
cores=$(tg-show-kg-cores)
backup_date=$(date +%Y%m%d-%H%M%S)
backup_dir="disaster-recovery-$backup_date"
mkdir -p "$backup_dir"

for core in $cores; do
    echo "Backing up $core..."
    tg-get-kg-core --id "$core" -o "$backup_dir/$core.msgpack"
done

# Create checksum file
cd "$backup_dir"
sha256sum *.msgpack > checksums.sha256
```

## Automated Backup Strategies

### Cron Job Setup
```bash
# Add to crontab for daily backups at 2 AM
# 0 2 * * * /path/to/backup-script.sh

#!/bin/bash
# backup-script.sh
BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup all cores
tg-show-kg-cores | while read core; do
    tg-get-kg-core --id "$core" -o "$BACKUP_DIR/$core.msgpack"
done

# Cleanup old backups (keep 30 days)
find /backups -type d -mtime +30 -exec rm -rf {} \;
```

### Incremental Backups
```bash
# Compare with previous backup
current_cores=$(tg-show-kg-cores | sort)
previous_cores=$(cat last-backup-cores.txt 2>/dev/null | sort)

# Only backup changed cores
comm -13 <(echo "$previous_cores") <(echo "$current_cores") | while read core; do
    tg-get-kg-core --id "$core" -o "incremental/$core.msgpack"
done

echo "$current_cores" > last-backup-cores.txt
```

## Best Practices

1. **Regular Backups**: Schedule automated backups of important knowledge cores
2. **Organized Storage**: Use dated directories and consistent naming
3. **Verification**: Test backup files periodically by importing them
4. **Compression**: Compress large backup files to save storage
5. **Access Control**: Secure backup files with appropriate permissions
6. **Documentation**: Document what each knowledge core contains
7. **Retention Policy**: Implement backup retention policies

## Troubleshooting

### Large File Exports
```bash
# For very large knowledge cores
# Monitor progress and disk space
df -h .  # Check available space
tg-get-kg-core --id "huge-core" -o huge-core.msgpack &
watch -n 5 'ls -lh huge-core.msgpack'  # Monitor file growth
```

### Network Timeouts
```bash
# If export times out, try smaller cores or check network
# Split large cores if possible, or increase timeout settings
```

### Corrupted Exports
```bash
# Verify file integrity
file my-core.msgpack  # Should show "data"
python -c "import msgpack; msgpack.unpack(open('my-core.msgpack', 'rb'))"
```