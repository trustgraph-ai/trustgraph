# tg-invoke-prompt

Invokes the LLM prompt service using predefined prompt templates with variable substitution.

## Synopsis

```bash
tg-invoke-prompt [options] template-id [variable=value ...]
```

## Description

The `tg-invoke-prompt` command invokes TrustGraph's LLM prompt service using predefined prompt templates. Templates contain placeholder variables in the format `{{variable}}` that are replaced with values provided on the command line.

This provides a structured way to interact with language models using consistent, reusable prompt templates for specific tasks like question answering, text extraction, analysis, and more.

## Options

### Required Arguments

- `template-id`: Prompt template identifier (e.g., `question`, `extract-definitions`, `summarize`)

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-f, --flow-id ID`: Flow instance ID to use (default: `default`)
- `variable=value`: Template variable assignments (can be specified multiple times)

## Examples

### Basic Question Answering
```bash
tg-invoke-prompt question text="What is artificial intelligence?" context="AI research field"
```

### Extract Definitions
```bash
tg-invoke-prompt extract-definitions \
  document="Machine learning is a subset of artificial intelligence..." \
  terms="machine learning,neural networks"
```

### Text Summarization
```bash
tg-invoke-prompt summarize \
  text="$(cat large-document.txt)" \
  max_length="200" \
  style="technical"
```

### Custom Flow and Variables
```bash
tg-invoke-prompt analysis \
  -f "research-flow" \
  data="$(cat research-data.json)" \
  focus="trends" \
  output_format="markdown"
```

## Variable Substitution

Templates use `{{variable}}` placeholders that are replaced with command-line values:

### Simple Variables
```bash
tg-invoke-prompt greeting name="Alice" time="morning"
# Template: "Good {{time}}, {{name}}!"
# Result: "Good morning, Alice!"
```

### Complex Variables
```bash
tg-invoke-prompt analyze \
  dataset="$(cat data.csv)" \
  columns="name,age,salary" \
  analysis_type="statistical_summary"
```

### Multi-line Variables
```bash
tg-invoke-prompt review \
  code="$(cat app.py)" \
  checklist="security,performance,maintainability" \
  severity="high"
```

## Common Template Types

### Question Answering
```bash
# Direct question
tg-invoke-prompt question \
  text="What is the capital of France?" \
  context="geography"

# Contextual question
tg-invoke-prompt question \
  text="How does this work?" \
  context="$(cat technical-manual.txt)"
```

### Text Processing
```bash
# Extract key information
tg-invoke-prompt extract-key-points \
  document="$(cat meeting-notes.txt)" \
  format="bullet_points"

# Text classification
tg-invoke-prompt classify \
  text="Customer is very unhappy with service" \
  categories="positive,negative,neutral"
```

### Code Analysis
```bash
# Code review
tg-invoke-prompt code-review \
  code="$(cat script.py)" \
  language="python" \
  focus="security,performance"

# Bug analysis
tg-invoke-prompt debug \
  code="$(cat buggy-code.js)" \
  error="TypeError: Cannot read property 'length' of undefined"
```

### Data Analysis
```bash
# Data insights
tg-invoke-prompt data-analysis \
  data="$(cat sales-data.json)" \
  metrics="revenue,growth,trends" \
  period="quarterly"
```

## Template Management

### List Available Templates
```bash
# Show available prompt templates
tg-show-prompts
```

### Create Custom Templates
```bash
# Define a new template
tg-set-prompt analysis-template \
  "Analyze the following {{data_type}}: {{data}}. Focus on {{focus_areas}}. Output format: {{format}}"
```

### Template Variables
Common template variables:
- `{{text}}` - Input text to process
- `{{context}}` - Additional context information
- `{{format}}` - Output format specification
- `{{language}}` - Programming language for code analysis
- `{{style}}` - Writing or analysis style
- `{{length}}` - Length constraints for output

## Output Formats

### String Response
```bash
tg-invoke-prompt summarize text="Long document..." max_length="100"
# Output: "This document discusses..."
```

### JSON Response
```bash
tg-invoke-prompt extract-structured data="Name: John, Age: 30, City: NYC"
# Output:
# {
#   "name": "John",
#   "age": 30,
#   "city": "NYC"
# }
```

## Error Handling

### Missing Template
```bash
Exception: Template 'nonexistent-template' not found
```
**Solution**: Check available templates with `tg-show-prompts`.

### Missing Variables
```bash
Exception: Template variable 'required_var' not provided
```
**Solution**: Provide all required variables as `variable=value` arguments.

### Malformed Variables
```bash
Exception: Malformed variable: invalid-format
```
**Solution**: Use `variable=value` format for all variable assignments.

### Flow Not Found
```bash
Exception: Flow instance 'invalid-flow' not found
```
**Solution**: Verify flow ID exists with `tg-show-flows`.

## Advanced Usage

### File Input Processing
```bash
# Process multiple files
for file in *.txt; do
  echo "Processing $file..."
  tg-invoke-prompt summarize \
    text="$(cat "$file")" \
    filename="$file" \
    max_length="150"
