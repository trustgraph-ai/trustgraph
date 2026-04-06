# Flow Class Definition Specification

## Overview

A flow class defines a complete dataflow pattern template in the TrustGraph system. When instantiated, it creates an interconnected network of processors that handle data ingestion, processing, storage, and querying as a unified system.

## Structure

A flow class definition consists of four main sections:

### 1. Class Section
Defines shared service processors that are instantiated once per flow class. These processors handle requests from all flow instances of this class.

```json
"class": {
  "service-name:{class}": {
    "request": "queue-pattern:{class}",
    "response": "queue-pattern:{class}"
  }
}
```

**Characteristics:**
- Shared across all flow instances of the same class
- Typically expensive or stateless services (LLMs, embedding models)
- Use `{class}` template variable for queue naming
- Examples: `embeddings:{class}`, `text-completion:{class}`, `graph-rag:{class}`

### 2. Flow Section
Defines flow-specific processors that are instantiated for each individual flow instance. Each flow gets its own isolated set of these processors.

```json
"flow": {
  "processor-name:{id}": {
    "input": "queue-pattern:{id}",
    "output": "queue-pattern:{id}"
  }
}
```

**Characteristics:**
- Unique instance per flow
- Handle flow-specific data and state
- Use `{id}` template variable for queue naming
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

### 4. Metadata
Additional information about the flow class:

```json
"description": "Human-readable description",
"tags": ["capability-1", "capability-2"]
```

## Template Variables

### {id}
- Replaced with the unique flow instance identifier
- Creates isolated resources for each flow
- Example: `flow-123`, `customer-A-flow`

### {class}
- Replaced with the flow class name
- Creates shared resources across flows of the same class
- Example: `standard-rag`, `enterprise-rag`

## Queue Patterns (Pulsar)

Flow classes use Apache Pulsar for messaging. Queue names follow the Pulsar format:
```
<persistence>://<tenant>/<namespace>/<topic>
```

### Components:
- **persistence**: `persistent` or `non-persistent` (Pulsar persistence mode)
- **tenant**: `tg` for TrustGraph-supplied flow class definitions
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

The flow class creates a unified dataflow where:

1. **Document Processing Pipeline**: Flows from ingestion through transformation to storage
2. **Query Services**: Integrated processors that query the same data stores and services
3. **Shared Services**: Centralized processors that all flows can utilize
4. **Storage Writers**: Persist processed data to appropriate stores

All processors (both `{id}` and `{class}`) work together as a cohesive dataflow graph, not as separate systems.

## Example Flow Instantiation

Given:
- Flow Instance ID: `customer-A-flow`
- Flow Class: `standard-rag`

Template expansions:
- `persistent://tg/flow/chunk-load:{id}` → `persistent://tg/flow/chunk-load:customer-A-flow`
- `non-persistent://tg/request/embeddings:{class}` → `non-persistent://tg/request/embeddings:standard-rag`

This creates:
- Isolated document processing pipeline for `customer-A-flow`
- Shared embedding service for all `standard-rag` flows
- Complete dataflow from document ingestion through querying

## Benefits

1. **Resource Efficiency**: Expensive services are shared across flows
2. **Flow Isolation**: Each flow has its own data processing pipeline
3. **Scalability**: Can instantiate multiple flows from the same template
4. **Modularity**: Clear separation between shared and flow-specific components
5. **Unified Architecture**: Query and processing are part of the same dataflow