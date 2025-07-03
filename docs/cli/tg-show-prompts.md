# tg-show-prompts

Displays all configured prompt templates and system prompts in TrustGraph.

## Synopsis

```bash
tg-show-prompts [options]
```

## Description

The `tg-show-prompts` command displays all prompt templates and the system prompt currently configured in TrustGraph. This includes template IDs, prompt text, response types, and JSON schemas for structured responses.

Use this command to review existing prompts, verify configurations, and understand available templates for use with `tg-invoke-prompt`.

## Options

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Display All Prompts
```bash
tg-show-prompts
```

### Using Custom API URL
```bash
tg-show-prompts -u http://production:8088/
```

## Output Format

The command displays prompts in formatted tables:

```
System prompt:
+---------+--------------------------------------------------+
| prompt  | You are a helpful AI assistant. Always provide  |
|         | accurate, concise responses. When uncertain,     |
|         | clearly state your limitations.                  |
+---------+--------------------------------------------------+

greeting:
+---------+--------------------------------------------------+
| prompt  | Hello {{name}}, welcome to {{place}}!           |
+---------+--------------------------------------------------+

question:
+----------+-------------------------------------------------+
| prompt   | Answer this question based on the context:     |
|          | {{question}}                                    |
|          |                                                 |
|          | Context: {{context}}                           |
+----------+-------------------------------------------------+

extract-info:
+----------+-------------------------------------------------+
| prompt   | Extract key information from: {{text}}         |
| response | json                                            |
| schema   | {"type": "object", "properties": {             |
|          | "name": {"type": "string"},                     |
|          | "age": {"type": "number"}}}                     |
+----------+-------------------------------------------------+
```

### Template Information

For each template, the output shows:
- **prompt**: The template text with variable placeholders
- **response**: Response format (`text` or `json`)
- **schema**: JSON schema for structured responses (when applicable)

## Use Cases

### Template Discovery
```bash
# Find all available templates
tg-show-prompts | grep "^[a-zA-Z]" | grep ":"

# Find templates with specific keywords
tg-show-prompts | grep -B5 -A5 "analyze"
```

### Template Verification
```bash
# Check if specific template exists
if tg-show-prompts | grep -q "my-template:"; then
  echo "Template exists"
else
  echo "Template not found"
fi
```

### Configuration Review
```bash
# Review current system prompt
tg-show-prompts | grep -A10 "System prompt:"

# Check JSON response templates
tg-show-prompts | grep -B2 -A5 "response.*json"
```

### Template Inventory
```bash
# Count total templates
template_count=$(tg-show-prompts | grep -c "^[a-zA-Z][^:]*:$")
echo "Total templates: $template_count"

# List template names only
tg-show-prompts | grep "^[a-zA-Z][^:]*:$" | sed 's/:$//'
```

## Advanced Usage

### Template Analysis
```bash
# Analyze template complexity
analyze_templates() {
  echo "Template Analysis"
  echo "================"
  
  tg-show-prompts > temp_prompts.txt
  
  # Count variables per template
  echo "Templates with variables:"
  grep -B1 -A5 "{{" temp_prompts.txt | \
    grep "^[a-zA-Z]" | \
    while read template; do
      var_count=$(grep -A5 "$template" temp_prompts.txt | grep -o "{{[^}]*}}" | wc -l)
      echo "  $template $var_count variables"
    done
  
  # Find JSON response templates
  echo -e "\nJSON Response Templates:"
  grep -B1 "response.*json" temp_prompts.txt | \
    grep "^[a-zA-Z]" | \
    sed 's/:$//'
  
  rm temp_prompts.txt
}

analyze_templates
```

