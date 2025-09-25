# Flow Class Configurable Parameters Technical Specification

## Overview

This specification describes the implementation of configurable parameters for flow classes in TrustGraph. Parameters enable users to customize processor parameters at flow launch time by providing values that replace parameter placeholders in the flow class definition.

Parameters work through template variable substitution in processor parameters, similar to how `{id}` and `{class}` variables work, but with user-provided values.

The integration supports four primary use cases:

1. **Model Selection**: Allowing users to choose different LLM models (e.g., `gemma3:8b`, `gpt-4`, `claude-3`) for processors
2. **Resource Configuration**: Adjusting processor parameters like chunk sizes, batch sizes, and concurrency limits
3. **Behavioral Tuning**: Modifying processor behavior through parameters like temperature, max-tokens, or retrieval thresholds
4. **Environment-Specific Parameters**: Configuring endpoints, API keys, or region-specific URLs per deployment

## Goals

- **Dynamic Processor Configuration**: Enable runtime configuration of processor parameters through parameter substitution
- **Parameter Validation**: Provide type checking and validation for parameters at flow launch time
- **Default Values**: Support sensible defaults while allowing overrides for advanced users
- **Template Substitution**: Seamlessly replace parameter placeholders in processor parameters
- **UI Integration**: Enable parameter input through both API and UI interfaces
- **Type Safety**: Ensure parameter types match expected processor parameter types
- **Documentation**: Self-documenting parameter schemas within flow class definitions
- **Backward Compatibility**: Maintain compatibility with existing flow classes that don't use parameters

## Background

Flow classes in TrustGraph now support processor parameters that can contain either fixed values or parameter placeholders. This creates an opportunity for runtime customization.

Current processor parameters support:
- Fixed values: `"model": "gemma3:12b"`
- Parameter placeholders: `"model": "gemma3:{model-size}"`

This specification defines how parameters are:
- Declared in flow class definitions
- Validated when flows are launched
- Substituted in processor parameters
- Exposed through APIs and UI

By leveraging parameterized processor parameters, TrustGraph can:
- Reduce flow class duplication by using parameters for variations
- Enable users to tune processor behavior without modifying definitions
- Support environment-specific configurations through parameter values
- Maintain type safety through parameter schema validation

## Technical Design

### Architecture

The configurable parameters system requires the following technical components:

1. **Parameter Schema Definition**
   - JSON Schema-based parameter definitions within flow class metadata
   - Type definitions including string, number, boolean, enum, and object types
   - Validation rules including min/max values, patterns, and required fields

   Module: trustgraph-flow/trustgraph/flow/definition.py

2. **Parameter Resolution Engine**
   - Runtime parameter validation against schema
   - Default value application for unspecified parameters
   - Parameter injection into flow execution context
   - Type coercion and conversion as needed

   Module: trustgraph-flow/trustgraph/flow/parameter_resolver.py

3. **Parameter Store Integration**
   - Retrieval of parameter definitions from schema/config store
   - Caching of frequently-used parameter definitions
   - Validation against centrally-stored schemas

   Module: trustgraph-flow/trustgraph/flow/parameter_store.py

4. **Flow Launcher Extensions**
   - API extensions to accept parameter values during flow launch
   - Parameter mapping resolution (flow names to definition names)
   - Error handling for invalid parameter combinations

   Module: trustgraph-flow/trustgraph/flow/launcher.py

5. **UI Parameter Forms**
   - Dynamic form generation from flow parameter metadata
   - Ordered parameter display using `order` field
   - Descriptive parameter labels using `description` field
   - Input validation against parameter type definitions
   - Parameter presets and templates

   Module: trustgraph-ui/components/flow-parameters/

### Data Models

#### Parameter Definitions (Stored in Schema/Config)

Parameter definitions are stored centrally in the schema and config system with type "parameter-types":

