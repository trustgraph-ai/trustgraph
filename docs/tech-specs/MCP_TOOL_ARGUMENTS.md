# MCP Tool Arguments Specification

## Overview
**Feature Name**: MCP Tool Arguments Support
**Author**: Claude Code Assistant
**Date**: 2025-08-21
**Status**: Finalised

### Executive Summary

Enable ReACT agents to invoke MCP (Model Context Protocol) tools with
properly defined arguments by adding argument specification support to
MCP tool configurations, similar to how prompt template tools
currently work.

### Problem Statement

Currently, MCP tools in the ReACT agent framework cannot specify their
expected arguments. The `McpToolImpl.get_arguments()` method returns
an empty list, forcing LLMs to guess the correct parameter structure
based only on tool names and descriptions. This leads to:
- Unreliable tool invocations due to parameter guessing
- Poor user experience when tools fail due to incorrect arguments
- No validation of tool parameters before execution
- Missing parameter documentation in agent prompts

### Goals

- [ ] Allow MCP tool configurations to specify expected arguments (name, type, description)
- [ ] Update agent manager to expose MCP tool arguments to LLMs via prompts
- [ ] Maintain backward compatibility with existing MCP tool configurations
- [ ] Support argument validation similar to prompt template tools

### Non-Goals
- Dynamic argument discovery from MCP servers (future enhancement)
- Argument type validation beyond basic structure
- Complex argument schemas (nested objects, arrays)

## Background and Context

### Current State
MCP tools are configured in the ReACT agent system with minimal metadata:
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance",
  "description": "Get bank account balance",
  "mcp-tool": "get_bank_balance"
}
```

The `McpToolImpl.get_arguments()` method returns `[]`, so LLMs receive no argument guidance in their prompts.

### Limitations

1. **No argument specification**: MCP tools cannot define expected
   parameters

2. **LLM parameter guessing**: Agents must infer parameters from tool
   names/descriptions

3. **Missing prompt information**: Agent prompts show no argument
   details for MCP tools

4. **No validation**: Invalid parameters are only caught at MCP tool
   execution time

### Related Components
- **trustgraph-flow/agent/react/service.py**: Tool configuration loading and AgentManager creation
- **trustgraph-flow/agent/react/tools.py**: McpToolImpl implementation  
- **trustgraph-flow/agent/react/agent_manager.py**: Prompt generation with tool arguments
- **trustgraph-cli**: CLI tools for MCP tool management
- **Workbench**: External UI for agent tool configuration

## Requirements

### Functional Requirements

1. **MCP Tool Configuration Arguments**: MCP tool configurations MUST support an optional `arguments` array with name, type, and description fields
2. **Argument Exposure**: `McpToolImpl.get_arguments()` MUST return configured arguments instead of empty list
3. **Prompt Integration**: Agent prompts MUST include MCP tool argument details when arguments are specified
4. **Backward Compatibility**: Existing MCP tool configurations without arguments MUST continue to work
5. **CLI Support**: Existing `tg-invoke-mcp-tool` CLI supports arguments (already implemented)

### Non-Functional Requirements
1. **Backward Compatibility**: Zero breaking changes for existing MCP tool configurations
2. **Performance**: No significant performance impact on agent prompt generation
3. **Consistency**: Argument handling MUST match prompt template tool patterns

### User Stories

1. As an **agent developer**, I want to specify MCP tool arguments in configuration so that LLMs can invoke tools with correct parameters
2. As a **workbench user**, I want to configure MCP tool arguments in the UI so that agents use tools properly
3. As an **LLM in a ReACT agent**, I want to see tool argument specifications in prompts so that I can provide correct parameters

## Design

### High-Level Architecture
Extend MCP tool configuration to match the prompt template pattern by:
1. Adding optional `arguments` array to MCP tool configurations
2. Modifying `McpToolImpl` to accept and return configured arguments  
3. Updating tool configuration loading to handle MCP tool arguments
4. Ensuring agent prompts include MCP tool argument information

### Configuration Schema
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance", 
  "description": "Get bank account balance",
  "mcp-tool": "get_bank_balance",
  "arguments": [
    {
      "name": "account_id",
      "type": "string", 
      "description": "Bank account identifier"
    },
    {
      "name": "date",
      "type": "string",
      "description": "Date for balance query (optional, format: YYYY-MM-DD)"
    }
  ]
}
```

### Data Flow
1. **Configuration Loading**: MCP tool config with arguments is loaded by `on_tools_config()`
2. **Tool Creation**: Arguments are parsed and passed to `McpToolImpl` via constructor
3. **Prompt Generation**: `agent_manager.py` calls `tool.arguments` to include in LLM prompts
4. **Tool Invocation**: LLM provides parameters which are passed to MCP service unchanged

### API Changes
No external API changes - this is purely internal configuration and argument handling.

### Component Details

#### Component 1: service.py (Tool Configuration Loading)
- **Purpose**: Parse MCP tool configurations and create tool instances
- **Changes Required**: Add argument parsing for MCP tools (similar to prompt tools)
- **New Functionality**: Extract `arguments` array from MCP tool config and create `Argument` objects

#### Component 2: tools.py (McpToolImpl)
- **Purpose**: MCP tool implementation wrapper
- **Changes Required**: Accept arguments in constructor and return them from `get_arguments()`
- **New Functionality**: Store and expose configured arguments instead of returning empty list

