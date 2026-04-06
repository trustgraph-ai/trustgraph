# Streaming Support for TrustGraph Client

**Status**: Draft for Review
**Author**: Claude
**Date**: 2025-11-27
**Version**: 1.0

## Executive Summary

Extend the TrustGraph TypeScript client to support streaming responses for Graph RAG, Document RAG, Text Completion, and Prompt services. The client already has streaming infrastructure (`ServiceCallMulti`) used by Agent, but the other services only support single-response mode. This spec proposes minimal changes to enable streaming across all services while maintaining backward compatibility.

## Background

### Current State

The client has **two request patterns**:

1. **Single-response** (`makeRequest` → `ServiceCall`)
   - Used by: text-completion, graph-rag, document-rag, prompt, and most other services
   - Returns Promise that resolves with single response
   - Example: `graphRag(text: string): Promise<string>`

2. **Multi-response** (`makeRequestMulti` → `ServiceCallMulti`)
   - Used by: agent (thoughts/observations/answer), knowledge.getKgCore (large graph streaming)
   - Accepts `receiver: (resp: unknown) => boolean` callback
   - Receiver returns `true` to signal end-of-stream
   - Example: `agent(question, think, observe, answer, error): void`

### Backend Streaming Protocol

Per `STREAMING-IMPLEMENTATION-NOTES.txt`, the backend supports streaming when `streaming: true` is added to requests:

**Graph RAG / Document RAG**:
- Chunks arrive with `chunk` field
- Final chunk has `end_of_stream: true`

**Text Completion**:
- Chunks arrive with `response` field
- Final chunk has `end_of_stream: true`

**Prompt**:
- Chunks arrive with `text` field
- Final chunk has `end_of_stream: true`

**Agent** (already implemented):
- Multiple messages with `chunk_type` (thought/observation/final-answer)
- Final chunk has `end_of_dialog: true`

## Problem Statement

**Primary Issue**: Users who want streaming responses for Graph RAG, Document RAG, Text Completion, or Prompt services must:
1. Drop down to `makeRequestMulti` and handle raw responses
2. Manually parse `chunk`/`response`/`text` fields
3. Check `end_of_stream` flag
4. Handle errors mid-stream

**Secondary Issue**: The Agent API doesn't correctly implement the backend streaming protocol. The backend sends:
```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search", end_of_message: false, end_of_dialog: false}
```

But the client expects:
```
{thought?: string, observation?: string, answer?: string}
```

The Agent implementation needs to be updated to handle incremental chunks with completion flags.

## Goals

1. **Fix Agent API** to correctly implement backend streaming protocol with chunk-level callbacks
2. **Add streaming variants** for text-completion, graph-rag, document-rag, and prompt services
3. **Maintain backward compatibility** - existing non-streaming APIs unchanged (except Agent which needs fixing)
4. **Policy-free implementation** - no state management (accumulation, buffering, etc.) in client layer
5. **Minimal callback interface** - single receiver callback with chunk and completion flag
6. **Minimal type changes** - reuse existing request/response types where possible

## Non-Goals

- Changing the existing non-streaming APIs
- Supporting streaming for services that don't stream (embeddings, triples, etc.)
- Implementing state management (accumulation, buffering) - that belongs in higher layers
- Changing the underlying `ServiceCallMulti` implementation

## Design

### 1. Type Additions

Add streaming-specific response types to `src/models/messages.ts`:

```typescript
// Agent streaming response (NEW - replaces old AgentResponse for streaming)
export interface AgentStreamingResponse {
  chunk_type?: "thought" | "action" | "observation" | "final-answer" | "error";
  content?: string;
  end_of_message?: boolean;  // Current chunk type is complete
  end_of_dialog?: boolean;   // Entire agent dialog is complete

  // Legacy fields for backward compatibility with non-streaming
  thought?: string;
  observation?: string;
  answer?: string;
  error?: string;
}

// Generic streaming response wrapper for RAG/completion services
export interface StreamingChunk {
  chunk?: string;      // Graph RAG, Document RAG
  response?: string;   // Text Completion
  text?: string;       // Prompt
  end_of_stream?: boolean;
  error?: {
    message: string;
    type?: string;
  };
}

// Request types get optional streaming flag
export interface AgentRequest {
  question: string;
  user?: string;
  streaming?: boolean;  // NEW - enable streaming mode
}

export interface GraphRagRequest {
  query: string;
  user?: string;
  collection?: string;
  "entity-limit"?: number;
  "triple-limit"?: number;
  "max-subgraph-size"?: number;
  "max-path-length"?: number;
  streaming?: boolean;  // NEW
}

export interface DocumentRagRequest {
  query: string;
  user?: string;
  collection?: string;
  "doc-limit"?: number;
  streaming?: boolean;  // NEW
}

export interface TextCompletionRequest {
  system: string;
  prompt: string;
  streaming?: boolean;  // NEW
}

export interface PromptRequest {
  id: string;
  terms: Record<string, unknown>;
  streaming?: boolean;  // NEW
}

export interface PromptResponse {
  text: string;
}
```

