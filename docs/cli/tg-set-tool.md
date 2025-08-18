# tg-set-tool

## Synopsis

```
tg-set-tool [OPTIONS] --id ID --name NAME --type TYPE --description DESCRIPTION [--argument ARG...]
```

## Description

The `tg-set-tool` command configures and registers tools in the TrustGraph system. It allows defining tool metadata including ID, name, description, type, and argument specifications. Tools are stored in the agent configuration and indexed for discovery and execution.

This command is useful for:
- Registering new tools for agent use
- Updating existing tool configurations
- Defining tool arguments and parameter types
- Managing the tool registry for agent workflows

The command updates both the tool index and stores the complete tool configuration in the TrustGraph API.

## Options

- `-u, --api-url URL`
  - TrustGraph API URL for configuration storage
  - Default: `http://localhost:8088/` (or `TRUSTGRAPH_URL` environment variable)
  - Should point to a running TrustGraph API instance

- `--id ID`
  - **Required.** Unique identifier for the tool
  - Used to reference the tool in configurations and agent workflows
  - Must be unique within the tool registry

- `--name NAME`
  - **Required.** Human-readable name for the tool
  - Displayed in tool listings and user interfaces
  - Should be descriptive and clear

- `--type TYPE`
  - **Required.** Tool type defining its functionality
  - Valid types:
    - `knowledge-query` - Query knowledge bases
    - `text-completion` - Text completion/generation
    - `mcp-tool` - Model Control Protocol tool

- `--description DESCRIPTION`
  - **Required.** Detailed description of what the tool does
  - Used by agents to understand tool capabilities
  - Should clearly explain the tool's purpose and function

- `--argument ARG`
  - Tool argument specification in format: `name:type:description`
  - Can be specified multiple times for multiple arguments
  - Valid argument types:
    - `string` - String/text parameter
    - `number` - Numeric parameter

- `-h, --help`
  - Show help message and exit

## Examples

### Basic Tool Registration

Register a simple weather lookup tool:
```bash
tg-set-tool --id weather --name "Weather Lookup" \
            --type knowledge-query \
            --description "Get current weather information" \
            --argument location:string:"Location to query" \
            --argument units:string:"Temperature units (C/F)"
```

### Calculator Tool

Register a calculator tool with MCP type:
```bash
tg-set-tool --id calculator --name "Calculator" --type mcp-tool \
            --description "Perform mathematical calculations" \
            --argument expression:string:"Mathematical expression to evaluate"
```

### Text Completion Tool

Register a text completion tool:
```bash
tg-set-tool --id text-generator --name "Text Generator" \
            --type text-completion \
            --description "Generate text based on prompts" \
            --argument prompt:string:"Text prompt for generation" \
            --argument max_tokens:number:"Maximum tokens to generate"
```

### Custom API URL

Register a tool with custom API endpoint:
```bash
tg-set-tool -u http://trustgraph.example.com:8088/ \
            --id custom-tool --name "Custom Tool" \
            --type knowledge-query \
            --description "Custom tool functionality"
```

### Tool Without Arguments

Register a simple tool with no arguments:
```bash
tg-set-tool --id status-check --name "Status Check" \
            --type knowledge-query \
            --description "Check system status"
```

## Tool Types

### knowledge-query
Tools that query knowledge bases, databases, or information systems:
- Used for information retrieval
- Typically return structured data or search results
- Examples: web search, document lookup, database queries

### text-completion
Tools that generate or complete text:
- Used for text generation tasks
- Process prompts and return generated content
- Examples: language models, text generators, summarizers

### mcp-tool
Model Control Protocol tools:
- Standardized tool interface for AI models
- Support complex interactions and state management
- Examples: external API integrations, complex workflows

## Argument Types

### string
Text or string parameters:
- Accept any text input
- Used for queries, prompts, identifiers
- Should include clear description of expected format

### number
Numeric parameters:
- Accept integer or floating-point values
- Used for limits, thresholds, quantities
- Should specify valid ranges when applicable

## Configuration Storage

The tool configuration is stored in two parts:

1. **Tool Index** (`agent.tool-index`)
   - List of all registered tool IDs
   - Updated to include new tools
   - Used for tool discovery

2. **Tool Configuration** (`agent.tool.{id}`)
   - Complete tool definition as JSON
   - Includes metadata and argument specifications
   - Used for tool execution and validation

