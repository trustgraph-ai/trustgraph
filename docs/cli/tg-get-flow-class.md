# tg-get-flow-class

Retrieves and displays a flow class definition in JSON format.

## Synopsis

```bash
tg-get-flow-class -n CLASS_NAME [options]
```

## Description

The `tg-get-flow-class` command retrieves a stored flow class definition from TrustGraph and displays it in formatted JSON. This is useful for examining flow class configurations, creating backups, or preparing to modify existing flow classes.

The output can be saved to files for version control, documentation, or as input for creating new flow classes with `tg-put-flow-class`.

## Options

### Required Arguments

- `-n, --class-name CLASS_NAME`: Name of the flow class to retrieve

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Display Flow Class Definition
```bash
tg-get-flow-class -n "document-processing"
```

### Save Flow Class to File
```bash
tg-get-flow-class -n "production-flow" > production-flow-backup.json
```

### Compare Flow Classes
```bash
# Get multiple flow classes for comparison
tg-get-flow-class -n "dev-flow" > dev-flow.json
tg-get-flow-class -n "prod-flow" > prod-flow.json
diff dev-flow.json prod-flow.json
```

### Using Custom API URL
```bash
tg-get-flow-class -n "remote-flow" -u http://production:8088/
```

## Output Format

The command outputs the flow class definition in formatted JSON:

```json
{
    "description": "Document processing and analysis flow",
    "interfaces": {
        "agent": {
            "request": "non-persistent://tg/request/agent:doc-proc",
            "response": "non-persistent://tg/response/agent:doc-proc"
        },
        "document-rag": {
            "request": "non-persistent://tg/request/document-rag:doc-proc",
            "response": "non-persistent://tg/response/document-rag:doc-proc"
        },
        "text-load": "persistent://tg/flow/text-document-load:doc-proc",
        "document-load": "persistent://tg/flow/document-load:doc-proc",
        "triples-store": "persistent://tg/flow/triples-store:doc-proc"
    },
    "tags": ["production", "document-processing"]
}
```

### Key Components

#### Description
Human-readable description of the flow class purpose and capabilities.

#### Interfaces
Service definitions showing:
- **Request/Response Services**: Services with both request and response queues
- **Fire-and-Forget Services**: Services with only input queues

#### Tags (Optional)
Categorization tags for organizing flow classes.

## Prerequisites

### Flow Class Must Exist
Verify the flow class exists before retrieval:

```bash
# Check available flow classes
tg-show-flow-classes

# Look for specific class
tg-show-flow-classes | grep "target-class"
```

## Error Handling

### Flow Class Not Found
```bash
Exception: Flow class 'invalid-class' not found
```
**Solution**: Check available classes with `tg-show-flow-classes` and verify the class name.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Access denied to flow class
```
**Solution**: Verify user permissions for accessing flow class definitions.

## Use Cases

### Configuration Backup
```bash
# Backup all flow classes
mkdir -p flow-class-backups/$(date +%Y%m%d)
tg-show-flow-classes | awk '{print $1}' | while read class; do
    if [ "$class" != "flow" ]; then  # Skip header
        tg-get-flow-class -n "$class" > "flow-class-backups/$(date +%Y%m%d)/$class.json"
    fi
done
```

### Flow Class Migration
```bash
# Export from source environment
tg-get-flow-class -n "production-flow" -u http://source:8088/ > prod-flow.json

# Import to target environment
tg-put-flow-class -n "production-flow" -c "$(cat prod-flow.json)" -u http://target:8088/
```

### Template Creation
```bash
# Get existing flow class as template
tg-get-flow-class -n "base-flow" > template.json

# Modify template and create new class
sed 's/base-flow/new-flow/g' template.json > new-flow.json
tg-put-flow-class -n "custom-flow" -c "$(cat new-flow.json)"
```

### Configuration Analysis
```bash
# Analyze flow class configurations
tg-get-flow-class -n "complex-flow" | jq '.interfaces | keys'
tg-get-flow-class -n "complex-flow" | jq '.interfaces | length'
```

### Version Control Integration
```bash
# Store flow classes in git
mkdir -p flow-classes
tg-get-flow-class -n "main-flow" > flow-classes/main-flow.json
git add flow-classes/main-flow.json
git commit -m "Update main-flow configuration"
```

## JSON Processing

### Extract Specific Information
```bash
# Get only interface names
tg-get-flow-class -n "my-flow" | jq -r '.interfaces | keys[]'