### Template Documentation Generator
```bash
# Generate template documentation
generate_template_docs() {
  local output_file="template_documentation.md"
  
  echo "# TrustGraph Prompt Templates" > "$output_file"
  echo "Generated on $(date)" >> "$output_file"
  echo "" >> "$output_file"
  
  # Extract system prompt
  echo "## System Prompt" >> "$output_file"
  tg-show-prompts | \
    awk '/System prompt:/,/^\+.*\+$/' | \
    grep "| prompt" | \
    sed 's/| prompt  | //' | \
    sed 's/ *|$//' >> "$output_file"
  
  echo "" >> "$output_file"
  echo "## Templates" >> "$output_file"
  
  # Extract each template
  tg-show-prompts | \
    grep "^[a-zA-Z][^:]*:$" | \
    sed 's/:$//' | \
    while read template_id; do
      echo "" >> "$output_file"
      echo "### $template_id" >> "$output_file"
      
      # Get template details
      tg-show-prompts | \
        awk "/^$template_id:/,/^$/" | \
        while read line; do
          if [[ "$line" =~ ^\|\ prompt ]]; then
            echo "**Prompt:**" >> "$output_file"
            echo '```' >> "$output_file"
            echo "$line" | sed 's/| prompt[[:space:]]*| //' | sed 's/ *|$//' >> "$output_file"
            echo '```' >> "$output_file"
          elif [[ "$line" =~ ^\|\ response ]]; then
            response_type=$(echo "$line" | sed 's/| response[[:space:]]*| //' | sed 's/ *|$//')
            echo "**Response Type:** $response_type" >> "$output_file"
          elif [[ "$line" =~ ^\|\ schema ]]; then
            echo "**JSON Schema:**" >> "$output_file"
            echo '```json' >> "$output_file"
            echo "$line" | sed 's/| schema[[:space:]]*| //' | sed 's/ *|$//' >> "$output_file"
            echo '```' >> "$output_file"
          fi
        done
    done
  
  echo "Documentation generated: $output_file"
}

generate_template_docs
```

### Template Validation
```bash
# Validate template configurations
validate_templates() {
  echo "Template Validation Report"
  echo "========================="
  
  tg-show-prompts > temp_prompts.txt
  
  # Check for templates without variables
  echo "Templates without variables:"
  grep -B1 -A5 "^[a-zA-Z]" temp_prompts.txt | \
    grep -v "{{" | \
    grep "^[a-zA-Z][^:]*:$" | \
    sed 's/:$//' | \
    while read template; do
      if ! grep -A5 "$template:" temp_prompts.txt | grep -q "{{"; then
        echo "  - $template"
      fi
    done
  
  # Check JSON templates have schemas
  echo -e "\nJSON templates without schemas:"
  grep -B1 -A10 "response.*json" temp_prompts.txt | \
    grep -B10 -A10 "response.*json" | \
    while read -r line; do
      if [[ "$line" =~ ^([a-zA-Z][^:]*):$ ]]; then
        template="${BASH_REMATCH[1]}"
        if ! grep -A10 "$template:" temp_prompts.txt | grep -q "schema"; then
          echo "  - $template"
        fi
      fi
    done
  
  rm temp_prompts.txt
}

validate_templates
```

### Template Usage Examples
```bash
# Generate usage examples for templates
generate_usage_examples() {
  local template_id="$1"
  
  echo "Usage examples for template: $template_id"
  echo "========================================"
  
  # Extract template and find variables
  tg-show-prompts | \
    awk "/^$template_id:/,/^$/" | \
    grep "| prompt" | \
    sed 's/| prompt[[:space:]]*| //' | \
    sed 's/ *|$//' | \
    while read prompt_text; do
      echo "Template:"
      echo "$prompt_text"
      echo ""
      
      # Extract variables
      variables=$(echo "$prompt_text" | grep -o "{{[^}]*}}" | sed 's/[{}]//g' | sort | uniq)
      
      if [ -n "$variables" ]; then
        echo "Variables:"
        for var in $variables; do
          echo "  - $var"
        done
        echo ""
        
        echo "Example usage:"
        cmd="tg-invoke-prompt $template_id"
        for var in $variables; do
          case "$var" in
            *name*) cmd="$cmd $var=\"John Doe\"" ;;
            *text*|*content*) cmd="$cmd $var=\"Sample text content\"" ;;
            *question*) cmd="$cmd $var=\"What is this about?\"" ;;
            *context*) cmd="$cmd $var=\"Background information\"" ;;
            *) cmd="$cmd $var=\"value\"" ;;
          esac
        done
        echo "$cmd"
      else
        echo "No variables found."
        echo "Usage: tg-invoke-prompt $template_id"
      fi
    done
}