## Advanced Usage

### Updating Existing Tools

Update an existing tool configuration:
```bash
# Update tool description
tg-set-tool --id weather --name "Weather Lookup" \
            --type knowledge-query \
            --description "Updated weather information service" \
            --argument location:string:"Location to query"
```

### Batch Tool Registration

Register multiple tools in a script:
```bash
#!/bin/bash
# Register a suite of tools
tg-set-tool --id search --name "Web Search" --type knowledge-query \
            --description "Search the web" \
            --argument query:string:"Search query"

tg-set-tool --id summarize --name "Text Summarizer" --type text-completion \
            --description "Summarize text content" \
            --argument text:string:"Text to summarize"

tg-set-tool --id translate --name "Translator" --type mcp-tool \
            --description "Translate text between languages" \
            --argument text:string:"Text to translate" \
            --argument target_lang:string:"Target language"
```

### Tool Validation

Verify tool registration:
```bash
# Register tool and verify
tg-set-tool --id test-tool --name "Test Tool" \
            --type knowledge-query \
            --description "Test tool for validation"

# Check if tool was registered
tg-show-tools | grep test-tool
```

## Error Handling

The command handles various error conditions:

- **Missing required arguments**: All required fields must be provided
- **Invalid tool types**: Only valid types are accepted
- **Invalid argument format**: Arguments must follow `name:type:description` format
- **API connection errors**: If the TrustGraph API is unavailable
- **Configuration errors**: If tool data cannot be stored

Common error scenarios:
```bash
# Missing required field
tg-set-tool --id tool1 --name "Tool 1"
# Output: Exception: Must specify --type for tool

# Invalid tool type
tg-set-tool --id tool1 --name "Tool 1" --type invalid-type
# Output: Exception: Type must be one of: knowledge-query, text-completion, mcp-tool

# Invalid argument format
tg-set-tool --id tool1 --name "Tool 1" --type knowledge-query \
            --argument "bad-format"
# Output: Exception: Arguments should be form name:type:description
```

## Integration with Other Commands

### With Tool Management

View registered tools:
```bash
# Register tool
tg-set-tool --id new-tool --name "New Tool" \
            --type knowledge-query \
            --description "Newly registered tool"

# View all tools
tg-show-tools
```

### With Agent Invocation

Use registered tools with agents:
```bash
# Register tool
tg-set-tool --id weather --name "Weather" \
            --type knowledge-query \
            --description "Weather lookup"

# Use tool in agent workflow
tg-invoke-agent --prompt "What's the weather in London?"
```

### With Flow Configuration

Tools can be used in flow configurations:
```bash
# Register tool for flow use
tg-set-tool --id data-processor --name "Data Processor" \
            --type mcp-tool \
            --description "Process data in flows"

# View flows that might use the tool
tg-show-flows
```

## Best Practices

1. **Clear Naming**: Use descriptive, unique tool IDs and names
2. **Detailed Descriptions**: Provide comprehensive tool descriptions
3. **Argument Documentation**: Clearly describe each argument's purpose
4. **Type Selection**: Choose appropriate tool types for functionality
5. **Validation**: Test tools after registration
6. **Version Management**: Track tool configuration changes
7. **Documentation**: Document custom tools and their usage

## Troubleshooting

### Tool Not Appearing

If a registered tool doesn't appear in listings:
1. Verify the tool was registered successfully
2. Check the tool index with `tg-show-tools`
3. Ensure the API URL is correct
4. Verify TrustGraph API is running

### Tool Registration Errors

If tool registration fails:
1. Check all required arguments are provided
2. Verify argument format is correct
3. Ensure tool type is valid
4. Check API connectivity
5. Review error messages for specific issues

### Tool Configuration Issues

If tools aren't working as expected:
1. Verify tool arguments are correctly specified
2. Check tool type matches intended functionality
3. Ensure tool implementation is available
4. Review agent logs for tool execution errors

## Related Commands

- [`tg-show-tools`](tg-show-tools.md) - Display registered tools
- [`tg-delete-tool`](tg-delete-tool.md) - Remove tool configurations
- [`tg-set-mcp-tool`](tg-set-mcp-tool.md) - Configure MCP tools
- [`tg-invoke-agent`](tg-invoke-agent.md) - Use tools with agents

## See Also

- TrustGraph Tool Development Guide
- Agent Configuration Documentation
- MCP Tool Integration Guide