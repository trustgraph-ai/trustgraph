# How TrustGraph Templates Are Structured

## Overview

The TrustGraph template system is a Jsonnet-based configuration framework that generates deployment configurations for multiple platforms (Docker Compose, Kubernetes, etc.) from a single JSON configuration file. The system uses a component-based architecture with abstraction layers for different deployment targets.

## Directory Structure

```
trustgraph_configurator/
├── packager.py              # Main entry point
├── generator.py             # Jsonnet processor wrapper
├── templates/
│   └── 1.3/                 # Template version
│       ├── components.jsonnet           # Component registry
│       ├── config-to-docker-compose.jsonnet  # Docker Compose generator
│       ├── config-to-tg-configuration.jsonnet # TrustGraph config extractor
│       ├── components/      # Component definitions
│       ├── engine/          # Platform-specific engines
│       ├── util/            # Utility functions
│       ├── prompts/         # LLM prompt templates
│       └── values/          # Shared configuration values
└── resources/
    └── 1.3/                 # Static resource files
        ├── grafana/         # Grafana dashboards/configs
        └── prometheus/      # Prometheus configs
```

## Core Concepts

### 1. Components

Components are the building blocks of the system. Each component:
- Defines configuration parameters with defaults
- Implements a `create` function that generates platform-specific resources
- Can compose with other components through Jsonnet's object composition (`+`)
- Lives in `components/` directory

Example component structure (simplified `ollama.jsonnet`):
```jsonnet
{
    // Parameter with default value
    "ollama-model":: "gemma2:9b",
    
    // Service definition
    "text-completion" +: {
        create:: function(engine)
            // Use engine abstraction to create resources
            local container = engine.container("text-completion")
                .with_image(...)
                .with_command([...]);
            
            engine.resources([container, ...])
    },
    
    // Custom parameter setter
    with:: function(key, value)
        self + { ["ollama-" + key]:: value }
}
```

### 2. Engines

Engines provide platform-specific implementations for resource creation. Each engine implements:
- `container()` - Create container definitions
- `service()` - Create service definitions  
- `volume()` - Create volume definitions
- `resources()` - Aggregate resources for output

The engine abstraction allows components to be platform-agnostic. Available engines:
- `docker-compose.jsonnet` - Docker Compose format
- `noop.jsonnet` - No-op engine for configuration extraction only
- Kubernetes engines (various cloud providers)

### 3. Configuration Flow

```
config.json → decode → patterns → engine.create() → resources → output
```

1. **Input**: `config.json` contains a list of components to enable:
```json
[
    {"name": "trustgraph-base", "parameters": {}},
    {"name": "ollama", "parameters": {"model": "mixtral"}}
]
```

2. **Decode**: The `decode-config.jsonnet` utility:
   - Loads each component from the registry
   - Applies parameters using the `with_params` function
   - Merges all components into a single "patterns" object

3. **Engine Processing**: Platform-specific files like `config-to-docker-compose.jsonnet`:
   - Call each component's `create(engine)` function
   - Fold results into final resource structure
   - Output platform-specific configuration

### 4. Configuration Extraction

The `config-to-tg-configuration.jsonnet` file extracts the TrustGraph runtime configuration from components. This includes:
- Prompt templates
- Flow definitions
- Model token costs
- Agent tools
- MCP server configurations

This configuration is embedded into the deployment separately from the infrastructure resources.

## Processing Pipeline

### Entry Point: `packager.py`

The Packager class orchestrates the entire process:

1. **Template Selection**: Determines version and template based on user input
2. **Resource Generation**: 
   - For Docker Compose: Calls `config-to-docker-compose.jsonnet`
   - For Kubernetes: Calls `config-to-<platform>-k8s.jsonnet`
3. **Configuration Generation**: Calls `config-to-tg-configuration.jsonnet` for runtime config
4. **Packaging**: Creates ZIP file with all generated files and static resources

### Jsonnet Processing: `generator.py`

Simple wrapper around the Jsonnet library that:
- Evaluates Jsonnet templates
- Provides custom import callback for file resolution
- Returns parsed JSON output

## Component Composition

Components can be composed in several ways:

### 1. Base Component Extension
Many components extend `trustgraph-base` which provides core services:
```jsonnet
local trustgraph = import "components/trustgraph.jsonnet";
// Inherits all trustgraph services
{} + trustgraph + myCustomizations
```

### 2. Field Merging
Components use `+:` to merge with existing fields:
```jsonnet
"text-completion" +: {
    // Adds to existing text-completion definition
    create:: function(engine) ...
}
```

### 3. Parameter Injection
The `with` pattern allows runtime parameter injection:
```jsonnet
with:: function(key, value)
    self + { [key]:: value }
```

## Hidden Fields and Configuration

Jsonnet's `::` operator creates hidden fields that aren't included in JSON output by default. The template system uses this for:
- Default values that can be overridden
- Internal helper functions
- Configuration that needs special extraction

For example, `trustgraph-base` has a hidden `configuration::` field containing runtime config that's extracted separately by `config-to-tg-configuration.jsonnet`.

## Platform Abstraction

The engine pattern provides clean separation between:
- **Component logic** - What services/containers to create
- **Platform specifics** - How to represent them (Docker Compose YAML, K8s manifests, etc.)

This allows the same component definitions to generate configurations for multiple platforms without modification.

## Static Resources

Files in `resources/` are copied directly to the output package. These include:
- Grafana dashboard definitions
- Prometheus configuration
- Other platform-specific configs that don't need templating

## Best Practices

1. **Component Independence**: Components should be self-contained and not depend on specific ordering
2. **Parameter Namespacing**: Use prefixes (e.g., `ollama-model`) to avoid conflicts
3. **Hidden Fields for Defaults**: Use `::` for overridable defaults
4. **Engine Abstraction**: Always use engine methods rather than creating platform-specific structures directly
5. **Composition Over Inheritance**: Use Jsonnet's object composition (`+`) rather than complex inheritance hierarchies