# Get only description
tg-get-flow-class -n "my-flow" | jq -r '.description'

# Get request queues
tg-get-flow-class -n "my-flow" | jq -r '.interfaces | to_entries[] | select(.value.request) | .value.request'
```

### Validate Configuration
```bash
# Validate JSON structure
tg-get-flow-class -n "my-flow" | jq . > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Check required fields
config=$(tg-get-flow-class -n "my-flow")
echo "$config" | jq -e '.description' > /dev/null || echo "Missing description"
echo "$config" | jq -e '.interfaces' > /dev/null || echo "Missing interfaces"
```

## Integration with Other Commands

### Flow Class Lifecycle
```bash
# 1. Examine existing flow class
tg-get-flow-class -n "old-flow"

# 2. Save backup
tg-get-flow-class -n "old-flow" > old-flow-backup.json

# 3. Modify configuration
cp old-flow-backup.json new-flow.json
# Edit new-flow.json as needed

# 4. Upload new version
tg-put-flow-class -n "updated-flow" -c "$(cat new-flow.json)"

# 5. Test new flow class
tg-start-flow -n "updated-flow" -i "test-instance" -d "Testing updated flow"
```

### Bulk Operations
```bash
# Process multiple flow classes
flow_classes=("flow1" "flow2" "flow3")
for class in "${flow_classes[@]}"; do
    echo "Processing $class..."
    tg-get-flow-class -n "$class" > "backup-$class.json"
    
    # Modify configuration
    sed 's/old-pattern/new-pattern/g' "backup-$class.json" > "updated-$class.json"
    
    # Upload updated version
    tg-put-flow-class -n "$class" -c "$(cat updated-$class.json)"
done
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-put-flow-class`](tg-put-flow-class.md) - Upload/update flow class definitions
- [`tg-show-flow-classes`](tg-show-flow-classes.md) - List available flow classes
- [`tg-delete-flow-class`](tg-delete-flow-class.md) - Remove flow class definitions
- [`tg-start-flow`](tg-start-flow.md) - Create flow instances from classes

## API Integration

This command uses the [Flow API](../apis/api-flow.md) with the `get-class` operation to retrieve flow class definitions.

## Advanced Usage

### Configuration Diff
```bash
# Compare flow class versions
tg-get-flow-class -n "flow-v1" > v1.json
tg-get-flow-class -n "flow-v2" > v2.json
diff -u v1.json v2.json
```

### Extract Queue Information
```bash
# Get all queue names from flow class
tg-get-flow-class -n "my-flow" | jq -r '
  .interfaces | 
  to_entries[] | 
  if .value | type == "object" then
    .value.request, .value.response
  else
    .value
  end
' | sort | uniq
```

### Configuration Validation Script
```bash
#!/bin/bash
# validate-flow-class.sh
flow_class="$1"

if [ -z "$flow_class" ]; then
    echo "Usage: $0 <flow-class-name>"
    exit 1
fi

echo "Validating flow class: $flow_class"

# Get configuration
config=$(tg-get-flow-class -n "$flow_class" 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "ERROR: Flow class not found"
    exit 1
fi

# Validate JSON
echo "$config" | jq . > /dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Invalid JSON structure"
    exit 1
fi

# Check required fields
desc=$(echo "$config" | jq -r '.description // empty')
if [ -z "$desc" ]; then
    echo "WARNING: Missing description"
fi

interfaces=$(echo "$config" | jq -r '.interfaces // empty')
if [ -z "$interfaces" ] || [ "$interfaces" = "null" ]; then
    echo "ERROR: Missing interfaces"
    exit 1
fi

echo "Flow class validation passed"
```

## Best Practices

1. **Regular Backups**: Save flow class definitions before modifications
2. **Version Control**: Store configurations in version control systems
3. **Documentation**: Include meaningful descriptions in flow classes
4. **Validation**: Validate JSON structure before using configurations
5. **Template Management**: Use existing classes as templates for new ones
6. **Change Tracking**: Document changes when updating flow classes

## Troubleshooting

### Empty Output
```bash
# If command returns empty output
tg-get-flow-class -n "my-flow"
# Check if flow class exists
tg-show-flow-classes | grep "my-flow"
```

### Invalid JSON Output
```bash
# If output appears corrupted
tg-get-flow-class -n "my-flow" | jq .
# Should show parsing error if JSON is invalid
```

### Permission Issues
```bash
# If access denied errors occur
# Verify authentication and user permissions
# Contact system administrator if needed
```