# WebSocket Streaming Message Patterns

This document describes streaming behavior for TrustGraph WebSocket services.

## Overview

Many TrustGraph services support streaming responses, where a single request results in multiple response messages sent progressively over time. This enables:
- Real-time output as it's generated
- Lower latency for first results
- Progressive UI updates
- Better user experience for long-running operations

## Streaming Protocol

### Request ID Correlation

All streaming responses for a request share the same `id`:

```json
// Single request
{"id": "req-1", "service": "agent", "flow": "my-flow", "request": {...}}

// Multiple responses with same id
{"id": "req-1", "response": {...}}  // First chunk
{"id": "req-1", "response": {...}}  // Second chunk
{"id": "req-1", "response": {...}}  // Final chunk
```

### Completion Indicators

Services use different fields to indicate the final message:

| Service | Completion Field | Final Value |
|---------|-----------------|-------------|
| agent | `end-of-dialog` | `true` |
| document-rag | `end-of-stream` | `true` |
| graph-rag | `end-of-stream` | `true` |
| text-completion | `end-of-stream` | `true` |
| prompt | `end-of-stream` | `true` |

## Streaming Services

### Agent Service

Agent service streams thought processes, actions, observations, and answers:

```json
// Request
{
  "id": "agent-1",
  "service": "agent",
  "flow": "my-flow",
  "request": {
    "question": "What is quantum computing?",
    "streaming": true
  }
}

// Response stream
{
  "id": "agent-1",
  "response": {
    "chunk-type": "thought",
    "content": "I need to explain quantum computing concepts",
    "end-of-dialog": false
  }
}

{
  "id": "agent-1",
  "response": {
    "chunk-type": "answer",
    "content": "Quantum computing is a type of computing that uses quantum mechanical phenomena...",
    "end-of-dialog": false
  }
}

{
  "id": "agent-1",
  "response": {
    "chunk-type": "answer",
    "content": "Key principles include superposition and entanglement.",
    "end-of-dialog": true
  }
}
```

**Chunk Types**:
- `thought`: Internal reasoning
- `action`: Tool/action being invoked
- `observation`: Result from tool/action
- `answer`: Final answer content

### Document RAG Service

Document RAG streams answer chunks:

```json
// Request
{
  "id": "rag-1",
  "service": "document-rag",
  "flow": "my-flow",
  "request": {
    "query": "What are the main features?",
    "streaming": true,
    "doc-limit": 20
  }
}

// Response stream
{
  "id": "rag-1",
  "response": {
    "content": "The main features include: 1) ",
    "end-of-stream": false
  }
}

{
  "id": "rag-1",
  "response": {
    "content": "Knowledge graph storage, 2) Vector embeddings, ",
    "end-of-stream": false
  }
}

{
  "id": "rag-1",
  "response": {
    "content": "3) RAG capabilities.",
    "end-of-stream": true
  }
}
```

### Graph RAG Service

Similar to Document RAG but retrieves from knowledge graph:

```json
{
  "id": "graph-rag-1",
  "service": "graph-rag",
  "flow": "my-flow",
  "request": {
    "query": "What entities are related to quantum computing?",
    "streaming": true,
    "triple-limit": 100
  }
}
```

Response stream has same structure as Document RAG.

### Text Completion Service

Streams generated text:

```json
{
  "id": "complete-1",
  "service": "text-completion",
  "flow": "my-flow",
  "request": {
    "prompt": "Once upon a time",
    "streaming": true,
    "max-output-tokens": 100
  }
}

// Response stream
{
  "id": "complete-1",
  "response": {
    "content": " there was a ",
    "end-of-stream": false
  }
}

{
  "id": "complete-1",
  "response": {
    "content": "kingdom far away...",
    "end-of-stream": true
  }
}
```

### Prompt Service

Streams prompt expansion/generation:

```json
{
  "id": "prompt-1",
  "service": "prompt",
  "flow": "my-flow",
  "request": {
    "template": "default-template",
    "variables": {"topic": "quantum"},
    "streaming": true
  }
}
```

Response stream contains progressive prompt text.

## Non-Streaming Services

These services return a single response message:

- **config**: Configuration operations
- **flow**: Flow lifecycle management
- **librarian**: Library operations
- **knowledge**: Knowledge graph operations
- **collection-management**: Collection metadata
- **embeddings**: Generate embeddings
- **mcp-tool**: Tool invocation
- **triples**: Triple pattern queries
- **objects**: GraphQL queries
- **nlp-query**: NLP-based queries
- **structured-query**: Structured queries
- **structured-diag**: Diagnostics
- **graph-embeddings**: Embedding-based graph search
- **document-embeddings**: Embedding-based document search
- **text-load**: Text loading (returns status)
- **document-load**: Document loading (returns status)

## Client Implementation Guide

### Basic Streaming Handler

```javascript
const pendingRequests = new Map();

// Send request
const requestId = generateUniqueId();
const request = {
  id: requestId,
  service: 'agent',
  flow: 'my-flow',
  request: {
    question: 'What is quantum computing?',
    streaming: true
  }
};

pendingRequests.set(requestId, {
  chunks: [],
  complete: false
});

websocket.send(JSON.stringify(request));

// Handle responses
websocket.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.error) {
    // Handle error
    console.error(`Request ${message.id} failed:`, message.error);
    pendingRequests.delete(message.id);
    return;
  }

  const pending = pendingRequests.get(message.id);
  if (!pending) {
    console.warn(`Unexpected response for ${message.id}`);
    return;
  }

  // Accumulate chunk
  pending.chunks.push(message.response);

  // Check if complete
  const isComplete =
    message.response['end-of-stream'] === true ||
    message.response['end-of-dialog'] === true;

  if (isComplete) {
    pending.complete = true;
    console.log(`Request ${message.id} complete:`, pending.chunks);
    pendingRequests.delete(message.id);
  } else {
    // Process intermediate chunk
    console.log(`Chunk for ${message.id}:`, message.response);
  }
};
```

## Error Handling in Streaming

Errors can occur at any point during streaming:

```json
// Mid-stream error
{
  "id": "req-1",
  "response": {
    "chunk-type": "thought",
    "content": "Processing...",
    "end-of-dialog": false
  }
}

// Error interrupts stream
{
  "id": "req-1",
  "error": {
    "type": "service-error",
    "message": "Backend timeout"
  }
}
```

When an error occurs, no further response messages will be sent for that request ID. The client should:
1. Stop waiting for completion
2. Handle the partial results appropriately
3. Clean up request state

## Performance Considerations

### Multiplexing Streaming Requests

Multiple streaming requests can be active simultaneously:

```json
{"id": "req-1", "service": "agent", ...}
{"id": "req-2", "service": "document-rag", ...}
{"id": "req-3", "service": "text-completion", ...}

// Responses may interleave
{"id": "req-2", "response": {...}}
{"id": "req-1", "response": {...}}
{"id": "req-3", "response": {...}}
{"id": "req-1", "response": {...}}
{"id": "req-2", "response": {...}}
```

### Backpressure

If the client is slow to consume streaming responses, the WebSocket connection may experience:
- Buffering on the server side
- Increased latency
- Potential connection issues

Clients should process streaming chunks efficiently or implement flow control.

## Best Practices

1. **Always check completion flags**: Don't assume a fixed number of chunks
2. **Handle partial results**: Be prepared for errors mid-stream
3. **Unique request IDs**: Ensure IDs are unique across active requests
4. **Timeout handling**: Implement client-side timeouts for streaming requests
5. **Memory management**: Don't accumulate unbounded chunks; process incrementally
6. **User feedback**: Show progressive results to users as chunks arrive