### 2. BaseApi Additions

No changes needed to `BaseApi` - `makeRequestMulti` already exists.

### 3. FlowApi Changes

#### 3.1 Fix Agent Method

Update the existing `agent()` method to correctly handle the backend streaming protocol:

```typescript
export class FlowApi {
  /**
   * Interacts with an AI agent that provides streaming responses
   * BREAKING CHANGE: Callbacks now receive (chunk, complete) instead of full messages
   */
  agent(
    question: string,
    think: (chunk: string, complete: boolean) => void,
    observe: (chunk: string, complete: boolean) => void,
    answer: (chunk: string, complete: boolean) => void,
    error: (s: string) => void,
  ) {
    const receiver = (response: unknown) => {
      const resp = response as AgentStreamingResponse;

      // Check for errors
      if (resp.chunk_type === "error" || resp.error) {
        const errorMessage = resp.content || resp.error || "Unknown agent error";
        error(typeof errorMessage === "string" ? errorMessage : String(errorMessage));
        return true; // End streaming on error
      }

      // Handle streaming chunks by chunk_type
      const content = resp.content || "";
      const messageComplete = !!resp.end_of_message;
      const dialogComplete = !!resp.end_of_dialog;

      switch (resp.chunk_type) {
        case "thought":
          think(content, messageComplete);
          break;
        case "observation":
          observe(content, messageComplete);
          break;
        case "final-answer":
          answer(content, messageComplete);
          break;
        case "action":
          // Actions are typically not streamed incrementally, just logged
          console.log("Agent action:", content);
          break;
      }

      return dialogComplete; // End when backend signals end_of_dialog
    };

    return this.api
      .makeRequestMulti<AgentRequest, AgentStreamingResponse>(
        "agent",
        {
          question: question,
          user: this.api.user,
          streaming: true, // Always use streaming mode
        },
        receiver,
        120000,
        2,
        this.flowId,
      )
      .catch((err) => {
        const errorMessage =
          err instanceof Error ? err.message : err?.toString() || "Unknown error";
        error(`Agent request failed: ${errorMessage}`);
      });
  }

#### 3.2 Add New Streaming Methods

Add streaming variants for other services alongside existing methods in `src/socket/trustgraph-socket.ts`:

```typescript
  // ... existing non-streaming methods unchanged ...

  /**
   * Performs Graph RAG query with streaming response
   * @param text - Query text
   * @param receiver - Called for each chunk with (chunk, complete) where complete=true on final chunk
   * @param onError - Called on error
   * @param options - Graph RAG options
   * @param collection - Collection name
   */
  graphRagStreaming(
    text: string,
    receiver: (chunk: string, complete: boolean) => void,
    onError: (error: string) => void,
    options?: GraphRagOptions,
    collection?: string,
  ): void {
    const recv = (response: unknown): boolean => {
      const resp = response as StreamingChunk;

      if (resp.error) {
        onError(resp.error.message);
        return true; // End streaming
      }

      const chunk = resp.chunk || "";
      const complete = !!resp.end_of_stream;

      receiver(chunk, complete);

      return complete; // End when backend signals end_of_stream
    };

    this.api.makeRequestMulti<GraphRagRequest, StreamingChunk>(
      "graph-rag",
      {
        query: text,
        user: this.api.user,
        collection: collection || "default",
        "entity-limit": options?.entityLimit,
        "triple-limit": options?.tripleLimit,
        "max-subgraph-size": options?.maxSubgraphSize,
        "max-path-length": options?.pathLength,
        streaming: true,
      },
      recv,
      60000,
      undefined,
      this.flowId,
    );
  }

  /**
   * Performs Document RAG query with streaming response
   * @param text - Query text
   * @param receiver - Called for each chunk with (chunk, complete) where complete=true on final chunk
   * @param onError - Called on error
   * @param docLimit - Maximum documents to retrieve
   * @param collection - Collection name
   */
  documentRagStreaming(
    text: string,
    receiver: (chunk: string, complete: boolean) => void,
    onError: (error: string) => void,
    docLimit?: number,
    collection?: string,
  ): void {
    const recv = (response: unknown): boolean => {
      const resp = response as StreamingChunk;

      if (resp.error) {
        onError(resp.error.message);
        return true;
      }

      const chunk = resp.chunk || "";
      const complete = !!resp.end_of_stream;

      receiver(chunk, complete);

      return complete;
    };

    this.api.makeRequestMulti<DocumentRagRequest, StreamingChunk>(
      "document-rag",
      {
        query: text,
        user: this.api.user,
        collection: collection || "default",
        "doc-limit": docLimit,
        streaming: true,
      },
      recv,
      60000,
      undefined,
      this.flowId,
    );
  }

  /**
   * Performs text completion with streaming response
   * @param system - System prompt
   * @param text - User prompt
   * @param receiver - Called for each chunk with (chunk, complete) where complete=true on final chunk
   * @param onError - Called on error
   */
  textCompletionStreaming(
    system: string,
    text: string,
    receiver: (chunk: string, complete: boolean) => void,
    onError: (error: string) => void,
  ): void {
    const recv = (response: unknown): boolean => {
      const resp = response as StreamingChunk;

      if (resp.error) {
        onError(resp.error.message);
        return true;
      }

      // Text completion uses 'response' field, not 'chunk'
      const chunk = resp.response || "";
      const complete = !!resp.end_of_stream;

      receiver(chunk, complete);

      return complete;
    };

    this.api.makeRequestMulti<TextCompletionRequest, StreamingChunk>(
      "text-completion",
      {
        system: system,
        prompt: text,
        streaming: true,
      },
      recv,
      30000,
      undefined,
      this.flowId,
    );
  }

  /**
   * Executes a prompt template with streaming response
   * @param id - Prompt template ID
   * @param terms - Template variables
   * @param receiver - Called for each chunk with (chunk, complete) where complete=true on final chunk
   * @param onError - Called on error
   */
  promptStreaming(
    id: string,
    terms: Record<string, unknown>,
    receiver: (chunk: string, complete: boolean) => void,
    onError: (error: string) => void,
  ): void {
    const recv = (response: unknown): boolean => {
      const resp = response as StreamingChunk;

      if (resp.error) {
        onError(resp.error.message);
        return true;
      }

      // Prompt service uses 'text' field
      const chunk = resp.text || "";
      const complete = !!resp.end_of_stream;

      receiver(chunk, complete);

      return complete;
    };

    this.api.makeRequestMulti<PromptRequest, StreamingChunk>(
      "prompt",
      {
        id: id,
        terms: terms,
        streaming: true,
      },
      recv,
      30000,
      undefined,
      this.flowId,
    );
  }
}
```

### 4. BaseApi Convenience Methods (Optional)

For users who don't need flow routing, add streaming methods to BaseApi:

```typescript
export class BaseApi {
  // Existing methods...

