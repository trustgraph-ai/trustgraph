# tg-show-flow-blueprints

Lists all defined flow blueprintes in TrustGraph with their descriptions and tags.

## Synopsis

```bash
tg-show-flow-blueprints [options]
```

## Description

The `tg-show-flow-blueprints` command displays a formatted table of all flow blueprint definitions currently stored in TrustGraph. Each flow blueprint is shown with its name, description, and associated tags.

Flow blueprintes are templates that define the structure and services available for creating flow instances. This command helps you understand what flow blueprintes are available for use.

## Options

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### List All Flow Blueprintes
```bash
tg-show-flow-blueprints
```

Output:
```
+-----------------+----------------------------------+----------------------+
| flow blueprint      | description                      | tags                 |
+-----------------+----------------------------------+----------------------+
| document-proc   | Document processing pipeline     | production, nlp      |
| data-analysis   | Data analysis and visualization  | analytics, dev       |
| web-scraper     | Web content extraction flow     | scraping, batch      |
| chat-assistant  | Conversational AI assistant     | ai, interactive      |
+-----------------+----------------------------------+----------------------+
```

### Using Custom API URL
```bash
tg-show-flow-blueprints -u http://production:8088/
```

### Filter Flow Blueprintes
```bash
# Show only production-tagged flow blueprintes
tg-show-flow-blueprints | grep "production"

# Count total flow blueprintes
tg-show-flow-blueprints | grep -c "^|"

# Show flow blueprintes with specific patterns
tg-show-flow-blueprints | grep -E "(document|text|nlp)"
```

## Output Format

The command displays results in a formatted table with columns:

- **flow blueprint**: The unique name/identifier of the flow blueprint
- **description**: Human-readable description of the flow blueprint purpose
- **tags**: Comma-separated list of categorization tags

### Empty Results
If no flow blueprintes exist:
```
No flows.
```

## Use Cases

### Flow Blueprint Discovery
```bash
# Find available flow blueprintes for document processing
tg-show-flow-blueprints | grep -i document

# List all AI-related flow blueprintes
tg-show-flow-blueprints | grep -i "ai\|nlp\|chat\|assistant"

# Find development vs production flow blueprintes
tg-show-flow-blueprints | grep -E "(dev|test|staging)"
tg-show-flow-blueprints | grep "production"
```

### Flow Blueprint Management
```bash
# Get list of flow blueprint names for scripting
tg-show-flow-blueprints | awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); print $2}' | grep -v "^$"

# Check if specific flow blueprint exists
if tg-show-flow-blueprints | grep -q "target-flow"; then
    echo "Flow blueprint 'target-flow' exists"
else
    echo "Flow blueprint 'target-flow' not found"
fi
```

### Environment Comparison
```bash
# Compare flow blueprintes between environments
echo "Development environment:"
tg-show-flow-blueprints -u http://dev:8088/

echo "Production environment:"
tg-show-flow-blueprints -u http://prod:8088/
```

### Reporting and Documentation
```bash
# Generate flow blueprint inventory report
echo "Flow Blueprint Inventory - $(date)" > flow-inventory.txt
echo "=====================================" >> flow-inventory.txt
tg-show-flow-blueprints >> flow-inventory.txt

# Create CSV export
echo "flow_class,description,tags" > flow-classes.csv
tg-show-flow-blueprints | awk 'NR>3 && /^\|/ {
    gsub(/^\| */, "", $0); gsub(/ *\|$/, "", $0); 
    gsub(/ *\| */, ",", $0); print $0
}' >> flow-classes.csv
```

## Error Handling

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Access denied to list flow blueprintes
```
**Solution**: Verify user permissions for reading flow blueprint definitions.

### Network Timeouts
```bash
Exception: Request timeout
```
**Solution**: Check network connectivity and API server status.

## Integration with Other Commands

### Flow Blueprint Lifecycle
```bash
# 1. List available flow blueprintes
tg-show-flow-blueprints

# 2. Get details of specific flow blueprint
tg-get-flow-blueprint -n "interesting-flow"

# 3. Start flow instance from class
tg-start-flow -n "interesting-flow" -i "my-instance"

# 4. Monitor flow instance
tg-show-flows | grep "my-instance"
```

### Bulk Operations
```bash
# Process all flow blueprintes
tg-show-flow-blueprints | awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); if($2) print $2}' | \
while read class_name; do
    if [ -n "$class_name" ]; then
        echo "Processing flow blueprint: $class_name"
        tg-get-flow-blueprint -n "$class_name" > "backup-$class_name.json"
    fi
done
```

### Automated Validation
```bash
# Check flow blueprint health
echo "Validating flow blueprintes..."
tg-show-flow-blueprints | awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); if($2) print $2}' | \
while read class_name; do
    if [ -n "$class_name" ]; then
        echo -n "Checking $class_name... "
        if tg-get-flow-blueprint -n "$class_name" > /dev/null 2>&1; then
            echo "OK"
        else
            echo "ERROR"
        fi
    fi
