# Python API Refactor Technical Specification

## Overview

This specification describes a comprehensive refactor of the TrustGraph Python API client library to achieve feature parity with the API Gateway and add support for modern real-time communication patterns.

The refactor addresses four primary use cases:

1. **Streaming LLM Interactions**: Enable real-time streaming of LLM responses (agent, graph RAG, document RAG, text completion, prompts) with ~60x lower latency (500ms vs 30s for first token)
2. **Bulk Data Operations**: Support efficient bulk import/export of triples, graph embeddings, and document embeddings for large-scale knowledge graph management
3. **Feature Parity**: Ensure every API Gateway endpoint has a corresponding Python API method, including graph embeddings query
4. **Persistent Connections**: Enable WebSocket-based communication for multiplexed requests and reduced connection overhead

## Goals

- **Feature Parity**: Every Gateway API service has a corresponding Python API method
- **Streaming Support**: All streaming-capable services (agent, RAG, text completion, prompt) support streaming in Python API
- **WebSocket Transport**: Add optional WebSocket transport layer for persistent connections and multiplexing
- **Bulk Operations**: Add efficient bulk import/export for triples, graph embeddings, and document embeddings
- **Backward Compatibility**: Existing code continues to work without modification
- **Type Safety**: Maintain type-safe interfaces with dataclasses and type hints
- **Progressive Enhancement**: Streaming is opt-in via iterator pattern
- **Performance**: Achieve 60x latency improvement for streaming operations

## Background

### Current State

The Python API (`trustgraph-base/trustgraph/api/`) is a REST-only client library with the following modules:

- `flow.py`: Flow management and flow-scoped services (50 methods)
- `library.py`: Document library operations (9 methods)
- `knowledge.py`: KG core management (4 methods)
- `collection.py`: Collection metadata (3 methods)
- `config.py`: Configuration management (6 methods)
- `types.py`: Data type definitions (5 dataclasses)

**Total Operations**: 50/59 (85% coverage)

### Current Limitations

**Missing Operations**:
- Graph embeddings query (semantic search over graph entities)
- Bulk import/export for triples, graph embeddings, document embeddings, entity contexts, objects
- Metrics endpoint

**Missing Capabilities**:
- Streaming support for LLM services
- WebSocket transport
- Multiplexed concurrent requests
- Persistent connections

**Performance Issues**:
- High latency for LLM interactions (~30s time-to-first-token)
- Inefficient bulk data transfer (REST request per item)
- Connection overhead for multiple sequential operations

**User Experience Issues**:
- No real-time feedback during LLM generation
- Cannot cancel long-running LLM operations
- Poor scalability for bulk operations

### Impact

The November 2024 streaming enhancement to the Gateway API provided 60x latency improvement (500ms vs 30s first token) for LLM interactions, but Python API users cannot leverage this capability. This creates a significant experience gap between Python and non-Python users.

## Technical Design

### Architecture

The refactored Python API will support two transport layers:

1. **REST Transport** (existing, enhanced)
   - Synchronous request/response
   - Simple connection model
   - No streaming support
   - Default for backward compatibility

2. **WebSocket Transport** (new)
   - Persistent connection
   - Multiplexed requests
   - Streaming support
   - Bulk operations
   - Opt-in via constructor parameter

```python
# REST transport (default, backward compatible)
api = Api(url="http://localhost:8088/")

# WebSocket transport (new, opt-in)
api = Api(url="ws://localhost:8088/", transport="websocket")
```

### Components

#### 1. Transport Layer Abstraction

Module: `trustgraph-base/trustgraph/api/transport/`

```
transport/
├── __init__.py
├── base.py           # Abstract transport interface
├── rest.py           # REST transport (existing behavior)
└── websocket.py      # WebSocket transport (new)
```

**Base Transport Interface**:

