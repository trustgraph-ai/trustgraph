# TrustGraph Configuration Templates

TrustGraph configurator is a Python-based tool that generates deployment configurations for TrustGraph AI systems. It supports multiple deployment platforms and provides templated configurations with versioning support.

## Overview

The configurator uses Jsonnet templates to generate deployment configurations for various platforms including Docker Compose, Podman, and multiple Kubernetes environments. It packages the generated configurations into ZIP files containing all necessary deployment resources.

## Configuration Process

The TrustGraph configuration system uses a multi-stage pipeline to generate deployment packages:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Dialog Flow    │     │    JSONata      │     │  Configuration  │     │   Deployment    │
│  Configuration  │────▶│    Transform    │────▶│     Service     │────▶│    Package      │
│                 │     │                 │     │                 │     │                 │
│ (state object)  │     │ (config object) │     │   (templates)   │     │   (ZIP file)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
        │
        │               ┌─────────────────┐     ┌─────────────────┐
        └──────────────▶│  Documentation  │────▶│  Installation   │
                        │     Flow        │     │     Guide       │
                        └─────────────────┘     └─────────────────┘
```

### 1. Dialog Flow Configuration

The dialog flow file (`trustgraph-flow.yaml`) describes configuration steps in a technology-neutral way. A UI wizard walks users through these steps, collecting choices about platform, model provider, storage backends, and features. The output is a **state object** - a simple key/value map representing all user selections.

### 2. JSONata Transform

The JSONata transform file (`trustgraph-output.jsonata`) converts the state object into a **configuration object**. This object understands how to invoke TrustGraph templates and contains the structured parameters needed by the template system.

### 3. Configuration Service

The configuration service receives the configuration object, invokes the appropriate Jsonnet templates, and runs the package builder. The output is a **deployment package** - a ZIP file containing all deployment resources (docker-compose.yaml or Kubernetes manifests, plus supporting files).

### 4. Documentation Flow

The original state object can also be used with the documentation manifest (`trustgraph-docs.yaml`) to generate a customised **installation guide** based on the user's specific configuration choices.

## Installation

The configurator is distributed as a Python package. To use it:

```bash
export PYTHONPATH=.
# or install the package
pip install -e .
```

## Usage

### List Available Configurations

To see all available templates and platforms:

```bash
tg-show-config-params
```

This will display:
- Available platforms (docker-compose, podman-compose, various Kubernetes options)
- Available templates with versions and stability status
- Latest version and latest stable version

### Generate Configuration

To generate a configuration package:

```bash
scripts/tg-build-deployment --template <template-name> --version <version> \
    --input config.json --output output.zip --platform <platform>
```

Example:
```bash
scripts/tg-build-deployment --template 1.1 --version 1.1.9 \
    --input config.json --output deployment.zip --platform docker-compose
```

#### Output to stdout

To output only the TrustGraph configuration:
```bash
scripts/tg-build-deployment --template 1.1 --latest-stable \
    --input config.json -O > trustgraph-config.json
```

To output only the platform resources (docker-compose.yaml or resources.yaml):
```bash
# For Docker Compose
scripts/tg-build-deployment --template 1.1 --latest-stable \
    --input config.json --platform docker-compose -R > docker-compose.yaml

# For Kubernetes
scripts/tg-build-deployment --template 1.1 --latest-stable \
    --input config.json --platform gcp-k8s -R > resources.yaml
```

### Configuration Service API

You can also run the configurator as a REST API service:

```bash
scripts/tg-config-svc
```

This starts a web service on port 8080 that provides:
- REST API endpoints for configuration generation
- Programmatic access to version information
- Web-based configuration generation

The service provides the same functionality as the command-line tool but through HTTP endpoints (see API Service section below for details).

### Command Line Options

- `-i, --input`: Input configuration file (default: config.json)
- `-o, --output`: Output ZIP file (default: output.zip)
- `-t, --template`: Template name (e.g., "1.1", "1.0", "0.23")
- `-v, --version`: Specific version to use
- `-p, --platform`: Target platform (default: docker-compose)
- `--latest`: Use the latest available version
- `--latest-stable`: Use the latest stable version
- `-O, --output-tg-config`: Output only TrustGraph configuration to stdout (no ZIP file)
- `-R, --output-resources`: Output only platform resources (docker-compose.yaml or resources.yaml) to stdout (no ZIP file)

### Available Platforms

- `docker-compose`: Local Docker deployment using docker-compose
- `podman-compose`: Local Podman deployment using podman-compose
- `minikube-k8s`: Minikube Kubernetes cluster
- `gcp-k8s`: Google Cloud Kubernetes (GKE)
- `aks-k8s`: Azure Kubernetes Service (AKS)
- `eks-k8s`: AWS Elastic Kubernetes Service (EKS)
- `scw-k8s`: Scaleway Kubernetes

## Python Architecture

### Module Structure

The `trustgraph_configurator` package consists of several key modules:

#### Core Modules

1. **generator.py** (`Generator` class)
   - Processes Jsonnet templates using the `_jsonnet` library
   - Evaluates configuration snippets with custom import callbacks
   - Returns processed JSON configurations

2. **packager.py** (`Packager` class)
   - Main orchestrator for configuration generation
   - Handles template and resource file loading
   - Generates platform-specific deployment packages
   - Creates ZIP archives with all necessary files
   - Supports both Docker Compose and Kubernetes outputs

3. **index.py** (`Index` class)
   - Manages template and platform metadata
   - Reads from `templates/index.json`
   - Provides version sorting and comparison
   - Offers methods to get latest/stable versions

4. **api.py** (`Api` class)
   - REST API service for configuration generation
   - Endpoints for version information and generation
   - Validates input JSON before processing
   - Returns generated configurations as binary data

5. **service.py**
   - Simple wrapper to run the API service
   - Configures logging and starts the web server on port 8080

6. **run.py**
   - Command-line interface implementation
   - Argument parsing and validation
   - Reads input configuration and writes output ZIP

7. **list.py**
   - Command-line tool to list available configurations
   - Displays platforms, templates, and versions in tabular format

### How Components Interact

```
User Input (config.json) 
    ↓
