# More Configuration CLI Technical Specification

## Overview

This specification describes enhanced command-line configuration capabilities for TrustGraph, enabling users to manage individual configuration items through granular CLI commands. The integration supports four primary use cases:

1. **List Configuration Items**: Display configuration keys of a specific type
2. **Get Configuration Item**: Retrieve specific configuration values
3. **Put Configuration Item**: Set or update individual configuration items
4. **Delete Configuration Item**: Remove specific configuration items

## Goals

- **Granular Control**: Enable management of individual configuration items rather than bulk operations
- **Type-Based Listing**: Allow users to explore configuration items by type
- **Single Item Operations**: Provide commands for get/put/delete of individual config items
- **API Integration**: Leverage existing Config API for all operations
- **Consistent CLI Pattern**: Follow established TrustGraph CLI conventions and patterns
- **Error Handling**: Provide clear error messages for invalid operations
- **JSON Output**: Support structured output for programmatic use
- **Documentation**: Include comprehensive help and usage examples

## Background

TrustGraph currently provides configuration management through the Config API and a single CLI command `tg-show-config` that displays the entire configuration. While this works for viewing configuration, it lacks granular management capabilities.

Current limitations include:
- No way to list configuration items by type from CLI
- No CLI command to retrieve specific configuration values
- No CLI command to set individual configuration items
- No CLI command to delete specific configuration items

This specification addresses these gaps by adding four new CLI commands that provide granular configuration management. By exposing individual Config API operations through CLI commands, TrustGraph can:
- Enable scripted configuration management
- Allow exploration of configuration structure by type
- Support targeted configuration updates
- Provide fine-grained configuration control

## Technical Design

### Architecture

The enhanced CLI configuration requires the following technical components:

1. **tg-list-config-items**
   - Lists configuration keys for a specified type
   - Calls Config.list(type) API method
   - Outputs list of configuration keys
   
   Module: `trustgraph.cli.list_config_items`

2. **tg-get-config-item**
   - Retrieves specific configuration item(s)
   - Calls Config.get(keys) API method
   - Outputs configuration values in JSON format

   Module: `trustgraph.cli.get_config_item`

3. **tg-put-config-item**
   - Sets or updates a configuration item
   - Calls Config.put(values) API method
   - Accepts type, key, and value parameters

   Module: `trustgraph.cli.put_config_item`

4. **tg-delete-config-item**
   - Removes a configuration item
   - Calls Config.delete(keys) API method
   - Accepts type and key parameters

   Module: `trustgraph.cli.delete_config_item`

### Data Models

#### ConfigKey and ConfigValue

The commands utilize existing data structures from `trustgraph.api.types`:

```python
@dataclasses.dataclass
class ConfigKey:
    type : str
    key : str

@dataclasses.dataclass
class ConfigValue:
    type : str
    key : str
    value : str
```

This approach allows:
- Consistent data handling across CLI and API
- Type-safe configuration operations
- Structured input/output formats
- Integration with existing Config API

### CLI Command Specifications

#### tg-list-config-items
```bash
tg-list-config-items --type <config-type> [--format text|json] [--api-url <url>]
```
- **Purpose**: List all configuration keys for a given type
- **API Call**: `Config.list(type)`
- **Output**: 
  - `text` (default): Configuration keys separated by newlines
  - `json`: JSON array of configuration keys

#### tg-get-config-item
```bash
tg-get-config-item --type <type> --key <key> [--format text|json] [--api-url <url>]
```
- **Purpose**: Retrieve specific configuration item
- **API Call**: `Config.get([ConfigKey(type, key)])`
- **Output**: 
  - `text` (default): Raw string value
  - `json`: JSON-encoded string value

#### tg-put-config-item
```bash
tg-put-config-item --type <type> --key <key> --value <value> [--api-url <url>]
tg-put-config-item --type <type> --key <key> --stdin [--api-url <url>]
```
- **Purpose**: Set or update configuration item
- **API Call**: `Config.put([ConfigValue(type, key, value)])`
- **Input Options**:
  - `--value`: String value provided directly on command line
  - `--stdin`: Read value from standard input
- **Output**: Success confirmation

#### tg-delete-config-item
```bash
tg-delete-config-item --type <type> --key <key> [--api-url <url>]
```
- **Purpose**: Delete configuration item
- **API Call**: `Config.delete([ConfigKey(type, key)])`
- **Output**: Success confirmation

### Implementation Details

All commands follow the established TrustGraph CLI pattern:
- Use `argparse` for command-line argument parsing
- Import and use `trustgraph.api.Api` for backend communication
- Follow the same error handling patterns as existing CLI commands
- Support the standard `--api-url` parameter for API endpoint configuration
- Provide descriptive help text and usage examples

