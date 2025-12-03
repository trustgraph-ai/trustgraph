# Streaming LLM Responses Technical Specification

## Overview

This specification describes the implementation of streaming support for LLM
responses in TrustGraph. Streaming enables real-time delivery of generated
tokens as they are produced by the LLM, rather than waiting for complete
response generation.

This implementation supports the following use cases:

1. **Real-time User Interfaces**: Stream tokens to UI as they are generated,
   providing immediate visual feedback
2. **Reduced Time-to-First-Token**: Users see output beginning immediately
   rather than waiting for full generation
3. **Long Response Handling**: Handle very long outputs that might otherwise
   timeout or exceed memory limits
4. **Interactive Applications**: Enable responsive chat and agent interfaces

## Goals

- **Backward Compatibility**: Existing non-streaming clients continue to work
  without modification
- **Consistent API Design**: Streaming and non-streaming use the same schema
  patterns with minimal divergence
- **Provider Flexibility**: Support streaming where available, graceful
  fallback where not
- **Phased Rollout**: Incremental implementation to reduce risk
- **End-to-End Support**: Streaming from LLM provider through to client
  applications via Pulsar, Gateway API, and Python API

## Background

### Current Architecture

The current LLM text completion flow operates as follows:

1. Client sends `TextCompletionRequest` with `system` and `prompt` fields
2. LLM service processes the request and waits for complete generation
3. Single `TextCompletionResponse` returned with complete `response` string