  /**
   * Streaming text completion without flow routing
   */
  textCompletionStreaming(
    system: string,
    prompt: string,
    receiver: (chunk: string, complete: boolean) => void,
    onError: (error: string) => void,
  ): void {
    const flowApi = new FlowApi(this, undefined);
    flowApi.textCompletionStreaming(system, prompt, receiver, onError);
  }

  // Similar for graphRagStreaming, documentRagStreaming, promptStreaming...
}
```

**Recommendation**: Add these for consistency with existing non-streaming methods on BaseApi.

## Implementation Plan

### Phase 1: Core Types (1 hour)
1. Add `streaming?: boolean` to request types
2. Add `StreamingChunk` interface
3. Add `PromptRequest` and `PromptResponse` types (currently missing)

### Phase 2: FlowApi Streaming Methods (2 hours)
1. Implement `textCompletionStreaming`
2. Implement `graphRagStreaming`
3. Implement `documentRagStreaming`
4. Implement `promptStreaming`
5. Add JSDoc comments

### Phase 3: BaseApi Convenience Methods (1 hour)
1. Add streaming methods to BaseApi
2. Update interface definitions
3. Update README with streaming examples

### Phase 4: Testing (2 hours)
1. Add unit tests for streaming methods
2. Add integration tests against mock WebSocket
3. Test error handling mid-stream
4. Test timeout behavior
5. Test concurrent streaming requests

### Phase 5: Documentation (1 hour)
1. Update README with streaming examples
2. Add streaming guide to docs/
3. Update API reference

**Total Estimated Time**: 7 hours

## Testing Strategy

### Unit Tests

```typescript
describe("FlowApi streaming", () => {
  it("should stream graph-rag chunks", async () => {
    const chunks: Array<{ chunk: string; complete: boolean }> = [];

    flowApi.graphRagStreaming(
      "test query",
      (chunk, complete) => {
        chunks.push({ chunk, complete });
      },
      (error) => fail(error),
    );

    // Simulate streaming chunks
    mockWebSocket.simulateMessage({ chunk: "Hello", end_of_stream: false });
    mockWebSocket.simulateMessage({ chunk: " world", end_of_stream: false });
    mockWebSocket.simulateMessage({ chunk: "", end_of_stream: true });

    expect(chunks).toEqual([
      { chunk: "Hello", complete: false },
      { chunk: " world", complete: false },
      { chunk: "", complete: true },
    ]);
  });

  it("should handle errors mid-stream", async () => {
    let errorMsg = "";
    const chunks: string[] = [];

    flowApi.graphRagStreaming(
      "test query",
      (chunk, complete) => {
        chunks.push(chunk);
      },
      (error) => {
        errorMsg = error;
      },
    );

    mockWebSocket.simulateMessage({ chunk: "Partial", end_of_stream: false });
    mockWebSocket.simulateMessage({
      error: { message: "LLM timeout" },
      end_of_stream: true,
    });

    expect(errorMsg).toBe("LLM timeout");
    expect(chunks).toEqual(["Partial"]); // Receiver gets chunks before error
  });
});
```

### Integration Tests

Test against actual TrustGraph backend (manual testing):
1. Start TrustGraph backend with streaming enabled
2. Test each streaming method with real queries
3. Verify chunks arrive in order
4. Verify end_of_stream handling
5. Test error scenarios (invalid query, timeout)

## Migration Guide

### For Users

#### Graph RAG / Document RAG / Text Completion / Prompt

**Before (non-streaming)**:
```typescript
const response = await flowApi.graphRag("What is machine learning?");
console.log(response); // Full text after 10-30 seconds
```

**After (streaming)**:
```typescript
let accumulated = "";

