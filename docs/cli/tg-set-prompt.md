# tg-set-prompt

Sets prompt templates and system prompts for TrustGraph LLM services.

## Synopsis

```bash
# Set a prompt template
tg-set-prompt --id TEMPLATE_ID --prompt TEMPLATE [options]

# Set system prompt
tg-set-prompt --system SYSTEM_PROMPT
```

## Description

The `tg-set-prompt` command configures prompt templates and system prompts used by TrustGraph's LLM services. Prompt templates contain placeholders like `{{variable}}` that are replaced with actual values when invoked. System prompts provide global context for all LLM interactions.

Templates are stored in TrustGraph's configuration system and can be used with `tg-invoke-prompt` for consistent AI interactions.

## Options

### Prompt Template Mode

- `--id ID`: Unique identifier for the prompt template (required for templates)
- `--prompt TEMPLATE`: Prompt template text with `{{variable}}` placeholders (required for templates)
- `--response TYPE`: Response format - `text` or `json` (default: `text`)
- `--schema SCHEMA`: JSON schema for structured responses (required when response is `json`)

### System Prompt Mode

- `--system PROMPT`: System prompt text (cannot be used with other options)

### Common Options

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Basic Prompt Template
```bash
tg-set-prompt \
  --id "greeting" \
  --prompt "Hello {{name}}, welcome to {{place}}!"
```

### Question-Answer Template
```bash
tg-set-prompt \
  --id "question" \
  --prompt "Answer this question based on the context: {{question}}\n\nContext: {{context}}"
```

### JSON Response Template
```bash
tg-set-prompt \
  --id "extract-info" \
  --prompt "Extract key information from: {{text}}" \
  --response "json" \
  --schema '{"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "number"}}}'
```

### Analysis Template
```bash
tg-set-prompt \
  --id "analyze" \
  --prompt "Analyze the following {{data_type}} and provide insights about {{focus_area}}:\n\n{{data}}\n\nFormat the response as {{format}}."
```

### System Prompt
```bash
tg-set-prompt \
  --system "You are a helpful AI assistant. Always provide accurate, concise responses. When uncertain, clearly state your limitations."
```

## Template Variables

### Variable Syntax
Templates use `{{variable}}` syntax for placeholders:
```bash
# Template
"Hello {{name}}, today is {{day}}"

# Usage
tg-invoke-prompt greeting name="Alice" day="Monday"
# Result: "Hello Alice, today is Monday"
```

### Common Variables
- `{{text}}` - Input text for processing
- `{{question}}` - Question to answer
- `{{context}}` - Background context
- `{{data}}` - Data to analyze
- `{{format}}` - Output format specification

## Response Types

### Text Response (Default)
```bash
tg-set-prompt \
  --id "summarize" \
  --prompt "Summarize this text in {{max_words}} words: {{text}}"
```

### JSON Response
```bash
tg-set-prompt \
  --id "classify" \
  --prompt "Classify this text: {{text}}" \
  --response "json" \
  --schema '{
    "type": "object",
    "properties": {
      "category": {"type": "string"},
      "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "required": ["category", "confidence"]
  }'
```

## Use Cases

### Document Processing Templates
```bash
# Document summarization
tg-set-prompt \
  --id "document-summary" \
  --prompt "Provide a {{length}} summary of this document:\n\n{{document}}\n\nFocus on: {{focus_areas}}"

# Key point extraction
tg-set-prompt \
  --id "extract-key-points" \
  --prompt "Extract the main points from: {{text}}\n\nReturn as a bulleted list."

# Document classification
tg-set-prompt \
  --id "classify-document" \
  --prompt "Classify this document into one of these categories: {{categories}}\n\nDocument: {{text}}" \
  --response "json" \
  --schema '{"type": "object", "properties": {"category": {"type": "string"}, "confidence": {"type": "number"}}}'
```

