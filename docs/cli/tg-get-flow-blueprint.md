# tg-get-flow-blueprint

Retrieves and displays a flow blueprint definition in JSON format.

## Synopsis

```bash
tg-get-flow-blueprint -n CLASS_NAME [options]
```

## Description

The `tg-get-flow-blueprint` command retrieves a stored flow blueprint definition from TrustGraph and displays it in formatted JSON. This is useful for examining flow blueprint configurations, creating backups, or preparing to modify existing flow blueprintes.

The output can be saved to files for version control, documentation, or as input for creating new flow blueprintes with `tg-put-flow-blueprint`.

## Options

### Required Arguments

- `-n, --blueprint-name CLASS_NAME`: Name of the flow blueprint to retrieve

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Display Flow Blueprint Definition
```bash
tg-get-flow-blueprint -n "document-processing"
```

### Save Flow Blueprint to File
```bash
tg-get-flow-blueprint -n "production-flow" > production-flow-backup.json
```

### Compare Flow Blueprintes
```bash
# Get multiple flow blueprintes for comparison
tg-get-flow-blueprint -n "dev-flow" > dev-flow.json
tg-get-flow-blueprint -n "prod-flow" > prod-flow.json
diff dev-flow.json prod-flow.json
```

### Using Custom API URL
```bash
tg-get-flow-blueprint -n "remote-flow" -u http://production:8088/
```

## Output Format

The command outputs the flow blueprint definition in formatted JSON:

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
Human-readable description of the flow blueprint purpose and capabilities.

#### Interfaces
Service definitions showing:
- **Request/Response Services**: Services with both request and response queues
- **Fire-and-Forget Services**: Services with only input queues

#### Tags (Optional)
Categorization tags for organizing flow blueprintes.

## Prerequisites

### Flow Blueprint Must Exist
Verify the flow blueprint exists before retrieval:

```bash
# Check available flow blueprintes
tg-show-flow-blueprints

# Look for specific class
tg-show-flow-blueprints | grep "target-class"
```

## Error Handling

### Flow Blueprint Not Found
```bash
Exception: Flow blueprint 'invalid-class' not found
```
**Solution**: Check available classes with `tg-show-flow-blueprints` and verify the class name.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Access denied to flow blueprint
```
**Solution**: Verify user permissions for accessing flow blueprint definitions.

## Use Cases

### Configuration Backup
```bash
# Backup all flow blueprintes
mkdir -p flow-class-backups/$(date +%Y%m%d)
tg-show-flow-blueprints | awk '{print $1}' | while read class; do
    if [ "$class" != "flow" ]; then  # Skip header
        tg-get-flow-blueprint -n "$class" > "flow-class-backups/$(date +%Y%m%d)/$class.json"
    fi
done
```

### Flow Blueprint Migration
```bash
# Export from source environment
tg-get-flow-blueprint -n "production-flow" -u http://source:8088/ > prod-flow.json

# Import to target environment
tg-put-flow-blueprint -n "production-flow" -c "$(cat prod-flow.json)" -u http://target:8088/
```

### Template Creation
```bash
# Get existing flow blueprint as template
tg-get-flow-blueprint -n "base-flow" > template.json

# Modify template and create new class
sed 's/base-flow/new-flow/g' template.json > new-flow.json
tg-put-flow-blueprint -n "custom-flow" -c "$(cat new-flow.json)"
```

### Configuration Analysis
```bash
# Analyze flow blueprint configurations
tg-get-flow-blueprint -n "complex-flow" | jq '.interfaces | keys'
tg-get-flow-blueprint -n "complex-flow" | jq '.interfaces | length'
```

### Version Control Integration
```bash
# Store flow blueprintes in git
mkdir -p flow-classes
tg-get-flow-blueprint -n "main-flow" > flow-classes/main-flow.json
git add flow-classes/main-flow.json
git commit -m "Update main-flow configuration"
```

## JSON Processing

### Extract Specific Information
```bash
# Get only interface names
tg-get-flow-blueprint -n "my-flow" | jq -r '.interfaces | keys[]'

