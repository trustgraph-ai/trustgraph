# RAG Streaming Support Technical Specification

## Overview

This specification describes adding streaming support to GraphRAG and DocumentRAG services, enabling real-time token-by-token responses for knowledge graph and document retrieval queries. This extends the existing streaming architecture already implemented for LLM text-completion, prompt, and agent services.

## Goals

- **Consistent streaming UX**: Provide the same streaming experience across all TrustGraph services
- **Minimal API changes**: Add streaming support with a single `streaming` flag, following established patterns
- **Backward compatibility**: Maintain existing non-streaming behavior as default
- **Reuse existing infrastructure**: Leverage PromptClient streaming already implemented
- **Gateway support**: Enable streaming through websocket gateway for client applications

## Background

Currently implemented streaming services:
- **LLM text-completion service**: Phase 1 - streaming from LLM providers
- **Prompt service**: Phase 2 - streaming through prompt templates
- **Agent service**: Phase 3-4 - streaming ReAct responses with incremental thought/observation/answer chunks

Current limitations for RAG services:
- GraphRAG and DocumentRAG only support blocking responses
- Users must wait for complete LLM response before seeing any output
- Poor UX for long responses from knowledge graph or document queries
- Inconsistent experience compared to other TrustGraph services

This specification addresses these gaps by adding streaming support to GraphRAG and DocumentRAG. By enabling token-by-token responses, TrustGraph can:
- Provide consistent streaming UX across all query types
- Reduce perceived latency for RAG queries
- Enable better progress feedback for long-running queries
- Support real-time display in client applications

## Technical Design

### Architecture

The RAG streaming implementation leverages existing infrastructure:

1. **PromptClient Streaming** (Already implemented)
   - `kg_prompt()` and `document_prompt()` already accept `streaming` and `chunk_callback` parameters
   - These call `prompt()` internally with streaming support
   - No changes needed to PromptClient

   Module: `trustgraph-base/trustgraph/base/prompt_client.py`

2. **GraphRAG Service** (Needs streaming parameter pass-through)
   - Add `streaming` parameter to `query()` method
   - Pass streaming flag and callbacks to `prompt_client.kg_prompt()`
   - GraphRagRequest schema needs `streaming` field

   Modules:
   - `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
   - `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (Processor)
   - `trustgraph-base/trustgraph/schema/graph_rag.py` (Request schema)
   - `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (Gateway)

3. **DocumentRAG Service** (Needs streaming parameter pass-through)
   - Add `streaming` parameter to `query()` method
   - Pass streaming flag and callbacks to `prompt_client.document_prompt()`
   - DocumentRagRequest schema needs `streaming` field

   Modules:
   - `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
   - `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (Processor)
   - `trustgraph-base/trustgraph/schema/document_rag.py` (Request schema)
   - `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (Gateway)

### Data Flow

**Non-streaming (current)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=False)
                                   ↓
                                Prompt Service → LLM
                                   ↓
                                Complete response
                                   ↓
Client ← Gateway ← RAG Service ←  Response
```

**Streaming (proposed)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                                   ↓
                                Prompt Service → LLM (streaming)
                                   ↓
                                Chunk → callback → RAG Response (chunk)
                                   ↓                       ↓
Client ← Gateway ← ────────────────────────────────── Response stream
```

### APIs

**GraphRAG Changes**:

1. **GraphRag.query()** - Add streaming parameters
```python
async def query(
    self, query, user, collection,
    verbose=False, streaming=False, chunk_callback=None  # NEW
):
    # ... existing entity/triple retrieval ...

    if streaming and chunk_callback:
        resp = await self.prompt_client.kg_prompt(
            query, kg,
            streaming=True,
            chunk_callback=chunk_callback
        )
    else:
        resp = await self.prompt_client.kg_prompt(query, kg)

    return resp
```

2. **GraphRagRequest schema** - Add streaming field
```python
class GraphRagRequest(Record):
    query = String()
    user = String()
    collection = String()
    streaming = Boolean()  # NEW
```

3. **GraphRagResponse schema** - Add streaming fields (follow Agent pattern)
```python
class GraphRagResponse(Record):
    response = String()    # Legacy: complete response
    chunk = String()       # NEW: streaming chunk
    end_of_stream = Boolean()  # NEW: indicates last chunk
```

