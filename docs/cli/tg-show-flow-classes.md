# tg-show-flow-classes

Lists all defined flow classes in TrustGraph with their descriptions and tags.

## Synopsis

```bash
tg-show-flow-classes [options]
```

## Description

The `tg-show-flow-classes` command displays a formatted table of all flow class definitions currently stored in TrustGraph. Each flow class is shown with its name, description, and associated tags.

Flow classes are templates that define the structure and services available for creating flow instances. This command helps you understand what flow classes are available for use.

## Options

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### List All Flow Classes
```bash
tg-show-flow-classes
```

Output:
```
+-----------------+----------------------------------+----------------------+
| flow class      | description                      | tags                 |
+-----------------+----------------------------------+----------------------+
| document-proc   | Document processing pipeline     | production, nlp      |
| data-analysis   | Data analysis and visualization  | analytics, dev       |
| web-scraper     | Web content extraction flow     | scraping, batch      |
| chat-assistant  | Conversational AI assistant     | ai, interactive      |
+-----------------+----------------------------------+----------------------+
```

### Using Custom API URL
```bash
tg-show-flow-classes -u http://production:8088/
```

### Filter Flow Classes
```bash
# Show only production-tagged flow classes
tg-show-flow-classes | grep "production"

# Count total flow classes
tg-show-flow-classes | grep -c "^|"

# Show flow classes with specific patterns
tg-show-flow-classes | grep -E "(document|text|nlp)"
```

## Output Format

The command displays results in a formatted table with columns:

- **flow class**: The unique name/identifier of the flow class
- **description**: Human-readable description of the flow class purpose
- **tags**: Comma-separated list of categorization tags

### Empty Results
If no flow classes exist:
```
No flows.
```

## Use Cases

### Flow Class Discovery
```bash
# Find available flow classes for document processing
tg-show-flow-classes | grep -i document

# List all AI-related flow classes
tg-show-flow-classes | grep -i "ai\|nlp\|chat\|assistant"

# Find development vs production flow classes
tg-show-flow-classes | grep -E "(dev|test|staging)"
tg-show-flow-classes | grep "production"
```

### Flow Class Management
```bash
# Get list of flow class names for scripting
tg-show-flow-classes | awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); print $2}' | grep -v "^$"

# Check if specific flow class exists
if tg-show-flow-classes | grep -q "target-flow"; then
    echo "Flow class 'target-flow' exists"
else
    echo "Flow class 'target-flow' not found"
fi
```

### Environment Comparison
```bash
# Compare flow classes between environments
echo "Development environment:"
tg-show-flow-classes -u http://dev:8088/

echo "Production environment:"
tg-show-flow-classes -u http://prod:8088/
```

### Reporting and Documentation
```bash
# Generate flow class inventory report
echo "Flow Class Inventory - $(date)" > flow-inventory.txt
echo "=====================================" >> flow-inventory.txt
tg-show-flow-classes >> flow-inventory.txt

# Create CSV export
echo "flow_class,description,tags" > flow-classes.csv
tg-show-flow-classes | awk 'NR>3 && /^\|/ {
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
Exception: Access denied to list flow classes
```
**Solution**: Verify user permissions for reading flow class definitions.

### Network Timeouts
```bash
Exception: Request timeout
```
**Solution**: Check network connectivity and API server status.

## Integration with Other Commands

### Flow Class Lifecycle
```bash
# 1. List available flow classes
tg-show-flow-classes

# 2. Get details of specific flow class
tg-get-flow-class -n "interesting-flow"

# 3. Start flow instance from class
tg-start-flow -n "interesting-flow" -i "my-instance"

# 4. Monitor flow instance
tg-show-flows | grep "my-instance"
```

### Bulk Operations
```bash
# Process all flow classes
tg-show-flow-classes | awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); if($2) print $2}' | \
while read class_name; do
    if [ -n "$class_name" ]; then
        echo "Processing flow class: $class_name"
        tg-get-flow-class -n "$class_name" > "backup-$class_name.json"
    fi
done
```

