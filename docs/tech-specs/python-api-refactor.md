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
- **Full Async Support**: Complete async/await implementation for all interfaces (REST, WebSocket, bulk operations, metrics)
- **Backward Compatibility**: Existing code continues to work without modification
- **Type Safety**: Maintain type-safe interfaces with dataclasses and type hints
- **Progressive Enhancement**: Streaming and async are opt-in via explicit interface selection
- **Performance**: Achieve 60x latency improvement for streaming operations
- **Modern Python**: Support for both sync and async paradigms for maximum flexibility

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

The refactored Python API uses a **modular interface approach** with separate objects for different communication patterns. All interfaces are available in both **synchronous and asynchronous** variants:

1. **REST Interface** (existing, enhanced)
   - **Sync**: `api.flow()`, `api.library()`, `api.knowledge()`, `api.collection()`, `api.config()`
   - **Async**: `api.async_flow()`
   - Synchronous/asynchronous request/response
   - Simple connection model
   - Default for backward compatibility

2. **WebSocket Interface** (new)
   - **Sync**: `api.socket()`
   - **Async**: `api.async_socket()`
   - Persistent connection
   - Multiplexed requests
   - Streaming support
   - Same method signatures as REST where functionality overlaps

3. **Bulk Operations Interface** (new)
   - **Sync**: `api.bulk()`
   - **Async**: `api.async_bulk()`
   - WebSocket-based for efficiency
   - Iterator/AsyncIterator-based import/export
   - Handles large datasets

4. **Metrics Interface** (new)
   - **Sync**: `api.metrics()`
   - **Async**: `api.async_metrics()`
   - Prometheus metrics access

```python
import asyncio

# Synchronous interfaces
api = Api(url="http://localhost:8088/")

# REST (existing, unchanged)
flow = api.flow().id("default")
response = flow.agent(question="...", user="...")

# WebSocket (new)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="...", user="...")
for chunk in socket_flow.agent(question="...", user="...", streaming=True):
    print(chunk)

# Bulk operations (new)
bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Asynchronous interfaces
async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST (new)
    flow = api.async_flow().id("default")
    response = await flow.agent(question="...", user="...")

    # Async WebSocket (new)
    socket_flow = api.async_socket().flow("default")
    async for chunk in socket_flow.agent(question="...", streaming=True):
        print(chunk)

    # Async bulk operations (new)
    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

asyncio.run(main())
```

**Key Design Principles**:
- **Same URL for all interfaces**: `Api(url="http://localhost:8088/")` works for all
- **Sync/Async symmetry**: Every interface has both sync and async variants with identical method signatures
- **Identical signatures**: Where functionality overlaps, method signatures are identical between REST and WebSocket, sync and async
- **Progressive enhancement**: Choose interface based on needs (REST for simple, WebSocket for streaming, Bulk for large datasets, async for modern frameworks)
- **Explicit intent**: `api.socket()` signals WebSocket, `api.async_socket()` signals async WebSocket
- **Backward compatible**: Existing code unchanged

### Components

#### 1. Core API Class (Modified)

Module: `trustgraph-base/trustgraph/api/api.py`

**Enhanced API Class**:

```python
class Api:
    def __init__(self, url: str, timeout: int = 60, token: Optional[str] = None):
        self.url = url
        self.timeout = timeout
        self.token = token
        self._socket_client = None
        self._bulk_client = None
        self._async_flow = None
        self._async_socket_client = None
        self._async_bulk_client = None

    # Existing synchronous methods (unchanged)
    def flow(self) -> Flow:
        """Synchronous REST-based flow interface"""
        pass

    def library(self) -> Library:
        """Synchronous REST-based library interface"""
        pass

    def knowledge(self) -> Knowledge:
        """Synchronous REST-based knowledge interface"""
        pass

    def collection(self) -> Collection:
        """Synchronous REST-based collection interface"""
        pass

    def config(self) -> Config:
        """Synchronous REST-based config interface"""
        pass

    # New synchronous methods
    def socket(self) -> SocketClient:
        """Synchronous WebSocket-based interface for streaming operations"""
        if self._socket_client is None:
            self._socket_client = SocketClient(self.url, self.timeout, self.token)
        return self._socket_client

    def bulk(self) -> BulkClient:
        """Synchronous bulk operations interface for import/export"""
        if self._bulk_client is None:
            self._bulk_client = BulkClient(self.url, self.timeout, self.token)
        return self._bulk_client

    def metrics(self) -> Metrics:
        """Synchronous metrics interface"""
        return Metrics(self.url, self.timeout, self.token)

    # New asynchronous methods
    def async_flow(self) -> AsyncFlow:
        """Asynchronous REST-based flow interface"""
        if self._async_flow is None:
            self._async_flow = AsyncFlow(self.url, self.timeout, self.token)
        return self._async_flow

    def async_socket(self) -> AsyncSocketClient:
        """Asynchronous WebSocket-based interface for streaming operations"""
        if self._async_socket_client is None:
            self._async_socket_client = AsyncSocketClient(self.url, self.timeout, self.token)
        return self._async_socket_client

    def async_bulk(self) -> AsyncBulkClient:
        """Asynchronous bulk operations interface for import/export"""
        if self._async_bulk_client is None:
            self._async_bulk_client = AsyncBulkClient(self.url, self.timeout, self.token)
        return self._async_bulk_client

    def async_metrics(self) -> AsyncMetrics:
        """Asynchronous metrics interface"""
        return AsyncMetrics(self.url, self.timeout, self.token)

    # Resource management
    def close(self) -> None:
        """Close all synchronous connections"""
        if self._socket_client:
            self._socket_client.close()
        if self._bulk_client:
            self._bulk_client.close()

    async def aclose(self) -> None:
        """Close all asynchronous connections"""
        if self._async_socket_client:
            await self._async_socket_client.aclose()
        if self._async_bulk_client:
            await self._async_bulk_client.aclose()
        if self._async_flow:
            await self._async_flow.aclose()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
```

#### 2. Synchronous WebSocket Client

Module: `trustgraph-base/trustgraph/api/socket_client.py` (new)

**SocketClient Class**:

```python
class SocketClient:
    """Synchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> SocketFlowInstance:
        """Get flow instance for WebSocket operations"""
        return SocketFlowInstance(self, flow_id)

    def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Uses asyncio.run() internally to wrap async websockets library
        pass

    def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        # Synchronous wrapper around async WebSocket calls
        pass

    def close(self) -> None:
        """Close WebSocket connection"""
        pass

class SocketFlowInstance:
    """Synchronous WebSocket flow instance with same interface as REST FlowInstance"""
    def __init__(self, client: SocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance
    def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**Key Features**:
- Lazy connection (only connects when first request sent)
- Request multiplexing (up to 15 concurrent)
- Automatic reconnection on disconnect
- Streaming response parsing
- Thread-safe operation
- Synchronous wrapper around async websockets library

#### 3. Asynchronous WebSocket Client

Module: `trustgraph-base/trustgraph/api/async_socket_client.py` (new)

**AsyncSocketClient Class**:

```python
class AsyncSocketClient:
    """Asynchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> AsyncSocketFlowInstance:
        """Get async flow instance for WebSocket operations"""
        return AsyncSocketFlowInstance(self, flow_id)

    async def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Native async websockets library
        pass

    async def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        pass

    async def aclose(self) -> None:
        """Close WebSocket connection"""
        pass

class AsyncSocketFlowInstance:
    """Asynchronous WebSocket flow instance"""
    def __init__(self, client: AsyncSocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance (but async)
    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**Key Features**:
- Native async/await support
- Efficient for async applications (FastAPI, aiohttp)
- No thread blocking
- Same interface as sync version
- AsyncIterator for streaming

#### 4. Synchronous Bulk Operations Client

Module: `trustgraph-base/trustgraph/api/bulk_client.py` (new)

**BulkClient Class**:

```python
class BulkClient:
    """Synchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    def import_triples(
        self,
        flow: str,
        triples: Iterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    def import_graph_embeddings(
        self,
        flow: str,
        embeddings: Iterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    def close(self) -> None:
        """Close connections"""
        pass
```

**Key Features**:
- Iterator-based for constant memory usage
- Dedicated WebSocket connections per operation
- Progress tracking (optional callback)
- Error handling with partial success reporting

#### 5. Asynchronous Bulk Operations Client

Module: `trustgraph-base/trustgraph/api/async_bulk_client.py` (new)

**AsyncBulkClient Class**:

```python
class AsyncBulkClient:
    """Asynchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    async def import_triples(
        self,
        flow: str,
        triples: AsyncIterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    async def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    async def import_graph_embeddings(
        self,
        flow: str,
        embeddings: AsyncIterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    async def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    async def aclose(self) -> None:
        """Close connections"""
        pass
```

**Key Features**:
- AsyncIterator-based for constant memory usage
- Efficient for async applications
- Native async/await support
- Same interface as sync version

#### 6. REST Flow API (Synchronous - Unchanged)

Module: `trustgraph-base/trustgraph/api/flow.py`

The REST Flow API remains **completely unchanged** for backward compatibility. All existing methods continue to work:

- `Flow.list()`, `Flow.start()`, `Flow.stop()`, etc.
- `FlowInstance.agent()`, `FlowInstance.text_completion()`, `FlowInstance.graph_rag()`, etc.
- All existing signatures and return types preserved

**New**: Add `graph_embeddings_query()` to REST FlowInstance for feature parity:

```python
class FlowInstance:
    # All existing methods unchanged...

    # New: Graph embeddings query (REST)
    def graph_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query graph embeddings for semantic search"""
        # Calls POST /api/v1/flow/{flow}/service/graph-embeddings
        pass
```

#### 7. Asynchronous REST Flow API

Module: `trustgraph-base/trustgraph/api/async_flow.py` (new)

**AsyncFlow and AsyncFlowInstance Classes**:

```python
class AsyncFlow:
    """Asynchronous REST-based flow interface"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def list(self) -> List[Dict[str, Any]]:
        """List all flows"""
        pass

    async def get(self, id: str) -> Dict[str, Any]:
        """Get flow definition"""
        pass

    async def start(self, class_name: str, id: str, description: str, parameters: Dict) -> None:
        """Start a flow"""
        pass

    async def stop(self, id: str) -> None:
        """Stop a flow"""
        pass

    def id(self, flow_id: str) -> AsyncFlowInstance:
        """Get async flow instance"""
        return AsyncFlowInstance(self.url, self.timeout, self.token, flow_id)

    async def aclose(self) -> None:
        """Close connection"""
        pass

class AsyncFlowInstance:
    """Asynchronous REST flow instance"""

    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Async agent execution"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        **kwargs
    ) -> str:
        """Async text completion"""
        pass

    async def graph_rag(
        self,
        question: str,
        user: str,
        collection: str,
        **kwargs
    ) -> str:
        """Async graph RAG"""
        pass

    # ... all other FlowInstance methods as async versions
```

**Key Features**:
- Native async HTTP using `aiohttp` or `httpx`
- Same method signatures as sync REST API
- No streaming (use `async_socket()` for streaming)
- Efficient for async applications

#### 8. Metrics API

Module: `trustgraph-base/trustgraph/api/metrics.py` (new)

**Synchronous Metrics**:

```python
class Metrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

**Asynchronous Metrics**:

```python
class AsyncMetrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

#### 9. Enhanced Types

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
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

### Implementation Approach

#### Phase 1: Core API Enhancement (Week 1)

1. Add `socket()`, `bulk()`, and `metrics()` methods to `Api` class
2. Implement lazy initialization for WebSocket and bulk clients
3. Add context manager support (`__enter__`, `__exit__`)
4. Add `close()` method for cleanup
5. Add unit tests for API class enhancements
6. Verify backward compatibility

**Backward Compatibility**: Zero breaking changes. New methods only.

#### Phase 2: WebSocket Client (Week 2-3)

1. Implement `SocketClient` class with connection management
2. Implement `SocketFlowInstance` with same method signatures as `FlowInstance`
3. Add request multiplexing support (up to 15 concurrent)
4. Add streaming response parsing for different chunk types
5. Add automatic reconnection logic
6. Add unit and integration tests
7. Document WebSocket usage patterns

**Backward Compatibility**: New interface only. Zero impact on existing code.

#### Phase 3: Streaming Support (Week 3-4)

1. Add streaming chunk type classes (`AgentThought`, `AgentObservation`, `AgentAnswer`, `RAGChunk`)
2. Implement streaming response parsing in `SocketClient`
3. Add streaming parameter to all LLM methods in `SocketFlowInstance`
4. Handle error cases during streaming
5. Add unit and integration tests for streaming
6. Add streaming examples to documentation

**Backward Compatibility**: New interface only. Existing REST API unchanged.

#### Phase 4: Bulk Operations (Week 4-5)

1. Implement `BulkClient` class
2. Add bulk import/export methods for triples, embeddings, contexts, objects
3. Implement iterator-based processing for constant memory
4. Add progress tracking (optional callback)
5. Add error handling with partial success reporting
6. Add unit and integration tests
7. Add bulk operation examples

**Backward Compatibility**: New interface only. Zero impact on existing code.

#### Phase 5: Feature Parity & Polish (Week 5)

1. Add `graph_embeddings_query()` to REST `FlowInstance`
2. Implement `Metrics` class
3. Add comprehensive integration tests
4. Performance benchmarking
5. Update all documentation
6. Create migration guide

**Backward Compatibility**: New methods only. Zero impact on existing code.

### Data Models

#### Interface Selection

```python
# Single API instance, same URL for all interfaces
api = Api(url="http://localhost:8088/")

# Synchronous interfaces
rest_flow = api.flow().id("default")           # Sync REST
socket_flow = api.socket().flow("default")     # Sync WebSocket
bulk = api.bulk()                               # Sync bulk operations
metrics = api.metrics()                         # Sync metrics

# Asynchronous interfaces
async_rest_flow = api.async_flow().id("default")      # Async REST
async_socket_flow = api.async_socket().flow("default") # Async WebSocket
async_bulk = api.async_bulk()                          # Async bulk operations
async_metrics = api.async_metrics()                    # Async metrics
```

#### Streaming Response Types

**Agent Streaming**:

```python
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - non-streaming (same signature)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - streaming (new)
for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
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
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.graph_rag(question="What is Python?", user="user123", collection="default")
print(response)

# WebSocket interface - streaming (new)
socket_flow = api.socket().flow("default")
for chunk in socket_flow.graph_rag(
    question="What is Python?",
    user="user123",
    collection="default",
    streaming=True
):
    print(chunk.content, end="", flush=True)
    if chunk.end_of_stream:
        break
```

**Bulk Operations (Synchronous)**:

```python
api = Api(url="http://localhost:8088/")

# Bulk import triples
def triple_generator():
    yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
    yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
    yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Bulk export triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

**Bulk Operations (Asynchronous)**:

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async bulk import triples
    async def async_triple_generator():
        yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
        yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
        yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

    # Async bulk export triples
    async for triple in bulk.export_triples(flow="default"):
        print(f"{triple.s} -> {triple.p} -> {triple.o}")

asyncio.run(main())
```

**Async REST Example**:

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST flow operations
    flow = api.async_flow().id("default")
    response = await flow.agent(question="What is ML?", user="user123")
    print(response["response"])

asyncio.run(main())
```

**Async WebSocket Streaming Example**:

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async WebSocket streaming
    socket = api.async_socket()
    flow = socket.flow("default")

    async for chunk in flow.agent(question="What is ML?", user="user123", streaming=True):
        if isinstance(chunk, AgentAnswer):
            print(chunk.content, end="", flush=True)
            if chunk.end_of_dialog:
                break

asyncio.run(main())
```

### APIs

#### New APIs

1. **Core API Class**:
   - **Synchronous**:
     - `Api.socket()` - Get synchronous WebSocket client
     - `Api.bulk()` - Get synchronous bulk operations client
     - `Api.metrics()` - Get synchronous metrics client
     - `Api.close()` - Close all synchronous connections
     - Context manager support (`__enter__`, `__exit__`)
   - **Asynchronous**:
     - `Api.async_flow()` - Get asynchronous REST flow client
     - `Api.async_socket()` - Get asynchronous WebSocket client
     - `Api.async_bulk()` - Get asynchronous bulk operations client
     - `Api.async_metrics()` - Get asynchronous metrics client
     - `Api.aclose()` - Close all asynchronous connections
     - Async context manager support (`__aenter__`, `__aexit__`)

2. **Synchronous WebSocket Client**:
   - `SocketClient.flow(flow_id)` - Get WebSocket flow instance
   - `SocketFlowInstance.agent(..., streaming: bool = False)` - Agent with optional streaming
   - `SocketFlowInstance.text_completion(..., streaming: bool = False)` - Text completion with optional streaming
   - `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - Graph RAG with optional streaming
   - `SocketFlowInstance.document_rag(..., streaming: bool = False)` - Document RAG with optional streaming
   - `SocketFlowInstance.prompt(..., streaming: bool = False)` - Prompt with optional streaming
   - `SocketFlowInstance.graph_embeddings_query()` - Graph embeddings query
   - All other FlowInstance methods with identical signatures

3. **Asynchronous WebSocket Client**:
   - `AsyncSocketClient.flow(flow_id)` - Get async WebSocket flow instance
   - `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - Async agent with optional streaming
   - `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - Async text completion with optional streaming
   - `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - Async graph RAG with optional streaming
   - `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - Async document RAG with optional streaming
   - `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - Async prompt with optional streaming
   - `AsyncSocketFlowInstance.graph_embeddings_query()` - Async graph embeddings query
   - All other FlowInstance methods as async versions

4. **Synchronous Bulk Operations Client**:
   - `BulkClient.import_triples(flow, triples)` - Bulk triple import
   - `BulkClient.export_triples(flow)` - Bulk triple export
   - `BulkClient.import_graph_embeddings(flow, embeddings)` - Bulk graph embeddings import
   - `BulkClient.export_graph_embeddings(flow)` - Bulk graph embeddings export
   - `BulkClient.import_document_embeddings(flow, embeddings)` - Bulk document embeddings import
   - `BulkClient.export_document_embeddings(flow)` - Bulk document embeddings export
   - `BulkClient.import_entity_contexts(flow, contexts)` - Bulk entity contexts import
   - `BulkClient.export_entity_contexts(flow)` - Bulk entity contexts export
   - `BulkClient.import_objects(flow, objects)` - Bulk objects import

5. **Asynchronous Bulk Operations Client**:
   - `AsyncBulkClient.import_triples(flow, triples)` - Async bulk triple import
   - `AsyncBulkClient.export_triples(flow)` - Async bulk triple export
   - `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - Async bulk graph embeddings import
   - `AsyncBulkClient.export_graph_embeddings(flow)` - Async bulk graph embeddings export
   - `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - Async bulk document embeddings import
   - `AsyncBulkClient.export_document_embeddings(flow)` - Async bulk document embeddings export
   - `AsyncBulkClient.import_entity_contexts(flow, contexts)` - Async bulk entity contexts import
   - `AsyncBulkClient.export_entity_contexts(flow)` - Async bulk entity contexts export
   - `AsyncBulkClient.import_objects(flow, objects)` - Async bulk objects import

6. **Asynchronous REST Flow Client**:
   - `AsyncFlow.list()` - Async list all flows
   - `AsyncFlow.get(id)` - Async get flow definition
   - `AsyncFlow.start(...)` - Async start flow
   - `AsyncFlow.stop(id)` - Async stop flow
   - `AsyncFlow.id(flow_id)` - Get async flow instance
   - `AsyncFlowInstance.agent(...)` - Async agent execution
   - `AsyncFlowInstance.text_completion(...)` - Async text completion
   - `AsyncFlowInstance.graph_rag(...)` - Async graph RAG
   - All other FlowInstance methods as async versions

7. **Metrics Clients**:
   - `Metrics.get()` - Synchronous Prometheus metrics
   - `AsyncMetrics.get()` - Asynchronous Prometheus metrics

8. **REST Flow API Enhancement**:
   - `FlowInstance.graph_embeddings_query()` - Graph embeddings query (sync feature parity)
   - `AsyncFlowInstance.graph_embeddings_query()` - Graph embeddings query (async feature parity)

#### Modified APIs

1. **Constructor** (minor enhancement):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   - Added `token` parameter (optional, for authentication)
   - No other changes - fully backward compatible

2. **No Breaking Changes**:
   - All existing REST API methods unchanged
   - All existing signatures preserved
   - All existing return types preserved

### Implementation Details

#### Error Handling

**WebSocket Connection Errors**:
```python
try:
    api = Api(url="http://localhost:8088/")
    socket = api.socket()
    socket_flow = socket.flow("default")
    response = socket_flow.agent(question="...", user="user123")
except ConnectionError as e:
    print(f"WebSocket connection failed: {e}")
    print("Hint: Ensure Gateway is running and WebSocket endpoint is accessible")
```

**Graceful Fallback**:
```python
api = Api(url="http://localhost:8088/")

try:
    # Try WebSocket streaming first
    socket_flow = api.socket().flow("default")
    for chunk in socket_flow.agent(question="...", user="...", streaming=True):
        print(chunk.content)
except ConnectionError:
    # Fall back to REST non-streaming
    print("WebSocket unavailable, falling back to REST")
    rest_flow = api.flow().id("default")
    response = rest_flow.agent(question="...", user="...")
    print(response["response"])
```

**Partial Streaming Errors**:
```python
api = Api(url="http://localhost:8088/")
socket_flow = api.socket().flow("default")

accumulated = []
try:
    for chunk in socket_flow.graph_rag(question="...", streaming=True):
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
with Api(url="http://localhost:8088/") as api:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
# All connections automatically closed

# Manual cleanup
api = Api(url="http://localhost:8088/")
try:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
finally:
    api.close()  # Explicitly close all connections (WebSocket, bulk, etc.)
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

**Use `api.socket()` interface** to enable streaming:

```python
# Before: Non-streaming REST
api = Api(url="http://localhost:8088/")
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# After: Streaming WebSocket (same parameters!)
api = Api(url="http://localhost:8088/")  # Same URL
socket_flow = api.socket().flow("default")

for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentAnswer):
        print(chunk.content, end="", flush=True)
```

**Key Points**:
- Same URL for both REST and WebSocket
- Same method signatures (easy migration)
- Just add `.socket()` and `streaming=True`

### Phase 3: Bulk Operations (New Capability)

**Use `api.bulk()` interface** for large datasets:

```python
# Before: Inefficient per-item operations
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")

for triple in my_large_triple_list:
    # Slow per-item operations
    # (no direct bulk insert in REST API)
    pass

# After: Efficient bulk loading
api = Api(url="http://localhost:8088/")  # Same URL
bulk = api.bulk()

# This is fast (10,000 triples/second)
bulk.import_triples(flow="default", triples=iter(my_large_triple_list))
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

1. **Async Support**: ✅ **RESOLVED** - Full async support included in initial release
   - All interfaces have async variants: `async_flow()`, `async_socket()`, `async_bulk()`, `async_metrics()`
   - Provides complete symmetry between sync and async APIs
   - Essential for modern async frameworks (FastAPI, aiohttp)

2. **Progress Tracking**: Should bulk operations support progress callbacks?
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   - **Recommendation**: Add in Phase 2. Not critical for initial release.

3. **Streaming Timeout**: How should we handle timeouts for streaming operations?
   - **Recommendation**: Use same timeout as non-streaming, but reset on each chunk received.

4. **Chunk Buffering**: Should we buffer chunks or yield immediately?
   - **Recommendation**: Yield immediately for lowest latency.

5. **Global Services via WebSocket**: Should `api.socket()` support global services (library, knowledge, collection, config) or only flow-scoped services?
   - **Recommendation**: Start with flow-scoped only (where streaming matters). Add global services if needed in Phase 2.

### Implementation Questions

1. **WebSocket Library**: Should we use `websockets`, `websocket-client`, or `aiohttp`?
   - **Recommendation**: `websockets` (async, mature, well-maintained). Wrap in sync interface using `asyncio.run()`.

2. **Connection Pooling**: Should we support multiple concurrent `Api` instances sharing a connection pool?
   - **Recommendation**: Defer to Phase 2. Each `Api` instance has its own connections initially.

3. **Connection Reuse**: Should `SocketClient` and `BulkClient` share the same WebSocket connection, or use separate connections?
   - **Recommendation**: Separate connections. Simpler implementation, clearer separation of concerns.

4. **Lazy vs Eager Connection**: Should WebSocket connection be established in `api.socket()` or on first request?
   - **Recommendation**: Lazy (on first request). Avoids connection overhead if user only uses REST methods.

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