# Generate examples for specific template
generate_usage_examples "question"
```

### Environment Comparison
```bash
# Compare templates between environments
compare_environments() {
  local env1_url="$1"
  local env2_url="$2"
  
  echo "Comparing templates between environments"
  echo "======================================"
  
  # Get templates from both environments
  tg-show-prompts -u "$env1_url" | grep "^[a-zA-Z][^:]*:$" | sed 's/:$//' | sort > env1_templates.txt
  tg-show-prompts -u "$env2_url" | grep "^[a-zA-Z][^:]*:$" | sed 's/:$//' | sort > env2_templates.txt
  
  echo "Environment 1 ($env1_url): $(wc -l < env1_templates.txt) templates"
  echo "Environment 2 ($env2_url): $(wc -l < env2_templates.txt) templates"
  echo ""
  
  # Find differences
  echo "Templates only in Environment 1:"
  comm -23 env1_templates.txt env2_templates.txt | sed 's/^/  - /'
  
  echo -e "\nTemplates only in Environment 2:"
  comm -13 env1_templates.txt env2_templates.txt | sed 's/^/  - /'
  
  echo -e "\nCommon templates:"
  comm -12 env1_templates.txt env2_templates.txt | sed 's/^/  - /'
  
  rm env1_templates.txt env2_templates.txt
}

# Compare development and production
compare_environments "http://dev:8088/" "http://prod:8088/"
```

### Template Export/Import
```bash
# Export templates to JSON
export_templates() {
  local output_file="$1"
  
  echo "Exporting templates to: $output_file"
  
  echo "{" > "$output_file"
  echo "  \"export_date\": \"$(date -Iseconds)\"," >> "$output_file"
  echo "  \"system_prompt\": \"$(tg-show-prompts | awk '/System prompt:/,/^\+.*\+$/' | grep '| prompt' | sed 's/| prompt[[:space:]]*| //' | sed 's/ *|$//' | sed 's/"/\\"/g')\"," >> "$output_file"
  echo "  \"templates\": {" >> "$output_file"
  
  first=true
  tg-show-prompts | \
    grep "^[a-zA-Z][^:]*:$" | \
    sed 's/:$//' | \
    while read template_id; do
      if [ "$first" = "false" ]; then
        echo "," >> "$output_file"
      fi
      first=false
      
      echo -n "    \"$template_id\": {" >> "$output_file"
      
      # Extract template details
      tg-show-prompts | \
        awk "/^$template_id:/,/^$/" | \
        while read line; do
          if [[ "$line" =~ ^\|\ prompt ]]; then
            prompt=$(echo "$line" | sed 's/| prompt[[:space:]]*| //' | sed 's/ *|$//' | sed 's/"/\\"/g')
            echo -n "\"prompt\": \"$prompt\"" >> "$output_file"
          elif [[ "$line" =~ ^\|\ response ]]; then
            response=$(echo "$line" | sed 's/| response[[:space:]]*| //' | sed 's/ *|$//')
            echo -n ", \"response\": \"$response\"" >> "$output_file"
          elif [[ "$line" =~ ^\|\ schema ]]; then
            schema=$(echo "$line" | sed 's/| schema[[:space:]]*| //' | sed 's/ *|$//' | sed 's/"/\\"/g')
            echo -n ", \"schema\": \"$schema\"" >> "$output_file"
          fi
        done
      
      echo "}" >> "$output_file"
    done
  
  echo "  }" >> "$output_file"
  echo "}" >> "$output_file"
  
  echo "Export completed: $output_file"
}

# Export current templates
export_templates "templates_backup.json"
```

## Error Handling

### Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Check API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Access denied
```
**Solution**: Verify user permissions for configuration access.

### No Templates Found
```bash
# Empty output or no templates section
```
**Solution**: Check if any templates are configured with `tg-set-prompt`.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-set-prompt`](tg-set-prompt.md) - Create/update prompt templates
- [`tg-invoke-prompt`](tg-invoke-prompt.md) - Use prompt templates
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Document-based queries

## API Integration

This command uses the [Config API](../apis/api-config.md) to retrieve prompt templates and system prompts from TrustGraph's configuration system.

## Best Practices

1. **Regular Review**: Periodically review templates for relevance and accuracy
2. **Documentation**: Document template purposes and expected variables
3. **Version Control**: Track template changes over time
4. **Testing**: Verify templates work as expected after viewing
5. **Organization**: Use consistent naming conventions for templates
6. **Cleanup**: Remove unused or outdated templates
7. **Backup**: Export templates for backup and migration purposes

## Troubleshooting

### Formatting Issues
```bash
# If output is garbled or truncated
export COLUMNS=120
tg-show-prompts
```

### Missing Templates
```bash
# Check if templates are actually configured
tg-show-prompts | grep -c "^[a-zA-Z].*:$"

# Verify API connectivity
curl -s "$TRUSTGRAPH_URL/api/v1/config" > /dev/null
```

### Template Not Displaying
```bash
# Check template was set correctly
tg-set-prompt --id "test" --prompt "test template"
tg-show-prompts | grep "test:"
```