```json
{
  "llm-model": {
    "type": "string",
    "description": "LLM model to use",
    "default": "gpt-4",
    "enum": ["gpt-4", "gpt-3.5-turbo", "claude-3", "gemma3:8b"],
    "required": false
  },
  "model-size": {
    "type": "string",
    "description": "Model size variant",
    "default": "8b",
    "enum": ["2b", "8b", "12b", "70b"],
    "required": false
  },
  "temperature": {
    "type": "number",
    "description": "Model temperature for generation",
    "default": 0.7,
    "minimum": 0.0,
    "maximum": 2.0,
    "required": false
  },
  "chunk-size": {
    "type": "integer",
    "description": "Document chunk size",
    "default": 512,
    "minimum": 128,
    "maximum": 2048,
    "required": false
  }
}
```

#### Flow Class with Parameter References

Flow classes define parameter metadata with type references, descriptions, and ordering:

```json
{
  "flow_class": "document-analysis",
  "parameters": {
    "model": {
      "type": "llm-model",
      "description": "LLM model to use for document analysis",
      "order": 1
    },
    "size": {
      "type": "model-size",
      "description": "Model size variant to use",
      "order": 2
    },
    "temp": {
      "type": "temperature",
      "description": "Generation temperature for creativity control",
      "order": 3
    },
    "chunk": {
      "type": "chunk-size",
      "description": "Document chunk size for processing",
      "order": 4
    }
  },
  "class": {
    "text-completion:{class}": {
      "request": "non-persistent://tg/request/text-completion:{class}",
      "response": "non-persistent://tg/response/text-completion:{class}",
      "parameters": {
        "model": "{model}",
        "temperature": "{temp}"
      }
    }
  },
  "flow": {
    "chunker:{id}": {
      "input": "persistent://tg/flow/chunk:{id}",
      "output": "persistent://tg/flow/chunk-load:{id}",
      "parameters": {
        "chunk_size": "{chunk}",
        "chunk_overlap": 100
      }
    }
  }
}
```

The `parameters` section maps flow-specific parameter names (keys) to parameter metadata objects containing:
- `type`: Reference to centrally-defined parameter definition (e.g., "llm-model")
- `description`: Human-readable description for UI display
- `order`: Display order for parameter forms (lower numbers appear first)

This approach allows:
- Reusable parameter type definitions across multiple flow classes
- Centralized parameter type management and validation
- Flow-specific parameter descriptions and ordering
- Enhanced UI experience with descriptive parameter forms
- Consistent parameter validation across flows
- Easy addition of new standard parameter types

#### Flow Launch Request

The flow launch API accepts parameters using the flow's parameter names:

```json
{
  "flow_class": "document-analysis",
  "flow_id": "customer-A-flow",
  "parameters": {
    "model": "claude-3",
    "size": "12b",
    "temp": 0.5,
    "chunk": 1024
  }
}
```

The system will:
1. Extract parameter metadata from flow class definition
2. Map flow parameter names to their type definitions (e.g., `model` → `llm-model` type)
3. Validate user-provided values against the parameter type definitions
4. Substitute validated values into processor parameters during flow instantiation

### Implementation Details

#### Parameter Resolution Process

1. **Flow Class Loading**: Load flow class and extract parameter metadata
2. **Metadata Extraction**: Extract `type`, `description`, and `order` for each parameter
3. **Type Definition Lookup**: Retrieve parameter type definitions from schema/config store using `type` field
4. **UI Form Generation**: Use `description` and `order` fields to create ordered parameter forms
5. **Validation**: Validate user-provided parameters against type definitions
6. **Default Application**: Apply default values for missing parameters from type definitions
7. **Template Substitution**: Replace parameter placeholders in processor parameters with validated values
8. **Processor Instantiation**: Create processors with substituted parameters

#### Pulsar Integration