### Code Analysis Templates
```bash
# Code review
tg-set-prompt \
  --id "code-review" \
  --prompt "Review this {{language}} code for {{focus}} issues:\n\n{{code}}\n\nProvide specific recommendations."

# Bug detection
tg-set-prompt \
  --id "find-bugs" \
  --prompt "Analyze this code for potential bugs:\n\n{{code}}\n\nError context: {{error}}"

# Code explanation
tg-set-prompt \
  --id "explain-code" \
  --prompt "Explain how this {{language}} code works:\n\n{{code}}\n\nTarget audience: {{audience}}"
```

### Data Analysis Templates
```bash
# Data insights
tg-set-prompt \
  --id "data-insights" \
  --prompt "Analyze this {{data_type}} data and provide insights:\n\n{{data}}\n\nFocus on: {{metrics}}"

# Trend analysis
tg-set-prompt \
  --id "trend-analysis" \
  --prompt "Identify trends in this data over {{timeframe}}:\n\n{{data}}" \
  --response "json" \
  --schema '{"type": "object", "properties": {"trends": {"type": "array", "items": {"type": "string"}}}}'
```

### Content Generation Templates
```bash
# Marketing copy
tg-set-prompt \
  --id "marketing-copy" \
  --prompt "Create {{tone}} marketing copy for {{product}} targeting {{audience}}. Key features: {{features}}"

# Technical documentation
tg-set-prompt \
  --id "tech-docs" \
  --prompt "Generate technical documentation for:\n\n{{code}}\n\nInclude: {{sections}}"
```

## Advanced Usage

### Multi-Step Templates
```bash
# Research template
tg-set-prompt \
  --id "research" \
  --prompt "Research question: {{question}}

Available sources: {{sources}}

Please:
1. Analyze the question
2. Review relevant sources
3. Synthesize findings
4. Provide conclusions

Format: {{output_format}}"
```

### Conditional Templates
```bash
# Adaptive response template
tg-set-prompt \
  --id "adaptive-response" \
  --prompt "Task: {{task}}
Context: {{context}}
Expertise level: {{level}}

If expertise level is 'beginner', provide simple explanations.
If expertise level is 'advanced', include technical details.
If task involves code, include examples.

Response:"
```

### Structured Analysis Template
```bash
tg-set-prompt \
  --id "structured-analysis" \
  --prompt "Analyze: {{subject}}
Criteria: {{criteria}}
Data: {{data}}

Provide analysis in this structure:
- Overview
- Key Findings
- Recommendations
- Next Steps" \
  --response "json" \
  --schema '{
    "type": "object",
    "properties": {
      "overview": {"type": "string"},
      "key_findings": {"type": "array", "items": {"type": "string"}},
      "recommendations": {"type": "array", "items": {"type": "string"}},
      "next_steps": {"type": "array", "items": {"type": "string"}}
    }
  }'
```

### Template Management
```bash
# Create template collection for specific domain
domain="customer-support"
templates=(
  "greeting:Hello! I'm here to help with {{issue_type}}. What can I assist you with?"
  "escalation:I understand your frustration with {{issue}}. Let me escalate this to {{department}}."
  "resolution:Great! I've resolved your {{issue}}. Is there anything else I can help with?"
)

for template in "${templates[@]}"; do
  IFS=':' read -r id prompt <<< "$template"
  tg-set-prompt --id "${domain}-${id}" --prompt "$prompt"
done
```

## System Prompt Configuration

### General Purpose System Prompt
```bash
tg-set-prompt --system "You are a knowledgeable AI assistant. Provide accurate, helpful responses. When you don't know something, say so clearly. Always consider the context and be concise unless detail is specifically requested."
```

### Domain-Specific System Prompt
```bash
tg-set-prompt --system "You are a technical documentation assistant specializing in software development. Focus on clarity, accuracy, and practical examples. Always include code snippets when relevant and explain complex concepts step-by-step."
```

### Role-Based System Prompt
```bash
tg-set-prompt --system "You are a data analyst AI. When analyzing data, always consider statistical significance, potential biases, and limitations. Present findings objectively and suggest actionable insights."
```

## Error Handling

### Missing Required Fields
```bash
Exception: Must specify --id for prompt
```
**Solution**: Provide both `--id` and `--prompt` for template creation.