# Get only description
tg-get-flow-blueprint -n "my-flow" | jq -r '.description'

# Get request queues
tg-get-flow-blueprint -n "my-flow" | jq -r '.interfaces | to_entries[] | select(.value.request) | .value.request'
```

### Validate Configuration
```bash
# Validate JSON structure
tg-get-flow-blueprint -n "my-flow" | jq . > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Check required fields
config=$(tg-get-flow-blueprint -n "my-flow")
echo "$config" | jq -e '.description' > /dev/null || echo "Missing description"
echo "$config" | jq -e '.interfaces' > /dev/null || echo "Missing interfaces"
```

## Integration with Other Commands

### Flow Blueprint Lifecycle
```bash
# 1. Examine existing flow blueprint
tg-get-flow-blueprint -n "old-flow"

# 2. Save backup
tg-get-flow-blueprint -n "old-flow" > old-flow-backup.json

# 3. Modify configuration
cp old-flow-backup.json new-flow.json
# Edit new-flow.json as needed

# 4. Upload new version
tg-put-flow-blueprint -n "updated-flow" -c "$(cat new-flow.json)"

# 5. Test new flow blueprint
tg-start-flow -n "updated-flow" -i "test-instance" -d "Testing updated flow"
```

### Bulk Operations
```bash
# Process multiple flow blueprintes
flow_classes=("flow1" "flow2" "flow3")
for class in "${flow_classes[@]}"; do
    echo "Processing $class..."
    tg-get-flow-blueprint -n "$class" > "backup-$class.json"
    
    # Modify configuration
    sed 's/old-pattern/new-pattern/g' "backup-$class.json" > "updated-$class.json"
    
    # Upload updated version
    tg-put-flow-blueprint -n "$class" -c "$(cat updated-$class.json)"
done
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-put-flow-blueprint`](tg-put-flow-blueprint.md) - Upload/update flow blueprint definitions
- [`tg-show-flow-blueprints`](tg-show-flow-blueprints.md) - List available flow blueprintes
- [`tg-delete-flow-blueprint`](tg-delete-flow-blueprint.md) - Remove flow blueprint definitions
- [`tg-start-flow`](tg-start-flow.md) - Create flow instances from classes

## API Integration

This command uses the [Flow API](../apis/api-flow.md) with the `get-class` operation to retrieve flow blueprint definitions.

## Advanced Usage

### Configuration Diff
```bash
# Compare flow blueprint versions
tg-get-flow-blueprint -n "flow-v1" > v1.json
tg-get-flow-blueprint -n "flow-v2" > v2.json
diff -u v1.json v2.json
```

### Extract Queue Information
```bash
# Get all queue names from flow blueprint
tg-get-flow-blueprint -n "my-flow" | jq -r '
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
    echo "Usage: $0 <flow-blueprint-name>"
    exit 1
fi

echo "Validating flow blueprint: $flow_class"

# Get configuration
config=$(tg-get-flow-blueprint -n "$flow_class" 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "ERROR: Flow blueprint not found"
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

echo "Flow blueprint validation passed"
```

## Best Practices

1. **Regular Backups**: Save flow blueprint definitions before modifications
2. **Version Control**: Store configurations in version control systems
3. **Documentation**: Include meaningful descriptions in flow blueprintes
4. **Validation**: Validate JSON structure before using configurations
5. **Template Management**: Use existing classes as templates for new ones
6. **Change Tracking**: Document changes when updating flow blueprintes

## Troubleshooting

### Empty Output
```bash
# If command returns empty output
tg-get-flow-blueprint -n "my-flow"
# Check if flow blueprint exists
tg-show-flow-blueprints | grep "my-flow"
```

### Invalid JSON Output
```bash
# If output appears corrupted
tg-get-flow-blueprint -n "my-flow" | jq .
# Should show parsing error if JSON is invalid
```

### Permission Issues
```bash
# If access denied errors occur
# Verify authentication and user permissions
# Contact system administrator if needed
```