flowApi.graphRagStreaming(
  "What is machine learning?",
  (chunk, complete) => {
    accumulated += chunk;
    updateDisplay(accumulated);

    if (complete) {
      console.log("Final:", accumulated);
    }
  },
  (error) => {
    console.error("Error:", error);
  }
);
```

#### Agent (BREAKING CHANGE)

**Before (old client - incorrect)**:
```typescript
flowApi.agent(
  "What is machine learning?",
  (thought) => console.log("Thinking:", thought),          // Full thought received
  (observation) => console.log("Observing:", observation), // Full observation received
  (answer) => console.log("Answer:", answer),              // Full answer received
  (error) => console.error(error),
);
```

**After (updated to match backend)**:
```typescript
let currentThought = "";
let currentObservation = "";
let currentAnswer = "";

flowApi.agent(
  "What is machine learning?",
  (chunk, complete) => {
    currentThought += chunk;
    updateThinkingDisplay(currentThought);
    if (complete) {
      console.log("Thought complete:", currentThought);
      currentThought = ""; // Reset for next thought
    }
  },
  (chunk, complete) => {
    currentObservation += chunk;
    updateObservationDisplay(currentObservation);
    if (complete) {
      console.log("Observation complete:", currentObservation);
      currentObservation = "";
    }
  },
  (chunk, complete) => {
    currentAnswer += chunk;
    updateAnswerDisplay(currentAnswer);
    if (complete) {
      console.log("Final answer:", currentAnswer);
    }
  },
  (error) => console.error(error),
);
```

### Gradual Adoption

**For Graph RAG / Document RAG / Text Completion / Prompt**:
1. Continue using non-streaming APIs (no breaking changes)
2. Add streaming variants for user-facing chat interfaces first
3. Keep non-streaming for background tasks
4. Optionally add feature flag to toggle streaming on/off

**For Agent (BREAKING CHANGE)**:
1. Existing Agent users MUST update their callbacks to handle (chunk, complete) signature
2. Add accumulation logic in callback handlers
3. Use `complete` flag to detect when to reset accumulator or take final action

## Risks and Mitigations

### Risk 1: BREAKING CHANGE for Agent API
**Concern**: Existing Agent users must update their code when they upgrade.

**Mitigation**:
- Document the breaking change clearly in release notes
- Provide migration examples in this spec
- Consider: Add deprecation warning in previous version before breaking change
- Consider: Bump major version to signal breaking change
- The old API was incorrect anyway - this fixes a bug in the client

### Risk 2: API Surface Growth
**Concern**: Adding 4 new methods per API class (FlowApi, BaseApi) increases maintenance burden.

**Mitigation**:
- Methods share identical structure (only field name differs: chunk/response/text)
- Could extract common streaming handler if needed
- Backend already implements streaming, so no protocol risk

### Risk 3: TypeScript Type Safety
**Concern**: `StreamingChunk` union type may be confusing (chunk vs response vs text).

**Mitigation**:
- Each service method documents which field it uses
- Runtime code checks correct field
- Implementation is simple enough that field selection is obvious

### Risk 4: State Management in User Code
**Concern**: Users must manually accumulate chunks if they need full text.

**Mitigation**:
- This is intentional - client stays policy-free
- Higher-level abstractions (React hooks, etc.) can provide accumulation
- For users who don't need streaming behavior, non-streaming APIs remain unchanged

## Future Enhancements

### 1. Async Iterator API
Provide a modern streaming API using async iterators:

```typescript
async *graphRagStream(text: string): AsyncGenerator<string, void, void> {
  // Wraps graphRagStreaming in async iterator
}