run.py (CLI) or api.py (REST)
    ↓
Packager (orchestrator)
    ├─→ Index (metadata/versions)
    ├─→ Generator (Jsonnet processing)
    └─→ Resource files (templates/)
         ↓
    Platform-specific generation
    (Docker Compose or Kubernetes)
         ↓
    ZIP archive (output.zip)
```

### Key Design Patterns

1. **Template Resolution**: The `Packager.fetch()` method implements a sophisticated file resolution system:
   - Special handling for `trustgraph/config.json` and `version.jsonnet`
   - Fallback search paths for templates and resources
   - Version-specific template directories

2. **Platform Abstraction**: Different platforms are handled through:
   - Platform-specific Jsonnet templates (e.g., `config-to-docker-compose.jsonnet`)
   - Conditional logic in `Packager.generate()`
   - Unified output format (ZIP archives)

3. **Version Management**: The system supports:
   - Multiple template versions with different features
   - Stability levels (alpha, beta, stable)
   - Automatic version selection (latest/latest-stable)

### Configuration Flow

1. User provides a JSON configuration file
2. Packager validates and loads the appropriate template version
3. Generator processes Jsonnet templates with the configuration
4. Platform-specific resources are added (Grafana dashboards, Prometheus config)
5. Everything is packaged into a ZIP file for deployment

### API Service

The REST API service (`tg-config-svc`) provides programmatic access to the configurator functionality. Start the service with:

```bash
scripts/tg-config-svc
```

The service runs on port 8080 and provides the following endpoints:

```
POST /api/generate/{platform}/{template}  # Generate configuration
GET /api/latest                          # Get latest version info
GET /api/latest-stable                   # Get latest stable version info
GET /api/versions                        # List all available versions
```

#### Dialog Flow Resources

These endpoints serve the dialog flow resources described in the Configuration Process section:

```
GET /api/dialog-flow     # Dialog flow state machine (YAML)
GET /api/config-prepare  # JSONata transform for config preparation
GET /api/docs-manifest   # Documentation manifest (YAML)
GET /api/docs/{path}     # Documentation markdown fragments
```

Example usage:
```bash
# Generate configuration via API
curl -X POST http://localhost:8080/api/generate/docker-compose/1.1 \
  -H "Content-Type: application/json" \
  -d @config.json \
  --output deployment.zip

# Fetch dialog flow configuration
curl http://localhost:8080/api/dialog-flow

# Fetch a documentation fragment
curl http://localhost:8080/api/docs/platform/docker-compose.md
```

## Output Structure

### Docker Compose Output

The generated ZIP file contains:
```
docker-compose.yaml      # Main deployment file
trustgraph/config.json   # TrustGraph configuration
grafana/                 # Grafana dashboards and provisioning
prometheus/              # Prometheus configuration
```

### Kubernetes Output

The generated ZIP file contains:
```
resources.yaml          # All Kubernetes resources in a single file
```

## Development

To extend or modify the configurator:

1. Templates are in `trustgraph_configurator/templates/<version>/`
2. Add new platforms by creating appropriate Jsonnet templates
3. Update `templates/index.json` for new versions
4. Resources (dashboards, configs) go in `trustgraph_configurator/resources/<version>/`
5. Dialog flow resources are in `trustgraph_configurator/resources/dialog/`:
   - `trustgraph-flow.yaml` - Dialog flow state machine
   - `trustgraph-output.jsonata` - State-to-config transform
   - `trustgraph-docs.yaml` - Documentation manifest
   - `docs/` - Markdown documentation fragments

## Error Handling

The configurator includes error handling for:
- Missing or invalid templates
- Malformed input JSON
- File resolution failures
- Platform-specific generation errors

Errors are logged with appropriate context for debugging.