#### Output Format Handling

**Text Format (Default)**:
- `tg-list-config-items`: One key per line, plain text
- `tg-get-config-item`: Raw string value, no quotes or encoding

**JSON Format**:
- `tg-list-config-items`: Array of strings `["key1", "key2", "key3"]`
- `tg-get-config-item`: JSON-encoded string value `"actual string value"`

#### Input Handling

**tg-put-config-item** supports two mutually exclusive input methods:
- `--value <string>`: Direct command-line string value
- `--stdin`: Read entire input from standard input as the configuration value
- stdin contents are read as raw text (preserving newlines, whitespace, etc.)
- Supports piping from files, commands, or interactive input

## Security Considerations

- **Input Validation**: All command-line parameters must be validated before API calls
- **API Authentication**: Commands inherit existing API authentication mechanisms
- **Configuration Access**: Commands respect existing configuration access controls
- **Error Information**: Error messages should not leak sensitive configuration details

## Performance Considerations

- **Single Item Operations**: Commands are designed for individual items, avoiding bulk operation overhead
- **API Efficiency**: Direct API calls minimize processing layers
- **Network Latency**: Each command makes one API call, minimizing network round trips
- **Memory Usage**: Minimal memory footprint for single-item operations

## Testing Strategy

- **Unit Tests**: Test each CLI command module independently
- **Integration Tests**: Test CLI commands against live Config API
- **Error Handling Tests**: Verify proper error handling for invalid inputs
- **API Compatibility**: Ensure commands work with existing Config API versions

## Migration Plan

No migration required - these are new CLI commands that complement existing functionality:
- Existing `tg-show-config` command remains unchanged
- New commands can be added incrementally
- No breaking changes to existing configuration workflows

## Packaging and Distribution

These commands will be added to the existing `trustgraph-cli` package:

**Package Location**: `trustgraph-cli/`
**Module Files**:
- `trustgraph-cli/trustgraph/cli/list_config_items.py`
- `trustgraph-cli/trustgraph/cli/get_config_item.py` 
- `trustgraph-cli/trustgraph/cli/put_config_item.py`
- `trustgraph-cli/trustgraph/cli/delete_config_item.py`

**Entry Points**: Added to `trustgraph-cli/pyproject.toml` in `[project.scripts]` section:
```toml
tg-list-config-items = "trustgraph.cli.list_config_items:main"
tg-get-config-item = "trustgraph.cli.get_config_item:main"
tg-put-config-item = "trustgraph.cli.put_config_item:main"
tg-delete-config-item = "trustgraph.cli.delete_config_item:main"
```

## Implementation Tasks

1. **Create CLI Modules**: Implement the four CLI command modules in `trustgraph-cli/trustgraph/cli/`
2. **Update pyproject.toml**: Add new command entry points to `trustgraph-cli/pyproject.toml`
3. **Documentation**: Create CLI documentation for each command in `docs/cli/`
4. **Testing**: Implement comprehensive test coverage
5. **Integration**: Ensure commands work with existing TrustGraph infrastructure
6. **Package Build**: Verify commands are properly installed with `pip install trustgraph-cli`

## Usage Examples

#### List configuration items
```bash
# List prompt keys (text format)
tg-list-config-items --type prompt
template-1
template-2
system-prompt

# List prompt keys (JSON format)  
tg-list-config-items --type prompt --format json
["template-1", "template-2", "system-prompt"]
```

#### Get configuration item
```bash
# Get prompt value (text format)
tg-get-config-item --type prompt --key template-1
You are a helpful assistant. Please respond to: {query}

# Get prompt value (JSON format)
tg-get-config-item --type prompt --key template-1 --format json
"You are a helpful assistant. Please respond to: {query}"
```

#### Set configuration item
```bash
# Set from command line
tg-put-config-item --type prompt --key new-template --value "Custom prompt: {input}"

# Set from file via pipe
cat ./prompt-template.txt | tg-put-config-item --type prompt --key complex-template --stdin

# Set from file via redirect
tg-put-config-item --type prompt --key complex-template --stdin < ./prompt-template.txt

# Set from command output
echo "Generated template: {query}" | tg-put-config-item --type prompt --key auto-template --stdin
```

#### Delete configuration item
```bash
tg-delete-config-item --type prompt --key old-template
```

## Open Questions

- Should commands support batch operations (multiple keys) in addition to single items?
- What output format should be used for success confirmations?
- How should configuration types be documented/discovered by users?

## References

- Existing Config API: `trustgraph/api/config.py`
- CLI patterns: `trustgraph-cli/trustgraph/cli/show_config.py`
- Data types: `trustgraph/api/types.py`