done
```

## Advanced Usage

### Flow Blueprint Analysis
```bash
# Analyze flow blueprint distribution by tags
tg-show-flow-blueprints | awk 'NR>3 && /^\|/ {
    # Extract tags column
    split($0, parts, "|"); 
    tags = parts[4]; 
    gsub(/^ *| *$/, "", tags);
    if (tags) {
        split(tags, tag_array, ",");
        for (i in tag_array) {
            gsub(/^ *| *$/, "", tag_array[i]);
            if (tag_array[i]) print tag_array[i];
        }
    }
}' | sort | uniq -c | sort -nr
```

### Environment Synchronization
```bash
# Sync flow blueprintes between environments
echo "Synchronizing flow blueprintes from dev to staging..."

# Get list from development
dev_classes=$(tg-show-flow-blueprints -u http://dev:8088/ | \
  awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); if($2) print $2}')

# Check each class in staging
for class in $dev_classes; do
    if tg-show-flow-blueprints -u http://staging:8088/ | grep -q "$class"; then
        echo "$class: Already exists in staging"
    else
        echo "$class: Missing in staging - needs sync"
        # Get from dev and put to staging
        tg-get-flow-blueprint -n "$class" -u http://dev:8088/ > temp-class.json
        tg-put-flow-blueprint -n "$class" -c "$(cat temp-class.json)" -u http://staging:8088/
        rm temp-class.json
    fi
done
```

### Monitoring Script
```bash
#!/bin/bash
# monitor-flow-classes.sh
api_url="${1:-http://localhost:8088/}"

echo "Flow Blueprint Monitoring Report - $(date)"
echo "API URL: $api_url"
echo "----------------------------------------"

# Total count
total=$(tg-show-flow-blueprints -u "$api_url" | grep -c "^|" 2>/dev/null || echo "0")
echo "Total flow blueprintes: $((total - 3))"  # Subtract header rows

# Tag analysis
echo -e "\nTag distribution:"
tg-show-flow-blueprints -u "$api_url" | awk 'NR>3 && /^\|/ {
    split($0, parts, "|"); 
    tags = parts[4]; 
    gsub(/^ *| *$/, "", tags);
    if (tags) {
        split(tags, tag_array, ",");
        for (i in tag_array) {
            gsub(/^ *| *$/, "", tag_array[i]);
            if (tag_array[i]) print tag_array[i];
        }
    }
}' | sort | uniq -c | sort -nr

# Health check
echo -e "\nHealth check:"
healthy=0
unhealthy=0
tg-show-flow-blueprints -u "$api_url" | awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); if($2) print $2}' | \
while read class_name; do
    if [ -n "$class_name" ]; then
        if tg-get-flow-blueprint -n "$class_name" -u "$api_url" > /dev/null 2>&1; then
            healthy=$((healthy + 1))
        else
            unhealthy=$((unhealthy + 1))
            echo "  ERROR: $class_name"
        fi
    fi
done

echo "Healthy: $healthy, Unhealthy: $unhealthy"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-get-flow-blueprint`](tg-get-flow-blueprint.md) - Retrieve specific flow blueprint definitions
- [`tg-put-flow-blueprint`](tg-put-flow-blueprint.md) - Create/update flow blueprint definitions
- [`tg-delete-flow-blueprint`](tg-delete-flow-blueprint.md) - Delete flow blueprint definitions
- [`tg-start-flow`](tg-start-flow.md) - Create flow instances from classes
- [`tg-show-flows`](tg-show-flows.md) - List active flow instances

## API Integration

This command uses the [Flow API](../apis/api-flow.md) with the `list-classes` operation to retrieve flow blueprint listings.

## Best Practices

1. **Regular Inventory**: Periodically review available flow blueprintes
2. **Documentation**: Ensure flow blueprintes have meaningful descriptions
3. **Tagging**: Use consistent tagging for better organization
4. **Cleanup**: Remove unused or deprecated flow blueprintes
5. **Monitoring**: Include flow blueprint health checks in monitoring
6. **Environment Parity**: Keep flow blueprintes synchronized across environments

## Troubleshooting

### No Output
```bash
# If command returns no output, check API connectivity
tg-show-flow-blueprints -u http://localhost:8088/
# Verify TrustGraph is running and accessible
```

### Formatting Issues
```bash
# If table formatting is broken, check terminal width
export COLUMNS=120
tg-show-flow-blueprints
```

### Missing Flow Blueprintes
```bash
# If expected flow blueprintes are missing, verify:
# 1. Correct API URL
# 2. Database connectivity
# 3. Flow blueprint definitions are properly stored
```