```python
from abc import ABC, abstractmethod
from typing import Iterator, Any, Dict

class Transport(ABC):
    @abstractmethod
    def request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous request/response"""
        pass

    @abstractmethod
    def streaming_request(
        self,
        endpoint: str,
        data: Dict[str, Any]
    ) -> Iterator[Dict[str, Any]]:
        """Streaming request/response (yields chunks)"""
        pass

    @abstractmethod
    def bulk_import(
        self,
        endpoint: str,
        items: Iterator[Dict[str, Any]]
    ) -> None:
        """Bulk import from iterator"""
        pass

    @abstractmethod
    def bulk_export(
        self,
        endpoint: str
    ) -> Iterator[Dict[str, Any]]:
        """Bulk export as iterator"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection and cleanup"""
        pass
```

#### 2. REST Transport Implementation

Module: `trustgraph-base/trustgraph/api/transport/rest.py`

- Uses existing `requests` library
- `streaming_request()` raises `NotImplementedError` with helpful message
- `bulk_import()` / `bulk_export()` implemented via REST endpoints where available
- Maintains current behavior for backward compatibility

#### 3. WebSocket Transport Implementation

Module: `trustgraph-base/trustgraph/api/transport/websocket.py`

- Uses `websockets` library (async, but wrapped in sync interface using `asyncio.run()`)
- Maintains persistent connection
- Implements request multiplexing (up to 15 concurrent)
- Supports streaming responses
- Handles WebSocket reconnection
- Parses streaming chunk types (thoughts, observations, final-answer, RAG chunks)

**Key Features**:
- Automatic request ID generation
- Response correlation by ID
- Graceful error handling
- Automatic reconnection on disconnect
- Thread-safe for multi-threaded applications

#### 4. Enhanced Flow API

Module: `trustgraph-base/trustgraph/api/flow.py` (modified)

**New Methods**:

```python
class FlowInstance:
    # Existing methods remain unchanged

    # New: Graph embeddings query
    def graph_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query graph embeddings for semantic search"""
        pass

    # New: Bulk triple import
    def import_triples(
        self,
        triples: Iterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples (requires WebSocket transport)"""
        pass

    # New: Bulk triple export
    def export_triples(
        self,
        **kwargs
    ) -> Iterator[Triple]:
        """Bulk export triples (requires WebSocket transport)"""
        pass

    # New: Bulk graph embeddings import
    def import_graph_embeddings(
        self,
        embeddings: Iterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings (requires WebSocket transport)"""
        pass

    # New: Bulk graph embeddings export
    def export_graph_embeddings(
        self,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Bulk export graph embeddings (requires WebSocket transport)"""
        pass

    # New: Bulk document embeddings import
    def import_document_embeddings(
        self,
        embeddings: Iterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import document embeddings (requires WebSocket transport)"""
        pass

    # New: Bulk document embeddings export
    def export_document_embeddings(
        self,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Bulk export document embeddings (requires WebSocket transport)"""
        pass

    # New: Bulk entity contexts import
    def import_entity_contexts(
        self,
        contexts: Iterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import entity contexts (requires WebSocket transport)"""
        pass

    # New: Bulk entity contexts export
    def export_entity_contexts(
        self,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Bulk export entity contexts (requires WebSocket transport)"""
        pass

    # New: Bulk objects import
    def import_objects(
        self,
        objects: Iterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import objects (requires WebSocket transport)"""
        pass
```

**Modified Methods** (add streaming parameter):