4. **Processor** - Pass streaming through
```python
async def handle(self, msg):
    # ... existing code ...

    async def send_chunk(chunk):
        await self.respond(GraphRagResponse(
            chunk=chunk,
            end_of_stream=False,
            response=None
        ))

    if request.streaming:
        full_response = await self.rag.query(
            query=request.query,
            user=request.user,
            collection=request.collection,
            streaming=True,
            chunk_callback=send_chunk
        )
        # Send final message
        await self.respond(GraphRagResponse(
            chunk=None,
            end_of_stream=True,
            response=full_response
        ))
    else:
        # Existing non-streaming path
        response = await self.rag.query(...)
        await self.respond(GraphRagResponse(response=response))
```

**DocumentRAG Changes**:

Identical pattern to GraphRAG:
1. Add `streaming` and `chunk_callback` parameters to `DocumentRag.query()`
2. Add `streaming` field to `DocumentRagRequest`
3. Add `chunk` and `end_of_stream` fields to `DocumentRagResponse`
4. Update Processor to handle streaming with callbacks

**Gateway Changes**:

Both `graph_rag.py` and `document_rag.py` in gateway/dispatch need updates to forward streaming chunks to websocket:

```python
async def handle(self, message, session, websocket):
    # ... existing code ...

    if request.streaming:
        async def recipient(resp):
            if resp.chunk:
                await websocket.send(json.dumps({
                    "id": message["id"],
                    "response": {"chunk": resp.chunk},
                    "complete": resp.end_of_stream
                }))
            return resp.end_of_stream

        await self.rag_client.request(request, recipient=recipient)
    else:
        # Existing non-streaming path
        resp = await self.rag_client.request(request)
        await websocket.send(...)
```

### Implementation Details

**Implementation order**:
1. Add schema fields (Request + Response for both RAG services)
2. Update GraphRag.query() and DocumentRag.query() methods
3. Update Processors to handle streaming
4. Update Gateway dispatch handlers
5. Add CLI flags to `tg-invoke-graph-rag` and `tg-invoke-document-rag`

**Callback pattern**:
Follow the same async callback pattern established in Agent streaming:
- Processor defines `async def send_chunk(chunk)` callback
- Passes callback to RAG service
- RAG service passes callback to PromptClient
- PromptClient invokes callback for each LLM chunk
- Processor sends streaming response message for each chunk

**Error handling**:
- Errors during streaming should send error response with `end_of_stream=True`
- Follow existing error propagation patterns from Agent streaming

## Security Considerations

No new security considerations beyond existing RAG services:
- Streaming responses use same user/collection isolation
- No changes to authentication or authorization
- Chunk boundaries don't expose sensitive data

## Performance Considerations

**Benefits**:
- Reduced perceived latency (first tokens arrive faster)
- Better UX for long responses
- Lower memory usage (no need to buffer complete response)

**Potential concerns**:
- More Pulsar messages for streaming responses
- Slightly higher CPU for chunking/callback overhead
- Mitigated by: streaming is opt-in, default remains non-streaming

**Testing considerations**:
- Test with large knowledge graphs (many triples)
- Test with many retrieved documents
- Measure overhead of streaming vs non-streaming

## Testing Strategy

**Unit tests**:
- Test GraphRag.query() with streaming=True/False
- Test DocumentRag.query() with streaming=True/False
- Mock PromptClient to verify callback invocations

**Integration tests**:
- Test full GraphRAG streaming flow (similar to existing agent streaming tests)
- Test full DocumentRAG streaming flow
- Test Gateway streaming forwarding
- Test CLI streaming output

**Manual testing**:
- `tg-invoke-graph-rag --streaming -q "What is machine learning?"`
- `tg-invoke-document-rag --streaming -q "Summarize the documents about AI"`
- Verify incremental output appears

## Migration Plan

No migration needed:
- Streaming is opt-in via `streaming` parameter (defaults to False)
- Existing clients continue to work unchanged
- New clients can opt into streaming

## Timeline

Estimated implementation: 4-6 hours
- Phase 1 (2 hours): GraphRAG streaming support
- Phase 2 (2 hours): DocumentRAG streaming support
- Phase 3 (1-2 hours): Gateway updates and CLI flags
- Testing: Built into each phase

## Open Questions

- Should we add streaming support to NLP Query service as well?
- Do we want to stream intermediate steps (e.g., "Retrieving entities...", "Querying graph...") or just LLM output?
- Should GraphRAG/DocumentRAG responses include chunk metadata (e.g., chunk number, total expected)?

## References

- Existing implementation: `docs/tech-specs/streaming-llm-responses.md`
- Agent streaming: `trustgraph-flow/trustgraph/agent/react/agent_manager.py`
- PromptClient streaming: `trustgraph-base/trustgraph/base/prompt_client.py`