done
```

### Batch Processing
```bash
# Process data in batches
while IFS= read -r line; do
  tg-invoke-prompt classify \
    text="$line" \
    categories="spam,ham,promotional" \
    confidence_threshold="0.8"
done < input-data.txt
```

### Pipeline Processing
```bash
# Chain multiple prompts
initial_analysis=$(tg-invoke-prompt analyze data="$(cat raw-data.json)")
summary=$(tg-invoke-prompt summarize text="$initial_analysis" style="executive")
echo "$summary"
```

### Interactive Processing
```bash
#!/bin/bash
# interactive-prompt.sh
template="$1"

if [ -z "$template" ]; then
    echo "Usage: $0 <template-id>"
    exit 1
fi

echo "Interactive prompt using template: $template"
echo "Enter variables (var=value), empty line to execute:"

variables=()
while true; do
    read -p "> " input
    if [ -z "$input" ]; then
        break
    fi
    variables+=("$input")
done

echo "Executing prompt..."
tg-invoke-prompt "$template" "${variables[@]}"
```

### Configuration-Driven Processing
```bash
# Use configuration file for prompts
config_file="prompt-config.json"
template=$(jq -r '.template' "$config_file")
variables=$(jq -r '.variables | to_entries[] | "\(.key)=\(.value)"' "$config_file")

tg-invoke-prompt "$template" $variables
```

## Performance Optimization

### Caching Results
```bash
# Cache prompt results
cache_dir="prompt-cache"
mkdir -p "$cache_dir"

invoke_with_cache() {
    local template="$1"
    shift
    local args="$@"
    local cache_key=$(echo "$template-$args" | md5sum | cut -d' ' -f1)
    local cache_file="$cache_dir/$cache_key.txt"
    
    if [ -f "$cache_file" ]; then
        echo "Cache hit"
        cat "$cache_file"
    else
        echo "Cache miss, invoking prompt..."
        tg-invoke-prompt "$template" "$@" | tee "$cache_file"
    fi
}
```

### Parallel Processing
```bash
# Process multiple items in parallel
input_files=(file1.txt file2.txt file3.txt)
for file in "${input_files[@]}"; do
    (
        echo "Processing $file..."
        tg-invoke-prompt analyze \
            text="$(cat "$file")" \
            filename="$file" > "result-$file.json"
    ) &
done
wait
```

## Use Cases

### Document Processing
```bash
# Extract metadata from documents
tg-invoke-prompt extract-metadata \
  document="$(cat document.pdf)" \
  fields="title,author,date,keywords"

# Generate document summaries
tg-invoke-prompt summarize \
  text="$(cat report.txt)" \
  audience="executives" \
  key_points="5"
```

### Code Analysis
```bash
# Security analysis
tg-invoke-prompt security-review \
  code="$(cat webapp.py)" \
  framework="flask" \
  focus="injection,authentication"

# Performance optimization suggestions
tg-invoke-prompt optimize \
  code="$(cat slow-function.js)" \
  language="javascript" \
  target="performance"
```

### Data Analysis
```bash
# Generate insights from data
tg-invoke-prompt insights \
  data="$(cat metrics.json)" \
  timeframe="monthly" \
  focus="trends,anomalies"

# Create data visualizations
tg-invoke-prompt visualize \
  data="$(cat sales-data.csv)" \
  chart_type="line" \
  metrics="revenue,growth"
```

### Content Generation
```bash
# Generate marketing copy
tg-invoke-prompt marketing \
  product="AI Assistant" \
  audience="developers" \
  tone="professional,friendly"

# Create technical documentation
tg-invoke-prompt document \
  code="$(cat api.py)" \
  format="markdown" \
  sections="overview,examples,parameters"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-prompts`](tg-show-prompts.md) - List available prompt templates
- [`tg-set-prompt`](tg-set-prompt.md) - Create/update prompt templates
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Document-based question answering
- [`tg-show-flows`](tg-show-flows.md) - List available flow instances

## API Integration

This command uses the prompt service API to process templates and generate responses using configured language models.

## Best Practices

1. **Template Reuse**: Create reusable templates for common tasks
2. **Variable Validation**: Validate required variables before execution
3. **Error Handling**: Implement proper error handling for production use
4. **Caching**: Cache results for repeated operations
5. **Documentation**: Document custom templates and their expected variables
6. **Security**: Avoid embedding sensitive data in templates
7. **Performance**: Use appropriate flow instances for different workloads

## Troubleshooting

### Template Not Found
```bash
# Check available templates
tg-show-prompts

# Verify template name spelling
tg-show-prompts | grep "template-name"
```

### Variable Errors
```bash
# Check template definition for required variables
tg-show-prompts | grep -A 10 "template-name"

# Validate variable format
echo "variable=value" | grep "="
```

### Flow Issues
```bash
# Check flow status
tg-show-flows | grep "flow-id"

# Verify flow has prompt service
tg-get-flow-class -n "flow-class" | jq '.interfaces.prompt'
```