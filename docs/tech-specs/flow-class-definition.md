# Flow Blueprint Definition Specification

## Overview

A flow blueprint defines a complete dataflow pattern template in the TrustGraph system. When instantiated, it creates an interconnected network of processors that handle data ingestion, processing, storage, and querying as a unified system.

## Structure

A flow blueprint definition consists of five main sections:

### 1. Class Section
Defines shared service processors that are instantiated once per flow blueprint. These processors handle requests from all flow instances of this class.

```json
"class": {
  "service-name:{class}": {
    "request": "queue-pattern:{class}",
    "response": "queue-pattern:{class}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Characteristics:**
- Shared across all flow instances of the same class
- Typically expensive or stateless services (LLMs, embedding models)
- Use `{class}` template variable for queue naming
- Settings can be fixed values or parameterized with `{parameter-name}` syntax
- Examples: `embeddings:{class}`, `text-completion:{class}`, `graph-rag:{class}`

### 2. Flow Section
Defines flow-specific processors that are instantiated for each individual flow instance. Each flow gets its own isolated set of these processors.

```json
"flow": {
  "processor-name:{id}": {
    "input": "queue-pattern:{id}",
    "output": "queue-pattern:{id}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Characteristics:**
- Unique instance per flow
- Handle flow-specific data and state
- Use `{id}` template variable for queue naming
- Settings can be fixed values or parameterized with `{parameter-name}` syntax
- Examples: `chunker:{id}`, `pdf-decoder:{id}`, `kg-extract-relationships:{id}`

### 3. Interfaces Section
Defines the entry points and interaction contracts for the flow. These form the API surface for external systems and internal component communication.

Interfaces can take two forms:

**Fire-and-Forget Pattern** (single queue):
```json
"interfaces": {
  "document-load": "persistent://tg/flow/document-load:{id}",
  "triples-store": "persistent://tg/flow/triples-store:{id}"
}
```

**Request/Response Pattern** (object with request/response fields):
```json
"interfaces": {
  "embeddings": {
    "request": "non-persistent://tg/request/embeddings:{class}",
    "response": "non-persistent://tg/response/embeddings:{class}"
  }
}
```

**Types of Interfaces:**
- **Entry Points**: Where external systems inject data (`document-load`, `agent`)
- **Service Interfaces**: Request/response patterns for services (`embeddings`, `text-completion`)
- **Data Interfaces**: Fire-and-forget data flow connection points (`triples-store`, `entity-contexts-load`)

### 4. Parameters Section
Maps flow-specific parameter names to centrally-stored parameter definitions:

```json
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "chunk": "chunk-size"
}
```

**Characteristics:**
- Keys are parameter names used in processor settings (e.g., `{model}`)
- Values reference parameter definitions stored in schema/config
- Enables reuse of common parameter definitions across flows
- Reduces duplication of parameter schemas

### 5. Metadata
Additional information about the flow blueprint:

```json
"description": "Human-readable description",
"tags": ["capability-1", "capability-2"]
```

## Template Variables

### System Variables

#### {id}
- Replaced with the unique flow instance identifier
- Creates isolated resources for each flow
- Example: `flow-123`, `customer-A-flow`

#### {class}
- Replaced with the flow blueprint name
- Creates shared resources across flows of the same class
- Example: `standard-rag`, `enterprise-rag`

### Parameter Variables

#### {parameter-name}
- Custom parameters defined at flow launch time
- Parameter names match keys in the flow's `parameters` section
- Used in processor settings to customize behavior
- Examples: `{model}`, `{temp}`, `{chunk}`
- Replaced with values provided when launching the flow
- Validated against centrally-stored parameter definitions

## Processor Settings

Settings provide configuration values to processors at instantiation time. They can be:

### Fixed Settings
Direct values that don't change:
```json
"settings": {
  "model": "gemma3:12b",
  "temperature": 0.7,
  "max_retries": 3
}
```

### Parameterized Settings
Values that use parameters provided at flow launch:
```json
"settings": {
  "model": "{model}",
  "temperature": "{temp}",
  "endpoint": "https://{region}.api.example.com"
}
```

Parameter names in settings correspond to keys in the flow's `parameters` section.

### Settings Examples

**LLM Processor with Parameters:**
```json
// In parameters section:
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "tokens": "max-tokens",
  "key": "openai-api-key"
}

// In processor definition:
"text-completion:{class}": {
  "request": "non-persistent://tg/request/text-completion:{class}",
  "response": "non-persistent://tg/response/text-completion:{class}",
  "settings": {
    "model": "{model}",
    "temperature": "{temp}",
    "max_tokens": "{tokens}",
    "api_key": "{key}"
  }
}
```

**Chunker with Fixed and Parameterized Settings:**
```json
// In parameters section:
"parameters": {
  "chunk": "chunk-size"
}

// In processor definition:
"chunker:{id}": {
  "input": "persistent://tg/flow/chunk:{id}",
  "output": "persistent://tg/flow/chunk-load:{id}",
  "settings": {
    "chunk_size": "{chunk}",
    "chunk_overlap": 100,
    "encoding": "utf-8"
  }
}
```

## Queue Patterns (Pulsar)

Flow blueprintes use Apache Pulsar for messaging. Queue names follow the Pulsar format:
```
<persistence>://<tenant>/<namespace>/<topic>
```

### Components:
- **persistence**: `persistent` or `non-persistent` (Pulsar persistence mode)
- **tenant**: `tg` for TrustGraph-supplied flow blueprint definitions
- **namespace**: Indicates the messaging pattern
  - `flow`: Fire-and-forget services
  - `request`: Request portion of request/response services
  - `response`: Response portion of request/response services
- **topic**: The specific queue/topic name with template variables

### Persistent Queues
- Pattern: `persistent://tg/flow/<topic>:{id}`
- Used for fire-and-forget services and durable data flow
- Data persists in Pulsar storage across restarts
- Example: `persistent://tg/flow/chunk-load:{id}`

### Non-Persistent Queues
- Pattern: `non-persistent://tg/request/<topic>:{class}` or `non-persistent://tg/response/<topic>:{class}`
- Used for request/response messaging patterns
- Ephemeral, not persisted to disk by Pulsar
- Lower latency, suitable for RPC-style communication
- Example: `non-persistent://tg/request/embeddings:{class}`

## Dataflow Architecture

The flow blueprint creates a unified dataflow where:

1. **Document Processing Pipeline**: Flows from ingestion through transformation to storage
2. **Query Services**: Integrated processors that query the same data stores and services
3. **Shared Services**: Centralized processors that all flows can utilize
4. **Storage Writers**: Persist processed data to appropriate stores

All processors (both `{id}` and `{class}`) work together as a cohesive dataflow graph, not as separate systems.

## Example Flow Instantiation

Given:
- Flow Instance ID: `customer-A-flow`
- Flow Blueprint: `standard-rag`
- Flow parameter mappings:
  - `"model": "llm-model"`
  - `"temp": "temperature"`
  - `"chunk": "chunk-size"`
- User-provided parameters:
  - `model`: `gpt-4`
  - `temp`: `0.5`
  - `chunk`: `512`

Template expansions:
- `persistent://tg/flow/chunk-load:{id}` → `persistent://tg/flow/chunk-load:customer-A-flow`
- `non-persistent://tg/request/embeddings:{class}` → `non-persistent://tg/request/embeddings:standard-rag`
- `"model": "{model}"` → `"model": "gpt-4"`
- `"temperature": "{temp}"` → `"temperature": "0.5"`
- `"chunk_size": "{chunk}"` → `"chunk_size": "512"`

This creates:
- Isolated document processing pipeline for `customer-A-flow`
- Shared embedding service for all `standard-rag` flows
- Complete dataflow from document ingestion through querying
- Processors configured with the provided parameter values

## Benefits

1. **Resource Efficiency**: Expensive services are shared across flows
2. **Flow Isolation**: Each flow has its own data processing pipeline
3. **Scalability**: Can instantiate multiple flows from the same template
4. **Modularity**: Clear separation between shared and flow-specific components
5. **Unified Architecture**: Query and processing are part of the same dataflow