### Invalid Response Type
```bash
Exception: Response must be one of: text json
```
**Solution**: Use only `text` or `json` for the `--response` option.

### Invalid JSON Schema
```bash
Exception: JSON schema must be valid JSON
```
**Solution**: Validate JSON schema syntax before using `--schema`.

### Conflicting Options
```bash
Exception: Can't use --system with other args
```
**Solution**: Use `--system` alone, or use template options without `--system`.

## Template Testing

### Test Template Creation
```bash
# Create and test a simple template
tg-set-prompt \
  --id "test-template" \
  --prompt "Test template with {{variable1}} and {{variable2}}"

# Test the template
tg-invoke-prompt test-template variable1="hello" variable2="world"
```

### Validate JSON Templates
```bash
# Create JSON template
tg-set-prompt \
  --id "json-test" \
  --prompt "Extract data from: {{text}}" \
  --response "json" \
  --schema '{"type": "object", "properties": {"result": {"type": "string"}}}'

# Test JSON response
tg-invoke-prompt json-test text="Sample text for testing"
```

### Template Iteration
```bash
# Version 1
tg-set-prompt \
  --id "analysis-v1" \
  --prompt "Analyze: {{data}}"

# Version 2 (improved)
tg-set-prompt \
  --id "analysis-v2" \
  --prompt "Analyze the following {{data_type}} and provide insights about {{focus}}:\n\n{{data}}\n\nConsider: {{considerations}}"

# Version 3 (structured)
tg-set-prompt \
  --id "analysis-v3" \
  --prompt "Analyze: {{data}}" \
  --response "json" \
  --schema '{"type": "object", "properties": {"summary": {"type": "string"}, "insights": {"type": "array"}}}'
```

## Best Practices

### Template Design
```bash
# Good: Clear, specific prompts
tg-set-prompt \
  --id "good-summary" \
  --prompt "Summarize this {{document_type}} in {{word_count}} words, focusing on {{key_aspects}}:\n\n{{content}}"

# Better: Include context and constraints
tg-set-prompt \
  --id "better-summary" \
  --prompt "Task: Summarize the following {{document_type}}
Length: {{word_count}} words maximum
Focus: {{key_aspects}}
Audience: {{target_audience}}

Document:
{{content}}

Summary:"
```

### Variable Naming
```bash
# Use descriptive variable names
tg-set-prompt \
  --id "descriptive-vars" \
  --prompt "Analyze {{data_source}} data from {{time_period}} for {{business_metric}} trends"

# Group related variables
tg-set-prompt \
  --id "grouped-vars" \
  --prompt "Compare {{baseline_data}} vs {{comparison_data}} using {{analysis_method}}"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-prompts`](tg-show-prompts.md) - Display configured prompts
- [`tg-invoke-prompt`](tg-invoke-prompt.md) - Use prompt templates
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Document-based AI queries

## API Integration

This command uses the [Config API](../apis/api-config.md) to store prompt templates and system prompts in TrustGraph's configuration system.

## Best Practices

1. **Clear Templates**: Write clear, specific prompt templates
2. **Variable Names**: Use descriptive variable names
3. **Response Types**: Choose appropriate response types for your use case
4. **Schema Validation**: Always validate JSON schemas before setting
5. **Version Control**: Consider versioning important templates
6. **Testing**: Test templates thoroughly with various inputs
7. **Documentation**: Document template variables and expected usage

## Troubleshooting

### Template Not Working
```bash
# Check template exists
tg-show-prompts | grep "template-id"

# Verify variable names match
tg-invoke-prompt template-id var1="test" var2="test"
```

### JSON Schema Errors
```bash
# Validate schema separately
echo '{"type": "object"}' | jq .

# Test with simple schema first
tg-set-prompt --id "test" --prompt "test" --response "json" --schema '{"type": "string"}'
```

### System Prompt Issues
```bash
# Check current system prompt
tg-show-prompts | grep -A5 "System prompt"

# Reset if needed
tg-set-prompt --system "Default system prompt"
```