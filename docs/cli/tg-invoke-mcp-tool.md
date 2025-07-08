# tg-invoke-mcp-tool

Invokes MCP (Model Control Protocol) tools through the TrustGraph API with parameter support.

## Synopsis

```bash
tg-invoke-mcp-tool [options] -n tool-name [-P parameters]
```

## Description

The `tg-invoke-mcp-tool` command invokes MCP (Model Control Protocol) tools through the TrustGraph API. MCP tools are external services that provide standardized interfaces for AI model interactions within the TrustGraph ecosystem.

MCP tools offer extensible functionality with consistent APIs, stateful interactions, and built-in security mechanisms. They can be used for various purposes including file operations, calculations, web requests, database queries, and custom integrations.

## Options

### Required Arguments

- `-n, --name TOOL_NAME`: MCP tool name to invoke

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-f, --flow-id ID`: Flow instance ID to use (default: `default`)
- `-P, --parameters JSON`: Tool parameters as JSON-encoded dictionary

## Examples

### Basic Tool Invocation
```bash
tg-invoke-mcp-tool -n weather
```

### Tool with Parameters
```bash
tg-invoke-mcp-tool -n calculator -P '{"expression": "2 + 2"}'
```

### File Operations
```bash
tg-invoke-mcp-tool -n file-reader -P '{"path": "/path/to/file.txt"}'
```

### Web Request Tool
```bash
tg-invoke-mcp-tool -n http-client -P '{"url": "https://api.example.com/data", "method": "GET"}'
```

### Database Query
```bash
tg-invoke-mcp-tool -n database -P '{"query": "SELECT * FROM users LIMIT 10", "database": "main"}'
```

### Custom Flow and API URL
```bash
tg-invoke-mcp-tool -u http://custom-api:8088/ -f my-flow -n weather -P '{"location": "London"}'
```

## Parameter Format

### Simple Parameters
```bash
tg-invoke-mcp-tool -n calculator -P '{"operation": "add", "a": 10, "b": 5}'
```

### Complex Parameters
```bash
tg-invoke-mcp-tool -n data-processor -P '{
  "input_data": [1, 2, 3, 4, 5],
  "operations": ["sum", "average", "max"],
  "output_format": "json"
}'
```

### File Input Parameters
```bash
tg-invoke-mcp-tool -n text-analyzer -P "{\"text\": \"$(cat document.txt)\", \"analysis_type\": \"sentiment\"}"
```

### Multiple Parameters
```bash
tg-invoke-mcp-tool -n report-generator -P '{
  "template": "monthly-report",
  "data_source": "sales_database",
  "period": "2024-01",
  "format": "pdf",
  "recipients": ["admin@example.com"]
}'
```

## Common MCP Tools

### File Operations
```bash
# Read file content
tg-invoke-mcp-tool -n file-reader -P '{"path": "/path/to/file.txt"}'

# Write file content
tg-invoke-mcp-tool -n file-writer -P '{"path": "/path/to/output.txt", "content": "Hello World"}'

# List directory contents
tg-invoke-mcp-tool -n directory-lister -P '{"path": "/home/user", "recursive": false}'
```

### Data Processing
```bash
# JSON processing
tg-invoke-mcp-tool -n json-processor -P '{"data": "{\"key\": \"value\"}", "operation": "validate"}'

# CSV analysis
tg-invoke-mcp-tool -n csv-analyzer -P '{"file": "data.csv", "columns": ["name", "age"], "operation": "statistics"}'

# Text transformation
tg-invoke-mcp-tool -n text-transformer -P '{"text": "Hello World", "operation": "uppercase"}'
```

### Web and API
```bash
# HTTP requests
tg-invoke-mcp-tool -n http-client -P '{"url": "https://api.github.com/users/octocat", "method": "GET"}'

# Web scraping
tg-invoke-mcp-tool -n web-scraper -P '{"url": "https://example.com", "selector": "h1"}'

# API testing
tg-invoke-mcp-tool -n api-tester -P '{"endpoint": "/api/v1/users", "method": "POST", "payload": {"name": "John"}}'
```

### Database Operations
```bash
# Query execution
tg-invoke-mcp-tool -n database -P '{"query": "SELECT COUNT(*) FROM users", "database": "production"}'

# Schema inspection
tg-invoke-mcp-tool -n db-inspector -P '{"database": "main", "operation": "list_tables"}'