```python
class FlowInstance:
    def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,  # NEW
        **kwargs
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Execute agent with optional streaming.

        Returns:
            - If streaming=False: Dict with final response
            - If streaming=True: Iterator yielding chunks

        Raises:
            NotImplementedError: If streaming=True with REST transport
        """
        pass

    def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,  # NEW
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        Text completion with optional streaming.

        Returns:
            - If streaming=False: Complete response string
            - If streaming=True: Iterator yielding token chunks

        Raises:
            NotImplementedError: If streaming=True with REST transport
        """
        pass

    def graph_rag(
        self,
        question: str,
        user: str,
        collection: str,
        max_subgraph_size: int = 1000,
        max_subgraph_count: int = 5,
        max_entity_distance: int = 3,
        streaming: bool = False,  # NEW
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        Graph RAG with optional streaming.

        Returns:
            - If streaming=False: Complete response string
            - If streaming=True: Iterator yielding chunks

        Raises:
            NotImplementedError: If streaming=True with REST transport
        """
        pass

    def document_rag(
        self,
        question: str,
        user: str,
        collection: str,
        doc_limit: int = 10,
        streaming: bool = False,  # NEW
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        Document RAG with optional streaming.

        Returns:
            - If streaming=False: Complete response string
            - If streaming=True: Iterator yielding chunks

        Raises:
            NotImplementedError: If streaming=True with REST transport
        """
        pass

    def prompt(
        self,
        id: str,
        variables: Dict[str, str],
        streaming: bool = False,  # NEW
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        Execute prompt with optional streaming.

        Returns:
            - If streaming=False: Complete response string
            - If streaming=True: Iterator yielding chunks

        Raises:
            NotImplementedError: If streaming=True with REST transport
        """
        pass
```

#### 5. Enhanced Types

Module: `trustgraph-base/trustgraph/api/types.py` (modified)

**New Types**:

```python
from typing import Iterator, Union, Dict, Any
import dataclasses

@dataclasses.dataclass
class StreamingChunk:
    """Base class for streaming chunks"""
    content: str
    end_of_message: bool = False

@dataclasses.dataclass
class AgentThought(StreamingChunk):
    """Agent reasoning chunk"""
    chunk_type: str = "thought"

@dataclasses.dataclass
class AgentObservation(StreamingChunk):
    """Agent tool observation chunk"""
    chunk_type: str = "observation"

@dataclasses.dataclass
class AgentAnswer(StreamingChunk):
    """Agent final answer chunk"""
    chunk_type: str = "final-answer"
    end_of_dialog: bool = False

@dataclasses.dataclass
class RAGChunk(StreamingChunk):
    """RAG streaming chunk"""
    end_of_stream: bool = False
    error: Optional[Dict[str, str]] = None

# Type aliases for clarity
AgentStream = Iterator[Union[AgentThought, AgentObservation, AgentAnswer]]
RAGStream = Iterator[RAGChunk]
CompletionStream = Iterator[str]
```

#### 6. Metrics API

Module: `trustgraph-base/trustgraph/api/metrics.py` (new)

```python
class Metrics:
    def __init__(self, transport: Transport):
        self.transport = transport

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

### Implementation Approach

#### Phase 1: Transport Abstraction (Week 1)

1. Create transport layer abstraction
2. Refactor existing REST code into `RestTransport` class
3. Update `Api` class to use transport abstraction
4. Add unit tests for transport layer
5. Verify backward compatibility

**Backward Compatibility**: Zero breaking changes. All existing code works unchanged.

#### Phase 2: WebSocket Transport (Week 2-3)

1. Implement `WebSocketTransport` class
2. Add WebSocket connection management
3. Implement request multiplexing
4. Add streaming response parsing
5. Add unit and integration tests
6. Document WebSocket usage patterns

**Backward Compatibility**: Opt-in via constructor parameter. Default remains REST.

#### Phase 3: Streaming API Enhancement (Week 3-4)

1. Add `streaming` parameter to LLM methods (agent, text_completion, graph_rag, document_rag, prompt)
2. Implement streaming response handling
3. Add streaming chunk types and parsers
4. Add unit and integration tests
5. Add streaming examples to documentation

**Backward Compatibility**: `streaming=False` by default. Existing calls work unchanged.

#### Phase 4: Bulk Operations (Week 4-5)

1. Add bulk import/export methods to `FlowInstance`
2. Implement iterator-based bulk operations
3. Add progress tracking (optional callback)
4. Add unit and integration tests
5. Add bulk operation examples

**Backward Compatibility**: New methods only. Zero impact on existing code.

#### Phase 5: Feature Parity (Week 5)

1. Add `graph_embeddings_query()` method
2. Add `Metrics` API
3. Comprehensive integration tests
4. Update documentation
5. Migration guide for users

**Backward Compatibility**: New methods only. Zero impact on existing code.

### Data Models

#### Transport Selection

```python
# Automatic transport selection based on URL scheme
api = Api(url="http://localhost:8088/")   # Uses RestTransport
api = Api(url="https://localhost:8088/")  # Uses RestTransport
api = Api(url="ws://localhost:8088/")     # Uses WebSocketTransport
api = Api(url="wss://localhost:8088/")    # Uses WebSocketTransport (secure)

