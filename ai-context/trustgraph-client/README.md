# @trustgraph/client

TypeScript/JavaScript client library for TrustGraph WebSocket API. This package provides a framework-agnostic client for communicating with TrustGraph services.

## Features

- 🌐 **WebSocket-based** - Real-time communication with TrustGraph services
- 📦 **Zero Dependencies** - No external runtime dependencies
- 🔐 **Authentication Support** - Optional API key authentication
- 🔄 **Auto-reconnection** - Handles connection failures gracefully
- 📝 **Full TypeScript Support** - Complete type definitions
- 🎯 **Framework Agnostic** - Works with any JavaScript framework or vanilla JS

## Installation

```bash
npm install @trustgraph/client
```

## Quick Start

```typescript
import { createTrustGraphSocket } from "@trustgraph/client";

// Create a socket connection
const socket = createTrustGraphSocket("your-username");

// Query triples from the knowledge graph
const triples = await socket.triplesQuery(
  { v: "http://example.org/subject", e: true },
  { v: "http://example.org/predicate", e: true },
  undefined,
  10, // limit
);

console.log(triples);
```

## With Authentication

```typescript
const socket = createTrustGraphSocket("your-username", "your-api-key");
```

## Core APIs

### Knowledge Graph Operations

**Query Triples**

```typescript
const triples = await socket.triplesQuery(
  subject?: Value,    // Optional subject filter
  predicate?: Value,  // Optional predicate filter
  object?: Value,     // Optional object filter
  limit: number,      // Maximum results
  collection?: string // Optional collection name
);
```

**Graph Embeddings Query**

```typescript
const entities = await socket.graphEmbeddingsQuery(
  vectors: number[][],  // Embedding vectors
  limit: number,        // Maximum results
  collection?: string   // Optional collection name
);
```

### Text & LLM Operations

**Text Completion**

```typescript
const response = await socket.textCompletion(
  system: string,    // System prompt
  prompt: string,    // User prompt
  temperature?: number
);
```

**Graph RAG**

```typescript
const answer = await socket.graphRag(
  query: string,
  options?: {
    'entity-limit'?: number,
    'triple-limit'?: number,
    'max-subgraph-size'?: number,
    'max-path-length'?: number
  },
  collection?: string
);
```

**Agent**

```typescript
socket.agent(
  question: string,
  think: (thought: string) => void,      // Called when agent is thinking
  observe: (observation: string) => void, // Called on observations
  answer: (answer: string) => void,      // Called with final answer
  error: (error: string) => void,        // Called on errors
  collection?: string
);
```

**Embeddings**

```typescript
const vectors = await socket.embeddings(text: string);
```

### Document Operations

**Load Document**

```typescript
await socket.loadDocument(
  id: string,           // Document ID
  data: string,         // Base64-encoded document
  metadata: Triple[],   // Document metadata as triples
  collection?: string
);
```

**Load Text**

```typescript
await socket.loadText(
  id: string,           // Document ID
  text: string,         // Plain text content
  charset: string,      // Character encoding (e.g., 'utf-8')
  metadata: Triple[],   // Document metadata as triples
  collection?: string
);
```

### Library Operations

**List Documents**

```typescript
const docs = await socket.library.listDocuments(
  user?: string,
  collection?: string
);
```

**Get Document**

```typescript
const doc = await socket.library.getDocument(
  id: string,
  user?: string,
  collection?: string
);
```

**Delete Document**

```typescript
await socket.library.deleteDocument(
  id: string,
  user?: string,
  collection?: string
);
```

### Flow Operations

Flows represent processing pipelines for documents and queries.

**Create Flow API**

```typescript
const flowApi = socket.flow("flow-id");
// flowApi has same methods as socket but scoped to this flow
```

**Start Flow**

```typescript
await socket.flows.startFlow(
  flowId: string,
  className: string,
  description: string
);
```

**Stop Flow**

```typescript
await socket.flows.stopFlow(flowId: string);
```

**List Flows**

```typescript
const flowIds = await socket.flows.getFlows();
```

**Get Flow Definition**

```typescript
const flowDef = await socket.flows.getFlow(flowId: string);
```

**List Flow Classes**

```typescript
const classes = await socket.flows.getFlowClasses();
```

**Get Flow Class**

```typescript
const classDef = await socket.flows.getFlowClass(className: string);
```

## Connection State Monitoring

```typescript
// Subscribe to connection state changes
const unsubscribe = socket.onConnectionStateChange((state) => {
  console.log("Status:", state.status); // 'connecting' | 'connected' | 'authenticated' | 'disconnected' | 'error'
  console.log("Authenticated:", state.authenticated);
  console.log("Error:", state.error);
});

// Unsubscribe when done
unsubscribe();
```

## Data Types

### Value

Represents a subject, predicate, or object in a triple:

```typescript
interface Value {
  v: string; // Value (URI or literal)
  e: boolean; // Is entity (true) or literal (false)
  label?: string; // Optional human-readable label
}
```

### Triple

Represents a subject-predicate-object relationship:

```typescript
interface Triple {
  s: Value; // Subject
  p: Value; // Predicate
  o: Value; // Object
}
```

## Advanced Usage

### Custom Timeout and Retries

Most methods accept optional timeout and retry parameters:

```typescript
await socket.triplesQuery(
  subject,
  predicate,
  object,
  limit,
  collection,
  30000, // timeout in ms
  5, // retry attempts
);
```

### Closing the Connection

```typescript
socket.close();
```

## Error Handling

All async methods return Promises that reject on error:

```typescript
try {
  const result = await socket.triplesQuery(...);
} catch (error) {
  console.error('Query failed:', error);
}
```

## React Integration

For React applications, use the companion package:

```bash
npm install @trustgraph/react-provider
```

See [@trustgraph/react-provider](https://github.com/trustgraph-ai/trustgraph-client) for React-specific hooks and providers.

## API Reference

Full API documentation is available in the TypeScript definitions. Your IDE will provide autocomplete and inline documentation for all methods.

## License

Apache 2.0

(c) KnowNext Inc., KnowNext Limited 2025