// Usage:
for await (const chunk of flowApi.graphRagStream("query")) {
  console.log(chunk);
}
```

### 2. Retry on Stream Interruption
Currently, retries only apply to initial request. Could add mid-stream retry:
- Detect connection drop mid-stream
- Resume from last chunk (if backend supports resumption)

### 3. Client-Side Buffering
For very fast chunk arrival, buffer multiple chunks before calling receiver:
- Reduces callback frequency
- Could be opt-in via options parameter
- Note: This would add policy to the client, may be better in higher layers

### 4. Stream Cancellation
Allow users to cancel in-flight streaming requests:
```typescript
const cancel = flowApi.graphRagStreaming(...);
// Later:
cancel();
```

## Alternatives Considered

### Alternative 1: Separate Callbacks for Chunk and Complete
Use three callbacks: onChunk, onComplete, onError:

```typescript
graphRagStreaming(
  text: string,
  onChunk: (chunk: string, accumulated: string) => void,
  onComplete: (fullText: string) => void,
  onError: (error: string) => void,
)
```

**Rejected because**:
- Adds state management (accumulation) to the client layer
- Harder for implementations that need both signals at once
- More verbose callback signature

### Alternative 2: Unified Streaming Flag on Existing Methods
Modify existing methods to detect streaming callbacks:

```typescript
graphRag(
  text: string,
  options?: GraphRagOptions,
  collection?: string,
  receiver?: (chunk: string, complete: boolean) => void,
): Promise<string> | void
```

**Rejected because**:
- Violates single responsibility principle
- Return type becomes conditional (Promise vs void)
- Hard to type correctly in TypeScript
- Confusing API (streaming vs non-streaming behavior implicit)

### Alternative 3: Separate StreamingFlowApi Class
Create a parallel API class for streaming:

```typescript
export class StreamingFlowApi {
  graphRag(text: string, receiver: ..., onError: ...): void;
  documentRag(text: string, receiver: ..., onError: ...): void;
}
```

**Rejected because**:
- Duplicates all configuration and state management
- Users must manage two API instances
- No clear benefit over method suffixes

## Open Questions

1. **Should we add streaming to Prompt service?**
   - Prompt service is not currently in client (no PromptRequest/Response types)
   - Could add it alongside streaming support
   - **Decision**: Yes, add it for completeness (mentioned in backend docs)

2. **Should we add TypeScript overloads?**
   - Allow `graphRagStreaming(text, callbacks)` vs `graphRagStreaming(text, options, callbacks)`
   - **Decision**: Use optional parameters (simpler implementation)

## Conclusion

This proposal adds streaming support to the TrustGraph client and fixes the Agent API to correctly implement the backend protocol:

**Changes**:
1. **Fix Agent API** (BREAKING): Update callbacks to receive `(chunk, complete)` instead of full messages
2. Add `streaming?: boolean` flag to all request types
3. Add `AgentStreamingResponse` and `StreamingChunk` response types
4. Add `*Streaming` method variants to FlowApi and BaseApi for RAG/completion services
5. Use consistent two-callback pattern: `receiver(chunk, complete)` and `onError(message)` across all services

The implementation is straightforward (~7-10 hours including Agent fix), stays minimal and focused, and provides a clean foundation for higher-level abstractions to build upon.

**Key Design Principles**:
- **Policy-free**: No accumulation or buffering in client layer
- **Minimal callbacks**: Single receiver gets both chunk and completion signal
- **Protocol-correct**: Agent now properly implements backend's chunk_type/content/end_of_message protocol
- **Consistent**: Same pattern across all streaming services
- **Backward compatible**: Existing non-streaming APIs unchanged (except Agent which needs fixing)

**Breaking Changes**:
- Agent API callbacks change from `(fullMessage: string)` to `(chunk: string, complete: boolean)`
- Requires major version bump

**Recommendation**: Approve and implement in current sprint.