# Data migration
tg-invoke-mcp-tool -n db-migrator -P '{"source": "old_db", "target": "new_db", "table": "users"}'
```

## Output Formats

### String Response
```bash
tg-invoke-mcp-tool -n calculator -P '{"expression": "10 + 5"}'
# Output: "15"
```

### JSON Response
```bash
tg-invoke-mcp-tool -n weather -P '{"location": "New York"}'
# Output:
# {
#     "location": "New York",
#     "temperature": 22,
#     "conditions": "sunny",
#     "humidity": 45
# }
```

### Complex Object Response
```bash
tg-invoke-mcp-tool -n data-analyzer -P '{"dataset": "sales.csv"}'
# Output:
# {
#     "summary": {
#         "total_records": 1000,
#         "columns": ["date", "product", "amount"],
#         "date_range": "2024-01-01 to 2024-12-31"
#     },
#     "statistics": {
#         "total_sales": 50000,
#         "average_transaction": 50.0,
#         "top_product": "Widget A"
#     }
# }
```

## Error Handling

### Tool Not Found
```bash
Exception: MCP tool 'nonexistent-tool' not found
```
**Solution**: Check available tools with `tg-show-mcp-tools`.

### Invalid Parameters
```bash
Exception: Invalid JSON in parameters: Expecting property name enclosed in double quotes
```
**Solution**: Verify JSON parameter format and escape special characters.

### Missing Required Parameters
```bash
Exception: Required parameter 'input_data' not provided
```
**Solution**: Check tool documentation for required parameters.

### Flow Not Found
```bash
Exception: Flow instance 'invalid-flow' not found
```
**Solution**: Verify flow ID exists with `tg-show-flows`.

### Tool Execution Error
```bash
Exception: Tool execution failed: Connection timeout
```
**Solution**: Check network connectivity and tool service availability.

## Advanced Usage

### Batch Processing
```bash
# Process multiple files
for file in *.txt; do
    echo "Processing $file..."
    tg-invoke-mcp-tool -n text-analyzer -P "{\"file\": \"$file\", \"analysis\": \"sentiment\"}"
done
```

### Error Handling in Scripts
```bash
#!/bin/bash
# robust-tool-invoke.sh
tool_name="$1"
parameters="$2"

if ! result=$(tg-invoke-mcp-tool -n "$tool_name" -P "$parameters" 2>&1); then
    echo "Error invoking tool: $result" >&2
    exit 1
fi

echo "Success: $result"
```

### Pipeline Processing
```bash
# Chain multiple tools
data=$(tg-invoke-mcp-tool -n data-loader -P '{"source": "database"}')
processed=$(tg-invoke-mcp-tool -n data-processor -P "{\"data\": \"$data\", \"operation\": \"clean\"}")
tg-invoke-mcp-tool -n report-generator -P "{\"data\": \"$processed\", \"format\": \"pdf\"}"
```

### Configuration-Driven Invocation
```bash
# Use configuration file
config_file="tool-config.json"
tool_name=$(jq -r '.tool' "$config_file")
parameters=$(jq -c '.parameters' "$config_file")

tg-invoke-mcp-tool -n "$tool_name" -P "$parameters"
```

### Interactive Tool Usage
```bash
#!/bin/bash
# interactive-mcp-tool.sh
echo "Available tools:"
tg-show-mcp-tools

read -p "Enter tool name: " tool_name
read -p "Enter parameters (JSON): " parameters

echo "Invoking tool..."
tg-invoke-mcp-tool -n "$tool_name" -P "$parameters"
```

### Parallel Tool Execution
```bash
# Execute multiple tools in parallel
tools=("weather" "calculator" "file-reader")
params=('{"location": "NYC"}' '{"expression": "2+2"}' '{"path": "file.txt"}')

for i in "${!tools[@]}"; do
    (
        echo "Executing ${tools[$i]}..."
        tg-invoke-mcp-tool -n "${tools[$i]}" -P "${params[$i]}" > "result-${tools[$i]}.json"
    ) &