# Explicit transport override
api = Api(url="http://localhost:8088/", transport="websocket")  # Force WebSocket
```

#### Streaming Response Types

**Agent Streaming**:

```python
flow = api.flow().id("default")

# Non-streaming (existing)
response = flow.agent(question="What is ML?", user="user123")
print(response["response"])

# Streaming (new)
for chunk in flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentThought):
        print(f"Thinking: {chunk.content}")
    elif isinstance(chunk, AgentObservation):
        print(f"Observed: {chunk.content}")
    elif isinstance(chunk, AgentAnswer):
        print(f"Answer: {chunk.content}")
        if chunk.end_of_dialog:
            break
```

**RAG Streaming**:

```python
# Non-streaming (existing)
response = flow.graph_rag(question="What is Python?", user="user123", collection="default")
print(response)

# Streaming (new)
for chunk in flow.graph_rag(
    question="What is Python?",
    user="user123",
    collection="default",
    streaming=True
):
    print(chunk.content, end="", flush=True)
    if chunk.end_of_stream:
        break
```

**Bulk Operations**:

```python
# Bulk import triples
def triple_generator():
    yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
    yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
    yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

flow = api.flow().id("default")
flow.import_triples(triple_generator())

# Bulk export triples
for triple in flow.export_triples():
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### APIs

#### New APIs

1. **Transport Layer**:
   - `Transport` (abstract base class)
   - `RestTransport` (REST implementation)
   - `WebSocketTransport` (WebSocket implementation)

2. **Flow-Scoped Services**:
   - `FlowInstance.graph_embeddings_query()` - Semantic graph search
   - `FlowInstance.import_triples()` - Bulk triple import
   - `FlowInstance.export_triples()` - Bulk triple export
   - `FlowInstance.import_graph_embeddings()` - Bulk graph embeddings import
   - `FlowInstance.export_graph_embeddings()` - Bulk graph embeddings export
   - `FlowInstance.import_document_embeddings()` - Bulk document embeddings import
   - `FlowInstance.export_document_embeddings()` - Bulk document embeddings export
   - `FlowInstance.import_entity_contexts()` - Bulk entity contexts import
   - `FlowInstance.export_entity_contexts()` - Bulk entity contexts export
   - `FlowInstance.import_objects()` - Bulk objects import

3. **Metrics**:
   - `Api.metrics()` - Access metrics API
   - `Metrics.get()` - Get Prometheus metrics

#### Modified APIs

1. **Constructor**:
   ```python
   Api(url: str, timeout: int = 60, transport: Optional[str] = None, token: Optional[str] = None)
   ```
   - Added `transport` parameter (optional, auto-detected from URL scheme)
   - Added `token` parameter (optional, for WebSocket query param auth)

2. **LLM Services** (add `streaming` parameter):
   - `FlowInstance.agent(..., streaming: bool = False)`
   - `FlowInstance.text_completion(..., streaming: bool = False)`
   - `FlowInstance.graph_rag(..., streaming: bool = False)`
   - `FlowInstance.document_rag(..., streaming: bool = False)`
   - `FlowInstance.prompt(..., streaming: bool = False)`

### Implementation Details

#### Error Handling