Current schema (`trustgraph-base/trustgraph/schema/services/llm.py`):

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
```

### Current Limitations

- **Latency**: Users must wait for complete generation before seeing any output
- **Timeout Risk**: Long generations may exceed client timeout thresholds
- **Poor UX**: No feedback during generation creates perception of slowness
- **Resource Usage**: Full responses must be buffered in memory

This specification addresses these limitations by enabling incremental response
delivery while maintaining full backward compatibility.

## Technical Design

### Phase 1: Infrastructure

Phase 1 establishes the foundation for streaming by modifying schemas, APIs,
and CLI tools.

#### Schema Changes

##### LLM Schema (`trustgraph-base/trustgraph/schema/services/llm.py`)

**Request Changes:**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

- `streaming`: When `true`, requests streaming response delivery
- Default: `false` (existing behavior preserved)

**Response Changes:**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

- `end_of_stream`: When `true`, indicates this is the final (or only) response
- For non-streaming requests: Single response with `end_of_stream=true`
- For streaming requests: Multiple responses, all with `end_of_stream=false`
  except the final one

##### Prompt Schema (`trustgraph-base/trustgraph/schema/services/prompt.py`)

The prompt service wraps text completion, so it mirrors the same pattern:

**Request Changes:**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**Response Changes:**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### Gateway API Changes

The Gateway API must expose streaming capabilities to HTTP/WebSocket clients.

**REST API Updates:**

- `POST /api/v1/text-completion`: Accept `streaming` parameter in request body
- Response behavior depends on streaming flag:
  - `streaming=false`: Single JSON response (current behavior)
  - `streaming=true`: Server-Sent Events (SSE) stream or WebSocket messages

**Response Format (Streaming):**

Each streamed chunk follows the same schema structure:
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

Final chunk:
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### Python API Changes

The Python client API must support both streaming and non-streaming modes
while maintaining backward compatibility.

**LlmClient Updates** (`trustgraph-base/trustgraph/clients/llm_client.py`):

```python
class LlmClient(BaseClient):
    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        # Existing behavior when streaming=False

    async def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request.
        Yields response chunks as they arrive.
        """
        # New async generator method
```

**PromptClient Updates** (`trustgraph-base/trustgraph/base/prompt_client.py`):

Similar pattern with `streaming` parameter and async generator variant.

#### CLI Tool Changes

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

- Streaming enabled by default for better interactive UX
- `--no-streaming` flag disables streaming
- When streaming: Output tokens to stdout as they arrive
- When not streaming: Wait for complete response, then output

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

Same pattern as `tg-invoke-llm`.

#### LLM Service Base Class Changes

**LlmService** (`trustgraph-base/trustgraph/base/llm_service.py`):

```python
class LlmService(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        request = msg.value()
        streaming = getattr(request, 'streaming', False)

        if streaming and self.supports_streaming():
            async for chunk in self.generate_content_stream(...):
                await self.send_response(chunk, end_of_stream=False)
            await self.send_response(final_chunk, end_of_stream=True)
        else:
            response = await self.generate_content(...)
            await self.send_response(response, end_of_stream=True)

    def supports_streaming(self):
        """Override in subclass to indicate streaming support."""
        return False

    async def generate_content_stream(self, system, prompt, model, temperature):
        """Override in subclass to implement streaming."""
        raise NotImplementedError()
```

---

### Phase 2: VertexAI Proof of Concept

Phase 2 implements streaming in a single provider (VertexAI) to validate the
infrastructure and enable end-to-end testing.

#### VertexAI Implementation

**Module:** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**Changes:**

1. Override `supports_streaming()` to return `True`
2. Implement `generate_content_stream()` async generator
3. Handle both Gemini and Claude models (via VertexAI Anthropic API)

**Gemini Streaming:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    model_instance = self.get_model(model, temperature)
    response = model_instance.generate_content(
        [system, prompt],
        stream=True  # Enable streaming
    )
    for chunk in response:
        yield LlmChunk(
            text=chunk.text,
            in_token=None,  # Available only in final chunk
            out_token=None,
        )
    # Final chunk includes token counts from response.usage_metadata
```

**Claude (via VertexAI Anthropic) Streaming:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### Testing

- Unit tests for streaming response assembly
- Integration tests with VertexAI (Gemini and Claude)
- End-to-end tests: CLI -> Gateway -> Pulsar -> VertexAI -> back
- Backward compatibility tests: Non-streaming requests still work

---

### Phase 3: All LLM Providers

Phase 3 extends streaming support to all LLM providers in the system.

#### Provider Implementation Status

Each provider must either:
1. **Full Streaming Support**: Implement `generate_content_stream()`
2. **Compatibility Mode**: Handle the `end_of_stream` flag correctly
   (return single response with `end_of_stream=true`)

| Provider | Package | Streaming Support |
|----------|---------|-------------------|
| OpenAI | trustgraph-flow | Full (native streaming API) |
| Claude/Anthropic | trustgraph-flow | Full (native streaming API) |
| Ollama | trustgraph-flow | Full (native streaming API) |
| Cohere | trustgraph-flow | Full (native streaming API) |
| Mistral | trustgraph-flow | Full (native streaming API) |
| Azure OpenAI | trustgraph-flow | Full (native streaming API) |
| Google AI Studio | trustgraph-flow | Full (native streaming API) |
| VertexAI | trustgraph-vertexai | Full (Phase 2) |
| Bedrock | trustgraph-bedrock | Full (native streaming API) |
| LM Studio | trustgraph-flow | Full (OpenAI-compatible) |
| LlamaFile | trustgraph-flow | Full (OpenAI-compatible) |
| vLLM | trustgraph-flow | Full (OpenAI-compatible) |
| TGI | trustgraph-flow | TBD |
| Azure | trustgraph-flow | TBD |

#### Implementation Pattern

For OpenAI-compatible providers (OpenAI, LM Studio, LlamaFile, vLLM):

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    response = await self.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield LlmChunk(text=chunk.choices[0].delta.content)
```

---

### Phase 4: Agent API

Phase 4 extends streaming to the Agent API. This is more complex because the
Agent API is already multi-message by nature (thought → action → observation
→ repeat → final answer).

#### Current Agent Schema

```python
class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()
```

#### Proposed Agent Schema Changes

**Request Changes:**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**Response Changes:**

The agent produces multiple types of output during its reasoning cycle:
- Thoughts (reasoning)
- Actions (tool calls)
- Observations (tool results)
- Answer (final response)
- Errors

Since `chunk_type` identifies what kind of content is being sent, the separate
`answer`, `error`, `thought`, and `observation` fields can be collapsed into
a single `content` field:

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**Field Semantics:**

- `chunk_type`: Indicates what type of content is in the `content` field
  - `"thought"`: Agent reasoning/thinking
  - `"action"`: Tool/action being invoked
  - `"observation"`: Result from tool execution
  - `"answer"`: Final answer to the user's question
  - `"error"`: Error message

- `content`: The actual streamed content, interpreted based on `chunk_type`

- `end_of_message`: When `true`, the current chunk type is complete
  - Example: All tokens for the current thought have been sent
  - Allows clients to know when to move to the next stage

- `end_of_dialog`: When `true`, the entire agent interaction is complete
  - This is the final message in the stream

#### Agent Streaming Behavior

When `streaming=true`:

1. **Thought streaming**:
   - Multiple chunks with `chunk_type="thought"`, `end_of_message=false`
   - Final thought chunk has `end_of_message=true`
2. **Action notification**:
   - Single chunk with `chunk_type="action"`, `end_of_message=true`
3. **Observation**:
   - Chunk(s) with `chunk_type="observation"`, final has `end_of_message=true`
4. **Repeat** steps 1-3 as the agent reasons
5. **Final answer**:
   - `chunk_type="answer"` with the final response in `content`
   - Last chunk has `end_of_message=true`, `end_of_dialog=true`

**Example Stream Sequence:**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

When `streaming=false`:
- Current behavior preserved
- Single response with complete answer
- `end_of_message=true`, `end_of_dialog=true`

#### Gateway and Python API

- Gateway: New SSE/WebSocket endpoint for agent streaming
- Python API: New `agent_stream()` async generator method

---

## Security Considerations

- **No new attack surface**: Streaming uses same authentication/authorization
- **Rate limiting**: Apply per-token or per-chunk rate limits if needed
- **Connection handling**: Properly terminate streams on client disconnect
- **Timeout management**: Streaming requests need appropriate timeout handling

## Performance Considerations

- **Memory**: Streaming reduces peak memory usage (no full response buffering)
- **Latency**: Time-to-first-token significantly reduced
- **Connection overhead**: SSE/WebSocket connections have keep-alive overhead
- **Pulsar throughput**: Multiple small messages vs. single large message
  tradeoff

## Testing Strategy

### Unit Tests
- Schema serialization/deserialization with new fields
- Backward compatibility (missing fields use defaults)
- Chunk assembly logic

### Integration Tests
- Each LLM provider's streaming implementation
- Gateway API streaming endpoints
- Python client streaming methods

### End-to-End Tests
- CLI tool streaming output
- Full flow: Client → Gateway → Pulsar → LLM → back
- Mixed streaming/non-streaming workloads

### Backward Compatibility Tests
- Existing clients work without modification
- Non-streaming requests behave identically

## Migration Plan

### Phase 1: Infrastructure
- Deploy schema changes (backward compatible)
- Deploy Gateway API updates
- Deploy Python API updates
- Release CLI tool updates

### Phase 2: VertexAI
- Deploy VertexAI streaming implementation
- Validate with test workloads

### Phase 3: All Providers
- Roll out provider updates incrementally
- Monitor for issues

### Phase 4: Agent API
- Deploy agent schema changes
- Deploy agent streaming implementation
- Update documentation

## Timeline

| Phase | Description | Dependencies |
|-------|-------------|--------------|
| Phase 1 | Infrastructure | None |
| Phase 2 | VertexAI PoC | Phase 1 |
| Phase 3 | All Providers | Phase 2 |
| Phase 4 | Agent API | Phase 3 |

## Design Decisions

The following questions were resolved during specification:

1. **Token Counts in Streaming**: Token counts are deltas, not running totals.
   Consumers can sum them if needed. This matches how most providers report
   usage and simplifies the implementation.

2. **Error Handling in Streams**: If an error occurs, the `error` field is
   populated and no other fields are needed. An error is always the final
   communication - no subsequent messages are permitted or expected after
   an error. For LLM/Prompt streams, `end_of_stream=true`. For Agent streams,
   `chunk_type="error"` with `end_of_dialog=true`.

3. **Partial Response Recovery**: The messaging protocol (Pulsar) is resilient,
   so message-level retry is not needed. If a client loses track of the stream
   or disconnects, it must retry the full request from scratch.

4. **Prompt Service Streaming**: Streaming is only supported for text (`text`)
   responses, not structured (`object`) responses. The prompt service knows at
   the outset whether the output will be JSON or text based on the prompt
   template. If a streaming request is made for a JSON-output prompt, the
   service should either:
   - Return the complete JSON in a single response with `end_of_stream=true`, or
   - Reject the streaming request with an error

## Open Questions

None at this time.

## References

- Current LLM schema: `trustgraph-base/trustgraph/schema/services/llm.py`
- Current prompt schema: `trustgraph-base/trustgraph/schema/services/prompt.py`
- Current agent schema: `trustgraph-base/trustgraph/schema/services/agent.py`
- LLM service base: `trustgraph-base/trustgraph/base/llm_service.py`
- VertexAI provider: `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
- Gateway API: `trustgraph-base/trustgraph/api/`
- CLI tools: `trustgraph-cli/trustgraph/cli/`
