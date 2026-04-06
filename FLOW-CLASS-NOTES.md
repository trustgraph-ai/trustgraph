# Flow Class Architecture Notes

## Overview

Flow Classes define distributed service mesh architectures for TrustGraph dataflow processing. They specify how processors connect through message queues to form complete data processing pipelines.

## Core Concepts

### Service Mesh Graph

Flow Classes describe a **service mesh graph** where:
- **Processors** are nodes that provide and consume services
- **Queues** are the edges that connect processors
- **Queue names** determine connectivity - matching names create connections
- **Template variables** control queue multiplexing strategy

### Service Providers vs Consumers

**Service Providers** implement services by listening to special queue names:
- `input` - receives work/data to process
- `request` - handles request/response patterns (receives requests)
- `response` - sends back responses in request/response patterns

**Service Consumers** use services through all other queue names:
- Any queue name NOT `input`/`request`/`response`
- Represents dependencies on external services
- Send messages TO these queues as clients

### Queue Multiplexing Strategy

**Class Processors** (`{class}` template):
- Use **shared queues** across all flow instances of that class
- One `service-name-{class}` queue serves ALL flows
- Higher throughput, shared resources
- Example: `user-auth-{class}` becomes `user-auth-nlp-chat`

**Flow Processors** (`{id}` template):
- Use **dedicated queues** per individual flow instance
- Each flow gets its own `service-name-{id}` queue
- Isolated processing, per-flow state
- Example: `document-store-{id}` becomes `document-store-flow123`

## Flow Class Structure

```typescript
interface FlowClassDefinition {
  id: string;
  class: {
    [processorName: string]: {
      [queueName: string]: string; // Queue pattern with templates
    };
  };
  flow: {
    [processorName: string]: {
      [queueName: string]: string; // Queue pattern with templates  
    };
  };
  interfaces: {
    [interfaceName: string]: string | {
      request: string;
      response: string;
    };
  };
  description?: string;
  tags?: string[];
}
```

## Service Graph Connections

Connections form when:
1. **Processor A** has queue "service-x" (as consumer)
2. **Processor B** implements "service-x" via `input`/`request`/`response` (as provider)
3. This creates edge: A → B

Example:
```
nlp-processor:
  input: "nlp-service-{class}"     # Provides nlp-service
  
chat-handler:
  nlp: "nlp-service-{class}"       # Consumes nlp-service
```
Result: `chat-handler` → `nlp-processor`

## External API Layer

**Interfaces** define the **external API contract** - how external clients access internal services:

- **Public Service Contract**: External clients call interface endpoints
- **Internal Routing**: Interfaces map to internal queue services
- **Implementation Hiding**: Internal processor topology is hidden from clients

Interface Types:
- **Simple**: `"api-endpoint": "internal-service-name"`
- **Request/Response**: 
  ```json
  {
    "user-api": {
      "request": "user-request-{class}",
      "response": "user-response-{class}"
    }
  }
  ```

## Architecture Layers

```
┌─────────────────────────────────┐
│        External Clients         │
│     (REST, GraphQL, etc.)       │
└─────────────────┬───────────────┘
                  │
┌─────────────────▼───────────────┐
│           Interfaces            │
│      (Public API Contract)      │
└─────────────────┬───────────────┘
                  │
┌─────────────────▼───────────────┐
│      Internal Service Mesh      │
│    (Class + Flow Processors)    │
│   Connected via Queue Names     │
└─────────────────────────────────┘
```

## Key Insights

1. **Class vs Flow is about queue sharing**, not different processor types
2. **Queue names create the service graph** - they're the connection points
3. **Interfaces expose internal services** to external clients
4. **Template variables control multiplexing** - shared vs dedicated queues
5. **Service mesh is unified** - class and flow processors all participate in the same graph