### Automated Validation
```bash
# Check flow class health
echo "Validating flow classes..."
tg-show-flow-classes | awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); if($2) print $2}' | \
while read class_name; do
    if [ -n "$class_name" ]; then
        echo -n "Checking $class_name... "
        if tg-get-flow-class -n "$class_name" > /dev/null 2>&1; then
            echo "OK"
        else
            echo "ERROR"
        fi
    fi
done
```

## Advanced Usage

### Flow Class Analysis
```bash
# Analyze flow class distribution by tags
tg-show-flow-classes | awk 'NR>3 && /^\|/ {
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
# Sync flow classes between environments
echo "Synchronizing flow classes from dev to staging..."

# Get list from development
dev_classes=$(tg-show-flow-classes -u http://dev:8088/ | \
  awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); if($2) print $2}')

# Check each class in staging
for class in $dev_classes; do
    if tg-show-flow-classes -u http://staging:8088/ | grep -q "$class"; then
        echo "$class: Already exists in staging"
    else
        echo "$class: Missing in staging - needs sync"
        # Get from dev and put to staging
        tg-get-flow-class -n "$class" -u http://dev:8088/ > temp-class.json
        tg-put-flow-class -n "$class" -c "$(cat temp-class.json)" -u http://staging:8088/
        rm temp-class.json
    fi
done
```

### Monitoring Script
```bash
#!/bin/bash
# monitor-flow-classes.sh
api_url="${1:-http://localhost:8088/}"

echo "Flow Class Monitoring Report - $(date)"
echo "API URL: $api_url"
echo "----------------------------------------"

# Total count
total=$(tg-show-flow-classes -u "$api_url" | grep -c "^|" 2>/dev/null || echo "0")
echo "Total flow classes: $((total - 3))"  # Subtract header rows

# Tag analysis
echo -e "\nTag distribution:"
tg-show-flow-classes -u "$api_url" | awk 'NR>3 && /^\|/ {
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
tg-show-flow-classes -u "$api_url" | awk 'NR>3 && /^\|/ {gsub(/[| ]/, "", $2); if($2) print $2}' | \
while read class_name; do
    if [ -n "$class_name" ]; then
        if tg-get-flow-class -n "$class_name" -u "$api_url" > /dev/null 2>&1; then
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

- [`tg-get-flow-class`](tg-get-flow-class.md) - Retrieve specific flow class definitions
- [`tg-put-flow-class`](tg-put-flow-class.md) - Create/update flow class definitions
- [`tg-delete-flow-class`](tg-delete-flow-class.md) - Delete flow class definitions
- [`tg-start-flow`](tg-start-flow.md) - Create flow instances from classes
- [`tg-show-flows`](tg-show-flows.md) - List active flow instances

## API Integration

This command uses the [Flow API](../apis/api-flow.md) with the `list-classes` operation to retrieve flow class listings.

## Best Practices

1. **Regular Inventory**: Periodically review available flow classes
2. **Documentation**: Ensure flow classes have meaningful descriptions
3. **Tagging**: Use consistent tagging for better organization
4. **Cleanup**: Remove unused or deprecated flow classes
5. **Monitoring**: Include flow class health checks in monitoring
6. **Environment Parity**: Keep flow classes synchronized across environments

## Troubleshooting

### No Output
```bash
# If command returns no output, check API connectivity
tg-show-flow-classes -u http://localhost:8088/
# Verify TrustGraph is running and accessible
```

### Formatting Issues
```bash
# If table formatting is broken, check terminal width
export COLUMNS=120
tg-show-flow-classes
```

### Missing Flow Classes
```bash
# If expected flow classes are missing, verify:
# 1. Correct API URL
# 2. Database connectivity
# 3. Flow class definitions are properly stored
```