#### Component 3: Workbench (External Repository)  
- **Purpose**: UI for configuring agent tools
- **Changes Required**: Add argument specification UI for MCP tools
- **New Functionality**: Allow users to add/edit/remove arguments for MCP tools

#### Component 4: CLI Tools
- **Purpose**: Command-line tool management
- **Changes Required**: Support argument specification in MCP tool creation/update commands
- **New Functionality**: Accept arguments parameter in tool configuration commands

## Implementation Plan

### Phase 1: Core Agent Framework Changes
- [ ] Update `McpToolImpl` constructor to accept `arguments` parameter
- [ ] Change `McpToolImpl.get_arguments()` to return stored arguments  
- [ ] Modify `service.py` MCP tool configuration parsing to handle arguments
- [ ] Add unit tests for MCP tool argument handling
- [ ] Verify agent prompts include MCP tool arguments

### Phase 2: External Tool Support
- [ ] Update CLI tools to support MCP tool argument specification
- [ ] Document argument configuration format for users
- [ ] Update Workbench UI to support MCP tool argument configuration
- [ ] Add examples and documentation

### Code Changes Summary
| File | Change Type | Description |
|------|------------|-------------|
| `tools.py` | Modified | Update McpToolImpl to accept and store arguments |
| `service.py` | Modified | Parse arguments from MCP tool config (line 108-113) |
| `test_react_processor.py` | Modified | Add tests for MCP tool arguments |
| CLI tools | Modified | Support argument specification in commands |
| Workbench | Modified | Add UI for MCP tool argument configuration |

## Testing Strategy

### Unit Tests
- **MCP Tool Argument Parsing**: Test `service.py` correctly parses arguments from MCP tool configurations
- **McpToolImpl Arguments**: Test `get_arguments()` returns configured arguments instead of empty list
- **Backward Compatibility**: Test MCP tools without arguments continue to work (return empty list)
- **Agent Prompt Generation**: Test agent prompts include MCP tool argument details

### Integration Tests  
- **End-to-End Tool Invocation**: Test agent with MCP tool arguments can successfully invoke tools
- **Configuration Loading**: Test complete config load cycle with MCP tool arguments
- **Cross-Component**: Test arguments flow correctly from config → tool creation → prompt generation

### Manual Testing
- **Agent Behavior**: Manually verify LLM receives and uses argument information in ReACT cycles
- **CLI Integration**: Test tg-invoke-mcp-tool works with new argument-configured MCP tools
- **Workbench Integration**: Test UI supports MCP tool argument configuration

## Migration and Rollout

### Migration Strategy
No migration required - this is purely additive functionality:
- Existing MCP tool configurations without `arguments` continue to work unchanged
- `McpToolImpl.get_arguments()` returns empty list for legacy tools  
- New configurations can optionally include `arguments` array

### Rollout Plan
1. **Phase 1**: Deploy core agent framework changes to development/staging
2. **Phase 2**: Deploy CLI tool updates and documentation
3. **Phase 3**: Deploy Workbench UI updates for argument configuration
4. **Phase 4**: Production rollout with monitoring

### Rollback Plan
- Core changes are backward compatible - no rollback needed for functionality
- If issues arise, disable argument parsing by reverting MCP tool config loading logic
- Workbench and CLI changes are independent and can be rolled back separately

## Security Considerations
- **No new attack surface**: Arguments are parsed from existing configuration sources with no new inputs
- **Parameter validation**: Arguments are passed through to MCP tools unchanged - validation remains at MCP tool level  
- **Configuration integrity**: Argument specifications are part of tool configuration - same security model applies

## Performance Impact
- **Minimal overhead**: Argument parsing happens only during configuration loading, not per-request
- **Prompt size increase**: Agent prompts will include MCP tool argument details, slightly increasing token usage
- **Memory usage**: Negligible increase for storing argument specifications in tool objects

## Documentation

### User Documentation
- [ ] Update MCP tool configuration guide with argument examples
- [ ] Add argument specification to CLI tool help text  
- [ ] Create examples of common MCP tool argument patterns

### Developer Documentation
- [ ] Update McpToolImpl class documentation
- [ ] Add inline comments for argument parsing logic
- [ ] Document argument flow in system architecture

## Open Questions
1. **Argument validation**: Should we validate argument types/formats beyond basic structure checking?
2. **Dynamic discovery**: Future enhancement to query MCP servers for tool schemas automatically?

## Alternatives Considered
1. **Dynamic MCP schema discovery**: Query MCP servers for tool argument schemas at runtime - rejected due to complexity and reliability concerns
2. **Separate argument registry**: Store MCP tool arguments in separate configuration section - rejected for consistency with prompt template approach
3. **Type validation**: Full JSON schema validation for arguments - deferred as future enhancement to keep initial implementation simple

## References
- [MCP Protocol Specification](https://github.com/modelcontextprotocol/spec)
- [Prompt Template Tool Implementation](./trustgraph-flow/trustgraph/agent/react/service.py#L114-129)
- [Current MCP Tool Implementation](./trustgraph-flow/trustgraph/agent/react/tools.py#L58-86)

## Appendix
[Any additional information, diagrams, or examples]