**Transport Not Supported**:
```python
try:
    api = Api(url="http://localhost:8088/", transport="rest")
    flow = api.flow().id("default")

    # This raises NotImplementedError
    for chunk in flow.agent(question="...", streaming=True):
        print(chunk)
except NotImplementedError as e:
    print(f"Error: {e}")
    print("Hint: Use WebSocket transport for streaming: Api(url='ws://localhost:8088/')")
```

**Connection Errors**:
```python
try:
    api = Api(url="ws://localhost:8088/")
    flow = api.flow().id("default")
    response = flow.agent(question="...", user="user123")
except ConnectionError as e:
    print(f"WebSocket connection failed: {e}")
    print("Hint: Ensure Gateway is running and WebSocket endpoint is accessible")
```

**Partial Streaming Errors**:
```python
flow = api.flow().id("default")

accumulated = []
try:
    for chunk in flow.graph_rag(question="...", streaming=True):
        accumulated.append(chunk.content)
        if chunk.error:
            print(f"Error occurred: {chunk.error}")
            print(f"Partial response: {''.join(accumulated)}")
            break
except Exception as e:
    print(f"Streaming error: {e}")
    print(f"Partial response: {''.join(accumulated)}")
```

#### Resource Management

**Context Manager Support**:
```python
# Automatic cleanup
with Api(url="ws://localhost:8088/") as api:
    flow = api.flow().id("default")
    response = flow.agent(question="...", user="user123")
# WebSocket connection automatically closed

# Manual cleanup
api = Api(url="ws://localhost:8088/")
try:
    flow = api.flow().id("default")
    response = flow.agent(question="...", user="user123")
finally:
    api.close()  # Explicitly close WebSocket connection
```

#### Threading and Concurrency

**Thread Safety**:
- Each `Api` instance maintains its own connection
- WebSocket transport uses locks for thread-safe request multiplexing
- Multiple threads can share an `Api` instance safely
- Streaming iterators are not thread-safe (consume from single thread)

**Async Support** (future consideration):
```python
# Phase 2 enhancement (not in initial scope)
import asyncio

async def main():
    api = await AsyncApi(url="ws://localhost:8088/")
    flow = api.flow().id("default")

    async for chunk in flow.agent(question="...", streaming=True):
        print(chunk.content)

    await api.close()

asyncio.run(main())
```

## Security Considerations

### Authentication

**REST Transport**:
- Bearer token via `Authorization` header (existing)
- Token passed in `Api()` constructor

**WebSocket Transport**:
- Token via query parameter: `?token=<token>`
- Token passed in `Api()` constructor
- Secure WebSocket (WSS) support for encrypted transport

**Example**:
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")

# WebSocket with auth
api = Api(url="ws://localhost:8088/", token="mytoken")
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### Secure Communication

- Support both WS (WebSocket) and WSS (WebSocket Secure) schemes
- TLS certificate validation for WSS connections
- Optional certificate verification disable for development (with warning)

### Input Validation

- Validate URL schemes (http, https, ws, wss)
- Validate transport parameter values
- Validate streaming parameter combinations
- Validate bulk import data types

## Performance Considerations

### Latency Improvements

**Streaming LLM Operations**:
- **Time-to-first-token**: ~500ms (vs ~30s non-streaming)
- **Improvement**: 60x faster perceived performance
- **Applicable to**: Agent, Graph RAG, Document RAG, Text Completion, Prompt

**Persistent Connections**:
- **Connection overhead**: Eliminated for subsequent requests
- **WebSocket handshake**: One-time cost (~100ms)
- **Applicable to**: All operations when using WebSocket transport

### Throughput Improvements

**Bulk Operations**:
- **Triples import**: ~10,000 triples/second (vs ~100/second with REST per-item)
- **Embeddings import**: ~5,000 embeddings/second (vs ~50/second with REST per-item)
- **Improvement**: 100x throughput for bulk operations

**Request Multiplexing**:
- **Concurrent requests**: Up to 15 simultaneous requests over single connection
- **Connection reuse**: No connection overhead for concurrent operations