done
wait
```

## Tool Management

### List Available Tools
```bash
# Show all registered MCP tools
tg-show-mcp-tools
```

### Register New Tools
```bash
# Register a new MCP tool
tg-set-mcp-tool weather-service "http://weather-api:8080/mcp" "Weather data provider"
```

### Remove Tools
```bash
# Remove an MCP tool
tg-delete-mcp-tool weather-service
```

## Use Cases

### Data Processing Workflows
```bash
# Extract, transform, and load data
raw_data=$(tg-invoke-mcp-tool -n data-extractor -P '{"source": "external_api"}')
clean_data=$(tg-invoke-mcp-tool -n data-cleaner -P "{\"data\": \"$raw_data\"}")
tg-invoke-mcp-tool -n data-loader -P "{\"data\": \"$clean_data\", \"target\": \"warehouse\"}"
```

### Automation Scripts
```bash
# Automated system monitoring
status=$(tg-invoke-mcp-tool -n system-monitor -P '{"checks": ["cpu", "memory", "disk"]}')
if echo "$status" | grep -q "warning"; then
    tg-invoke-mcp-tool -n alert-system -P "{\"message\": \"System warning detected\", \"severity\": \"medium\"}"
fi
```

### Integration Testing
```bash
# Test API endpoints
endpoints=("/api/users" "/api/orders" "/api/products")
for endpoint in "${endpoints[@]}"; do
    result=$(tg-invoke-mcp-tool -n api-tester -P "{\"endpoint\": \"$endpoint\", \"method\": \"GET\"}")
    echo "Testing $endpoint: $result"
done
```

### Content Generation
```bash
# Generate documentation
code_analysis=$(tg-invoke-mcp-tool -n code-analyzer -P '{"directory": "./src", "language": "python"}')
tg-invoke-mcp-tool -n doc-generator -P "{\"analysis\": \"$code_analysis\", \"format\": \"markdown\"}"
```

## Performance Optimization

### Caching Tool Results
```bash
# Cache expensive tool operations
cache_dir="mcp-cache"
mkdir -p "$cache_dir"

invoke_with_cache() {
    local tool="$1"
    local params="$2"
    local cache_key=$(echo "$tool-$params" | md5sum | cut -d' ' -f1)
    local cache_file="$cache_dir/$cache_key.json"
    
    if [ -f "$cache_file" ]; then
        echo "Cache hit for $tool"
        cat "$cache_file"
    else
        echo "Cache miss, invoking $tool..."
        tg-invoke-mcp-tool -n "$tool" -P "$params" | tee "$cache_file"
    fi
}
```

### Asynchronous Processing
```bash
# Non-blocking tool execution
async_invoke() {
    local tool="$1"
    local params="$2"
    local output_file="$3"
    
    tg-invoke-mcp-tool -n "$tool" -P "$params" > "$output_file" 2>&1 &
    echo $!  # Return process ID
}

# Execute multiple tools asynchronously
pid1=$(async_invoke "data-processor" '{"file": "data1.csv"}' "result1.json")
pid2=$(async_invoke "data-processor" '{"file": "data2.csv"}' "result2.json")

# Wait for completion
wait $pid1 $pid2
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-mcp-tools`](tg-show-mcp-tools.md) - List available MCP tools
- [`tg-set-mcp-tool`](tg-set-mcp-tool.md) - Register MCP tools
- [`tg-delete-mcp-tool`](tg-delete-mcp-tool.md) - Remove MCP tools
- [`tg-show-flows`](tg-show-flows.md) - List available flow instances
- [`tg-invoke-prompt`](tg-invoke-prompt.md) - Invoke prompt templates

## API Integration

This command uses the TrustGraph API flow interface to execute MCP tools within the context of specified flows. MCP tools are external services that implement the Model Control Protocol for standardized AI tool interactions.

## Best Practices

1. **Parameter Validation**: Always validate JSON parameters before execution
2. **Error Handling**: Implement robust error handling for production use
3. **Tool Discovery**: Use `tg-show-mcp-tools` to discover available tools
4. **Resource Management**: Consider performance implications of long-running tools
5. **Security**: Avoid passing sensitive data in parameters; use secure tool configurations
6. **Documentation**: Document custom tool parameters and expected responses
7. **Testing**: Test tool integrations thoroughly before production deployment

## Troubleshooting

### Tool Not Available
```bash
# Check tool registration
tg-show-mcp-tools | grep "tool-name"

# Verify tool service is running
curl -f http://tool-service:8080/health
```

### Parameter Issues
```bash
# Validate JSON format
echo '{"key": "value"}' | jq .

# Test with minimal parameters
tg-invoke-mcp-tool -n tool-name -P '{}'
```

### Flow Problems
```bash
# Check flow status
tg-show-flows | grep "flow-id"

# Verify flow supports MCP tools
tg-get-flow-class -n "flow-class" | jq '.interfaces.mcp_tool'
```

### Connection Issues
```bash
# Test API connectivity
curl -f http://localhost:8088/health

# Check environment variables
echo $TRUSTGRAPH_URL
```