1. **Start-Flow Operation**
   - The Pulsar start-flow operation needs to accept a `parameters` field containing a map of parameter values
   - The Pulsar schema for the start-flow request must be updated to include the optional `parameters` field
   - Example request:
   ```json
   {
     "flow_class": "document-analysis",
     "flow_id": "customer-A-flow",
     "parameters": {
       "model": "claude-3",
       "size": "12b",
       "temp": 0.5,
       "chunk": 1024
     }
   }
   ```

2. **Get-Flow Operation**
   - The Pulsar schema for the get-flow response must be updated to include the `parameters` field
   - This allows clients to retrieve the parameter values that were used when the flow was started
   - Example response:
   ```json
   {
     "flow_id": "customer-A-flow",
     "flow_class": "document-analysis",
     "status": "running",
     "parameters": {
       "model": "claude-3",
       "size": "12b",
       "temp": 0.5,
       "chunk": 1024
     }
   }
   ```

#### Config System Integration

3. **Flow Object Storage**
   - When a flow is added to the config system by the flow component in the config manager, the flow object must include the resolved parameter values
   - The config manager needs to store both the original user-provided parameters and the resolved values (with defaults applied)
   - Flow objects in the config system should include:
     - `parameters`: The final resolved parameter values used for the flow

#### CLI Integration

4. **Library CLI Commands**
   - CLI commands that start flows need parameter support:
     - Accept parameter values via command-line flags or configuration files
     - Validate parameters against flow class definitions before submission
     - Support parameter file input (JSON/YAML) for complex parameter sets

   - CLI commands that show flows need to display parameter information:
     - Show parameter values used when the flow was started
     - Display available parameters for a flow class
     - Show parameter validation schemas and defaults

#### Processor Base Class Integration

5. **ParameterSpec Support**
   - Processor base classes need to support parameter substitution through the existing ParametersSpec mechanism
   - The ParametersSpec class (located in the same module as ConsumerSpec and ProducerSpec) should be enhanced if necessary to support parameter template substitution
   - Processors should be able to invoke ParametersSpec to configure their parameters with parameter values resolved at flow launch time
   - The ParametersSpec implementation needs to:
     - Accept parameters configurations that contain parameter placeholders (e.g., `{model}`, `{temperature}`)
     - Support runtime parameter substitution when the processor is instantiated
     - Validate that substituted values match expected types and constraints
     - Provide error handling for missing or invalid parameter references

#### Substitution Rules

- Parameters use the format `{parameter-name}` in processor parameters
- Parameter names in parameters match the keys in the flow's `parameters` section
- Substitution occurs alongside `{id}` and `{class}` replacement
- Invalid parameter references result in launch-time errors
- Type validation happens based on the centrally-stored parameter definition

Example resolution:
```
Flow parameter mapping: "model": "llm-model"
Processor parameter: "model": "{model}"
User provides: "model": "gemma3:8b"
Final parameter: "model": "gemma3:8b"
```

## Testing Strategy

- Unit tests for parameter schema validation
- Integration tests for parameter substitution in processor parameters
- End-to-end tests for launching flows with different parameter values
- UI tests for parameter form generation and validation
- Performance tests for flows with many parameters
- Edge cases: missing parameters, invalid types, undefined parameter references

## Migration Plan

1. The system should continue to support flow classes with no parameters
   declared.
2. The system should continue to support flows no parameters specified:
   This works for flows with no parameters, and flows with parameters
   (they have defaults).

## Open Questions

Q: Should parameters support complex nested objects or keep to simple types?
A: The parameter values will be string encoded, we're probably going to want
   to stick to strings.

Q: Should parameter placeholders be allowed in queue names or only in
   parameters?
A: Only in parameters to remove strange injections and edge-cases.

Q: How to handle conflicts between parameter names and system variables like
   `id` and `class`?
A: It is not valid to specify id and class when launching a flow

Q: Should we support computed parameters (derived from other parameters)?
A: Just string substitution to remove strange injections and edge-cases.

## References

- JSON Schema Specification: https://json-schema.org/
- Flow Class Definition Spec: docs/tech-specs/flow-class-definition.md