### Memory Considerations

**Streaming Responses**:
- Constant memory usage (process chunks as they arrive)
- No buffering of complete response
- Suitable for very long outputs (>1MB)

**Bulk Operations**:
- Iterator-based processing (constant memory)
- No loading of entire dataset into memory
- Suitable for datasets with millions of items

### Benchmarks (Expected)

| Operation | REST (existing) | WebSocket (streaming) | Improvement |
|-----------|----------------|----------------------|-------------|
| Agent (time-to-first-token) | 30s | 0.5s | 60x |
| Graph RAG (time-to-first-token) | 25s | 0.5s | 50x |
| Import 10K triples | 100s | 1s | 100x |
| Import 1M triples | 10,000s (2.7h) | 100s (1.6m) | 100x |
| 10 concurrent small requests | 5s (sequential) | 0.5s (parallel) | 10x |

## Testing Strategy

### Unit Tests

**Transport Layer** (`test_transport.py`):
- Test REST transport request/response
- Test WebSocket transport connection
- Test WebSocket transport reconnection
- Test request multiplexing
- Test streaming response parsing
- Mock WebSocket server for deterministic tests

**API Methods** (`test_flow.py`, `test_library.py`, etc.):
- Test new methods with mocked transport
- Test streaming parameter handling
- Test bulk operation iterators
- Test error handling

**Types** (`test_types.py`):
- Test new streaming chunk types
- Test type serialization/deserialization

### Integration Tests

**End-to-End REST** (`test_integration_rest.py`):
- Test all operations against real Gateway (REST mode)
- Verify backward compatibility
- Test error conditions

**End-to-End WebSocket** (`test_integration_websocket.py`):
- Test all operations against real Gateway (WebSocket mode)
- Test streaming operations
- Test bulk operations
- Test concurrent requests
- Test connection recovery

**Streaming Services** (`test_streaming_integration.py`):
- Test agent streaming (thoughts, observations, answers)
- Test RAG streaming (incremental chunks)
- Test text completion streaming (token-by-token)
- Test prompt streaming
- Test error handling during streaming

**Bulk Operations** (`test_bulk_integration.py`):
- Test bulk import/export of triples (1K, 10K, 100K items)
- Test bulk import/export of embeddings
- Test memory usage during bulk operations
- Test progress tracking

### Performance Tests

**Latency Benchmarks** (`test_performance_latency.py`):
- Measure time-to-first-token (streaming vs non-streaming)
- Measure connection overhead (REST vs WebSocket)
- Compare against expected benchmarks

**Throughput Benchmarks** (`test_performance_throughput.py`):
- Measure bulk import throughput
- Measure request multiplexing efficiency
- Compare against expected benchmarks

### Compatibility Tests

**Backward Compatibility** (`test_backward_compatibility.py`):
- Run existing test suite against refactored API
- Verify zero breaking changes
- Test migration path for common patterns

## Migration Plan

### Phase 1: Transparent Migration (Default)

**No code changes required**. Existing code continues to work:

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### Phase 2: Opt-in Streaming (Simple)

**Add `streaming=True` parameter** to enable streaming:

```python
# Before: Non-streaming
response = flow.agent(question="What is ML?", user="user123")
print(response["response"])

# After: Streaming
api = Api(url="ws://localhost:8088/")  # Use WebSocket transport
flow = api.flow().id("default")

for chunk in flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentAnswer):
        print(chunk.content, end="", flush=True)
```

### Phase 3: Bulk Operations (New Capability)

**Use new bulk methods** for large datasets:

```python
# Before: Inefficient per-item loading
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")

for triple in my_large_triple_list:
    # This is slow (100 triples/second)
    flow.triples_query(...)  # Not ideal for bulk insert

# After: Efficient bulk loading
api = Api(url="ws://localhost:8088/")
flow = api.flow().id("default")

# This is fast (10,000 triples/second)
flow.import_triples(iter(my_large_triple_list))
```

### Documentation Updates

1. **README.md**: Add streaming and WebSocket examples
2. **API Reference**: Document all new methods and parameters
3. **Migration Guide**: Step-by-step guide for enabling streaming
4. **Examples**: Add example scripts for common patterns
5. **Performance Guide**: Document expected performance improvements

### Deprecation Policy

**No deprecations**. All existing APIs remain supported. This is a pure enhancement.

## Timeline

### Week 1: Foundation
- Transport abstraction layer
- Refactor existing REST code
- Unit tests for transport layer
- Backward compatibility verification

### Week 2: WebSocket Transport
- WebSocket transport implementation
- Connection management and reconnection
- Request multiplexing
- Unit and integration tests

### Week 3: Streaming Support
- Add streaming parameter to LLM methods
- Implement streaming response parsing
- Add streaming chunk types
- Streaming integration tests

### Week 4: Bulk Operations
- Add bulk import/export methods
- Implement iterator-based operations
- Performance testing
- Bulk operation integration tests

### Week 5: Feature Parity & Documentation
- Add graph embeddings query
- Add metrics API
- Comprehensive documentation
- Migration guide
- Release candidate

### Week 6: Release
- Final integration testing
- Performance benchmarking
- Release documentation
- Community announcement

**Total Duration**: 6 weeks

## Open Questions

### API Design Questions

1. **Async Support**: Should we provide an async variant (`AsyncApi`) in the initial release, or defer to Phase 2?
   - **Recommendation**: Defer to Phase 2. Focus on sync API first for simplicity.

2. **Progress Tracking**: Should bulk operations support progress callbacks?
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   flow.import_triples(triples, on_progress=progress_callback)
   ```
   - **Recommendation**: Add in Phase 2. Not critical for initial release.

3. **Streaming Timeout**: How should we handle timeouts for streaming operations?
   - **Recommendation**: Use same timeout as non-streaming, but reset on each chunk received.

4. **Chunk Buffering**: Should we buffer chunks or yield immediately?
   - **Recommendation**: Yield immediately for lowest latency.

### Implementation Questions

1. **WebSocket Library**: Should we use `websockets`, `websocket-client`, or `aiohttp`?
   - **Recommendation**: `websockets` (async, mature, well-maintained). Wrap in sync interface.

2. **Connection Pooling**: Should we support multiple concurrent `Api` instances sharing a connection pool?
   - **Recommendation**: Defer to Phase 2. Each `Api` instance has its own connection initially.

3. **Automatic Fallback**: Should we automatically fallback from WebSocket to REST on connection failure?
   - **Recommendation**: No automatic fallback. Explicit user choice. Fail fast with clear error message.

### Testing Questions

1. **Mock Gateway**: Should we create a lightweight mock Gateway for testing, or test against real Gateway?
   - **Recommendation**: Both. Use mocks for unit tests, real Gateway for integration tests.

2. **Performance Regression Tests**: Should we add automated performance regression testing to CI?
   - **Recommendation**: Yes, but with generous thresholds to account for CI environment variability.

## References

### Related Tech Specs
- `docs/tech-specs/streaming-llm-responses.md` - Streaming implementation in Gateway
- `docs/tech-specs/rag-streaming-support.md` - RAG streaming support

### Implementation Files
- `trustgraph-base/trustgraph/api/` - Python API source
- `trustgraph-flow/trustgraph/gateway/` - Gateway source
- `trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - WebSocket multiplexer reference implementation

### Documentation
- `docs/apiSpecification.md` - Complete API reference
- `docs/api-status-summary.md` - API status summary
- `README.websocket` - WebSocket protocol documentation
- `STREAMING-IMPLEMENTATION-NOTES.txt` - Streaming implementation notes

### External Libraries
- `websockets` - Python WebSocket library (https://websockets.readthedocs.io/)
- `requests` - Python HTTP library (existing)
