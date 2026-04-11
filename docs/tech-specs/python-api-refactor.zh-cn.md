# Python API 重构技术规范

## 概述

本规范描述了 TrustGraph Python API 客户端库的全面重构，旨在实现与 API 网关的功能对齐，并添加对现代实时通信模式的支持。

该重构解决了四个主要用例：

1. **流式 LLM 交互**: 启用 LLM 响应的实时流式传输（代理、图 RAG、文档 RAG、文本补全、提示），延迟降低约 60 倍（第一个 token 为 500 毫秒，而不是 30 秒）。
2. **批量数据操作**: 支持高效的大规模知识图谱管理的 triples、图嵌入和文档嵌入的批量导入/导出。
3. **功能对齐**: 确保每个 API 网关端点都有相应的 Python API 方法，包括图嵌入查询。
4. **持久连接**: 启用基于 WebSocket 的通信，以实现多路复用请求和降低连接开销。

## 目标

**功能对齐**: 每个网关 API 服务都有相应的 Python API 方法。
**流式支持**: 所有支持流式传输的服务（代理、RAG、文本补全、提示）在 Python API 中支持流式传输。
**WebSocket 传输**: 添加可选的 WebSocket 传输层，用于持久连接和多路复用。
**批量操作**: 添加 triples、图嵌入和文档嵌入的高效批量导入/导出功能。
**完全异步支持**: 为所有接口（REST、WebSocket、批量操作、指标）实现完整的 async/await。
**向后兼容性**: 现有代码无需修改即可继续工作。
**类型安全**: 维护类型安全的接口，使用 dataclasses 和类型提示。
**渐进式增强**: 流式传输和异步是可选的，通过显式接口选择启用。
**性能**: 实现流式操作的 60 倍延迟改进。
**现代 Python**: 支持同步和异步范式，以实现最大的灵活性。

## 背景

### 当前状态

Python API (`trustgraph-base/trustgraph/api/`) 是一个仅支持 REST 的客户端库，包含以下模块：

`flow.py`: 流管理和流范围服务（50 个方法）。
`library.py`: 文档库操作（9 个方法）。
`knowledge.py`: KG 核心管理（4 个方法）。
`collection.py`: 集合元数据（3 个方法）。
`config.py`: 配置管理（6 个方法）。
`types.py`: 数据类型定义（5 个 dataclasses）。

**总操作**: 50/59 (覆盖率 85%)

### 当前限制

**缺失的操作**:
图嵌入查询（图实体上的语义搜索）。
triples、图嵌入、文档嵌入、实体上下文、对象的批量导入/导出。
指标端点。

**缺失的功能**:
LLM 服务的流式传输支持。
WebSocket 传输。
多路复用的并发请求。
持久连接。

**性能问题**:
LLM 交互的延迟高（第一个 token 需要 30 秒）。
批量数据传输效率低下（每个项目一个 REST 请求）。
多个连续操作的连接开销。

**用户体验问题**:
LLM 生成过程中没有实时反馈。
无法取消长时间运行的 LLM 操作。
批量操作的可扩展性差。

### 影响

2024 年 11 月对网关 API 的流式增强，将 LLM 交互的延迟提高了 60 倍（第一个 token 为 500 毫秒，而不是 30 秒），但 Python API 用户无法利用此功能。 这在 Python 用户和非 Python 用户之间造成了显著的体验差距。

## 技术设计

### 架构

重构的 Python API 采用 **模块化接口方法**，具有用于不同通信模式的单独对象。 所有接口都提供 **同步和异步** 两种版本：

1. **REST 接口** (现有，增强)
   **同步**: `api.flow()`, `api.library()`, `api.knowledge()`, `api.collection()`, `api.config()`
   **异步**: `api.async_flow()`
   同步/异步请求/响应。
   简单的连接模型。
   默认用于向后兼容。

2. **WebSocket 接口** (新)
   **同步**: `api.socket()`
   **异步**: `api.async_socket()`
   持久连接。
   多路复用的请求。
   流式传输支持。
   功能重叠时，方法签名与 REST 相同。

3. **批量操作接口** (新)
   **同步**: `api.bulk()`
   **异步**: `api.async_bulk()`
   基于 WebSocket，提高效率。
   基于 Iterator/AsyncIterator 的导入/导出。
   处理大型数据集。

4. **指标接口** (新)
   **同步**: `api.metrics()`
   **异步**: `api.async_metrics()`
   Prometheus 指标访问。

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

**关键设计原则**:
**所有接口使用相同的URL**: `Api(url="http://localhost:8088/")` 对所有接口都有效。
**同步/异步对称**: 每个接口都具有同步和异步变体，方法签名相同。
**相同的签名**: 当功能重叠时，REST 和 WebSocket 之间的同步和异步方法签名相同。
**渐进式增强**: 根据需求选择接口（REST 用于简单操作，WebSocket 用于流式传输，Bulk 用于大型数据集，async 用于现代框架）。
**明确意图**: `api.socket()` 表示 WebSocket，`api.async_socket()` 表示异步 WebSocket。
**向后兼容**: 现有代码保持不变。

### 组件

#### 1. 核心 API 类 (修改版)

模块: `trustgraph-base/trustgraph/api/api.py`

**增强的 API 类**:

```python
class Api:
    def __init__(self, url: str, timeout: int = 60, token: Optional[str] = None):
        self.url = url
        self.timeout = timeout
        self.token = token  # Optional bearer token for REST, query param for WebSocket
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

#### 2. 同步 WebSocket 客户端

模块：`trustgraph-base/trustgraph/api/socket_client.py` (新)

**SocketClient 类**:

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

**主要特性：**
延迟连接（仅在首次发送请求时建立连接）
请求复用（最多 15 个并发请求）
断开连接时自动重连
流式响应解析
线程安全操作
异步 WebSocket 库的同步封装

#### 3. 异步 WebSocket 客户端

模块：`trustgraph-base/trustgraph/api/async_socket_client.py` (新)

**AsyncSocketClient 类：**

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

**主要特性：**
原生支持 async/await
适用于异步应用程序（FastAPI, aiohttp）
无线程阻塞
与同步版本具有相同的接口
AsyncIterator 用于流式传输

#### 4. 同步批量操作客户端

模块：`trustgraph-base/trustgraph/api/bulk_client.py` (新)

**BulkClient 类：**

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

**主要特性：**
基于迭代器，内存占用恒定
每个操作都使用专用的 WebSocket 连接
进度跟踪（可选的回调函数）
错误处理，支持部分成功报告

#### 5. 异步批量操作客户端

模块：`trustgraph-base/trustgraph/api/async_bulk_client.py` (新)

**AsyncBulkClient 类：**

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

**主要特性：**
基于 AsyncIterator，内存占用恒定
适用于异步应用程序，效率高
原生支持 async/await
与同步版本具有相同的接口

#### 6. REST Flow API (同步 - 未改变)

模块：`trustgraph-base/trustgraph/api/flow.py`

REST Flow API 保持 **完全不变**，以确保向后兼容。所有现有方法均可继续使用：

`Flow.list()`, `Flow.start()`, `Flow.stop()`, 等等。
`FlowInstance.agent()`, `FlowInstance.text_completion()`, `FlowInstance.graph_rag()`, 等等。
所有现有签名和返回类型均已保留

**新增：** 为了实现功能对等，向 REST FlowInstance 添加 `graph_embeddings_query()`：

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

#### 7. 异步 REST 流程 API

模块：`trustgraph-base/trustgraph/api/async_flow.py` (新)

**AsyncFlow 和 AsyncFlowInstance 类：**

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

**主要特性：**
使用 `aiohttp` 或 `httpx` 实现原生异步 HTTP。
方法签名与同步 REST API 相同。
不支持流式传输（使用 `async_socket()` 进行流式传输）。
适用于异步应用程序。

#### 8. Metrics API

模块：`trustgraph-base/trustgraph/api/metrics.py` (新)

**同步 Metrics：**

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

**异步指标：**

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

#### 9. 增强的类型

模块：`trustgraph-base/trustgraph/api/types.py` (已修改)

**新类型：**

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

#### 6. 指标 API

模块：`trustgraph-base/trustgraph/api/metrics.py` (新)

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

### 实现方案

#### 第一阶段：核心 API 增强 (第一周)

1. 向 `Api` 类添加 `socket()`、`bulk()` 和 `metrics()` 方法
2. 实现 WebSocket 和批量客户端的延迟初始化
3. 添加上下文管理器支持 (`__enter__`, `__exit__`)
4. 添加 `close()` 方法进行清理
5. 为 API 类增强添加单元测试
6. 验证向后兼容性

**向后兼容性**: 没有破坏性更改。仅添加了新方法。

#### 第二阶段：WebSocket 客户端 (第二周 - 第三周)

1. 实现 `SocketClient` 类，用于连接管理
2. 实现 `SocketFlowInstance`，方法签名与 `FlowInstance` 相同
3. 添加请求复用支持 (最多 15 个并发)
4. 添加流式响应解析，支持不同的分块类型
5. 添加自动重连逻辑
6. 添加单元和集成测试
7. 记录 WebSocket 使用模式

**向后兼容性**: 仅为新接口。对现有代码没有影响。

#### 第三阶段：流式支持 (第三周 - 第四周)

1. 添加流式分块类型类 (`AgentThought`, `AgentObservation`, `AgentAnswer`, `RAGChunk`)
2. 在 `SocketClient` 中实现流式响应解析
3. 将流式参数添加到 `SocketFlowInstance` 中的所有 LLM 方法
4. 处理流式过程中的错误情况
5. 添加流式功能的单元和集成测试
6. 在文档中添加流式示例

**向后兼容性**: 仅为新接口。现有 REST API 未改变。

#### 第四阶段：批量操作 (第四周 - 第五周)

1. 实现 `BulkClient` 类
2. 添加三元组、嵌入、上下文、对象的批量导入/导出方法
3. 实现基于迭代器的处理，以实现恒定内存
4. 添加进度跟踪 (可选的回调)
5. 添加错误处理，并报告部分成功
6. 添加单元和集成测试
7. 添加批量操作示例

**向后兼容性**: 仅为新接口。对现有代码没有影响。

#### 第五阶段：功能完善与优化 (第五周)

1. 向 REST `FlowInstance` 添加 `graph_embeddings_query()`
2. 实现 `Metrics` 类
3. 添加全面的集成测试
4. 性能基准测试
5. 更新所有文档
6. 创建迁移指南

**向后兼容性**: 仅添加新方法。对现有代码没有影响。

### 数据模型

#### 接口选择

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

#### 流式响应类型

**代理流式传输**:

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

**RAG 流式传输**:

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

**批量操作 (同步)**:

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

**批量操作（异步）**:

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

**异步 REST 示例：**

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

**异步 WebSocket 流式传输示例：**

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
   **Synchronous**:
     `Api.socket()` - Get synchronous WebSocket client
     `Api.bulk()` - Get synchronous bulk operations client
     `Api.metrics()` - Get synchronous metrics client
     `Api.close()` - Close all synchronous connections
     Context manager support (`__enter__`, `__exit__`)
   **Asynchronous**:
     `Api.async_flow()` - Get asynchronous REST flow client
     `Api.async_socket()` - Get asynchronous WebSocket client
     `Api.async_bulk()` - Get asynchronous bulk operations client
     `Api.async_metrics()` - Get asynchronous metrics client
     `Api.aclose()` - Close all asynchronous connections
     Async context manager support (`__aenter__`, `__aexit__`)

2. **Synchronous WebSocket Client**:
   `SocketClient.flow(flow_id)` - Get WebSocket flow instance
   `SocketFlowInstance.agent(..., streaming: bool = False)` - Agent with optional streaming
   `SocketFlowInstance.text_completion(..., streaming: bool = False)` - Text completion with optional streaming
   `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - Graph RAG with optional streaming
   `SocketFlowInstance.document_rag(..., streaming: bool = False)` - Document RAG with optional streaming
   `SocketFlowInstance.prompt(..., streaming: bool = False)` - Prompt with optional streaming
   `SocketFlowInstance.graph_embeddings_query()` - Graph embeddings query
   All other FlowInstance methods with identical signatures

3. **Asynchronous WebSocket Client**:
   `AsyncSocketClient.flow(flow_id)` - Get async WebSocket flow instance
   `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - Async agent with optional streaming
   `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - Async text completion with optional streaming
   `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - Async graph RAG with optional streaming
   `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - Async document RAG with optional streaming
   `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - Async prompt with optional streaming
   `AsyncSocketFlowInstance.graph_embeddings_query()` - Async graph embeddings query
   All other FlowInstance methods as async versions

4. **Synchronous Bulk Operations Client**:
   `BulkClient.import_triples(flow, triples)` - Bulk triple import
   `BulkClient.export_triples(flow)` - Bulk triple export
   `BulkClient.import_graph_embeddings(flow, embeddings)` - Bulk graph embeddings import
   `BulkClient.export_graph_embeddings(flow)` - Bulk graph embeddings export
   `BulkClient.import_document_embeddings(flow, embeddings)` - Bulk document embeddings import
   `BulkClient.export_document_embeddings(flow)` - Bulk document embeddings export
   `BulkClient.import_entity_contexts(flow, contexts)` - Bulk entity contexts import
   `BulkClient.export_entity_contexts(flow)` - Bulk entity contexts export
   `BulkClient.import_objects(flow, objects)` - Bulk objects import

5. **Asynchronous Bulk Operations Client**:
   `AsyncBulkClient.import_triples(flow, triples)` - Async bulk triple import
   `AsyncBulkClient.export_triples(flow)` - Async bulk triple export
   `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - Async bulk graph embeddings import
   `AsyncBulkClient.export_graph_embeddings(flow)` - Async bulk graph embeddings export
   `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - Async bulk document embeddings import
   `AsyncBulkClient.export_document_embeddings(flow)` - Async bulk document embeddings export
   `AsyncBulkClient.import_entity_contexts(flow, contexts)` - Async bulk entity contexts import
   `AsyncBulkClient.export_entity_contexts(flow)` - Async bulk entity contexts export
   `AsyncBulkClient.import_objects(flow, objects)` - Async bulk objects import

6. **Asynchronous REST Flow Client**:
   `AsyncFlow.list()` - Async list all flows
   `AsyncFlow.get(id)` - Async get flow definition
   `AsyncFlow.start(...)` - Async start flow
   `AsyncFlow.stop(id)` - Async stop flow
   `AsyncFlow.id(flow_id)` - Get async flow instance
   `AsyncFlowInstance.agent(...)` - Async agent execution
   `AsyncFlowInstance.text_completion(...)` - Async text completion
   `AsyncFlowInstance.graph_rag(...)` - Async graph RAG
   All other FlowInstance methods as async versions

7. **Metrics Clients**:
   `Metrics.get()` - Synchronous Prometheus metrics
   `AsyncMetrics.get()` - Asynchronous Prometheus metrics

8. **REST Flow API Enhancement**:
   `FlowInstance.graph_embeddings_query()` - Graph embeddings query (sync feature parity)
   `AsyncFlowInstance.graph_embeddings_query()` - Graph embeddings query (async feature parity)

#### Modified APIs

1. **Constructor** (minor enhancement):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   添加了 `token` 参数（可选，用于身份验证）
   如果未指定 `None`（默认）：未使用身份验证
   如果已指定：用作 REST 的 bearer token（`Authorization: Bearer <token>`），用作 WebSocket 的查询参数（`?token=<token>`）
   没有其他更改 - 完全向后兼容

2. **无破坏性更改：**
   所有现有的 REST API 方法未更改
   所有现有的签名均保留
   所有现有的返回类型均保留

### 实现细节

#### 错误处理

**WebSocket 连接错误：**
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

**优雅的降级方案**:
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

**部分流式错误：**
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

#### 资源管理

**上下文管理器支持：**
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

#### 线程和并发

**线程安全**:
每个 `Api` 实例维护自己的连接。
WebSocket 传输使用锁进行线程安全的请求复用。
多个线程可以安全地共享一个 `Api` 实例。
流式迭代器不具备线程安全特性（只能从单个线程消费）。

**异步支持**（未来考虑）：
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

## 安全注意事项

### 身份验证

**令牌参数**:
```python
# No authentication (default)
api = Api(url="http://localhost:8088/")

# With authentication
api = Api(url="http://localhost:8088/", token="mytoken")
```

**REST 传输：**
通过 `Authorization` 头部传递认证令牌
自动应用于所有 REST 请求
格式：`Authorization: Bearer <token>`

**WebSocket 传输：**
通过附加到 WebSocket URL 的查询参数传递认证令牌
在连接建立期间自动应用
格式：`ws://localhost:8088/api/v1/socket?token=<token>`

**实现：**
```python
class SocketClient:
    def _connect(self) -> WebSocket:
        # Construct WebSocket URL with optional token
        ws_url = f"{self.url}/api/v1/socket"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"
        # Connect to WebSocket
        return websocket.connect(ws_url)
```

**示例：**
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")
flow = api.flow().id("default")
# All REST calls include: Authorization: Bearer mytoken

# WebSocket with auth
socket = api.socket()
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### 安全通信

支持 WS (WebSocket) 和 WSS (WebSocket Secure) 两种协议。
WSS 连接的 TLS 证书验证。
可选的开发环境下的证书验证禁用（带有警告）。

### 输入验证

验证 URL 协议 (http, https, ws, wss)。
验证传输参数值。
验证流式传输参数组合。
验证批量导入的数据类型。

## 性能考虑

### 延迟优化

**流式 LLM 操作**:
**首次 token 时间**: ~500 毫秒 (vs ~30 秒 非流式)
**改进**: 性能提升 60 倍
**适用范围**: Agent, Graph RAG, Document RAG, 文本补全, Prompt

**持久连接**:
**连接开销**: 后续请求消除连接开销
**WebSocket 握手**: 一次性成本 (~100 毫秒)
**适用范围**: 使用 WebSocket 传输的所有操作

### 吞吐量优化

**批量操作**:
**三元组导入**: ~10,000 三元组/秒 (vs ~100/秒 使用 REST 单个项目)
**嵌入向量导入**: ~5,000 嵌入向量/秒 (vs ~50/秒 使用 REST 单个项目)
**改进**: 批量操作的吞吐量提升 100 倍

**请求复用**:
**并发请求**: 单个连接可支持最多 15 个并发请求
**连接重用**: 并发操作无需连接开销

### 内存考虑

**流式响应**:
恒定内存使用 (按接收到的块处理)
不缓冲完整的响应
适用于非常长的输出 (>1MB)

**批量操作**:
基于迭代器的处理 (恒定内存)
不将整个数据集加载到内存中
适用于包含数百万项的数据集

### 基准测试 (预期)

| 操作 | REST (现有) | WebSocket (流式传输) | 改进 |
|-----------|----------------|----------------------|-------------|
| Agent (首次 token 时间) | 30 秒 | 0.5 秒 | 60 倍 |
| Graph RAG (首次 token 时间) | 25 秒 | 0.5 秒 | 50 倍 |
| 导入 10K 三元组 | 100 秒 | 1 秒 | 100 倍 |
| 导入 1M 三元组 | 10,000 秒 (2.7 小时) | 100 秒 (1.6 分钟) | 100 倍 |
| 10 个并发小请求 | 5 秒 (顺序) | 0.5 秒 (并行) | 10 倍 |

## 测试策略

### 单元测试

**传输层** (`test_transport.py`):
测试 REST 传输的请求/响应
测试 WebSocket 传输连接
测试 WebSocket 传输重连
测试请求复用
测试流式响应解析
模拟 WebSocket 服务器以进行确定性测试

**API 方法** (`test_flow.py`, `test_library.py`, 等):
使用模拟传输测试新方法
测试流式参数处理
测试批量操作迭代器
测试错误处理

**类型** (`test_types.py`):
测试新的流式分块类型
测试类型序列化/反序列化

### 集成测试

**端到端 REST** (`test_integration_rest.py`):
测试所有操作，针对真实的网关（REST 模式）
验证向后兼容性
测试错误条件

**端到端 WebSocket** (`test_integration_websocket.py`):
测试所有操作，针对真实的网关（WebSocket 模式）
测试流式操作
测试批量操作
测试并发请求
测试连接恢复

**流式服务** (`test_streaming_integration.py`):
测试代理流式传输（想法、观察、答案）
测试 RAG 流式传输（增量分块）
测试文本补全流式传输（逐个 token）
测试提示流式传输
测试流式传输过程中的错误处理

**批量操作** (`test_bulk_integration.py`):
测试三元组的批量导入/导出（1K、10K、100K 个条目）
测试嵌入的批量导入/导出
测试批量操作期间的内存使用情况
测试进度跟踪

### 性能测试

**延迟基准测试** (`test_performance_latency.py`):
测量第一个 token 的时间（流式传输与非流式传输）
测量连接开销（REST 与 WebSocket）
与预期基准进行比较

**吞吐量基准测试** (`test_performance_throughput.py`):
测量批量导入吞吐量
测量请求复用效率
与预期基准进行比较

### 兼容性测试

**向后兼容性** (`test_backward_compatibility.py`):
运行现有测试套件，针对重构的 API
验证没有破坏性更改
测试常见模式的迁移路径

## 迁移计划

### 第一阶段：透明迁移（默认）

**无需任何代码更改**。 现有代码继续工作：

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### 第二阶段：选择加入的流媒体（简单）

**使用 `api.socket()` 接口** 启用流媒体：

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

**关键点：**
REST 和 WebSocket 都使用相同的 URL
相同的函数签名（易于迁移）
只需要添加 `.socket()` 和 `streaming=True`

### 第三阶段：批量操作（新功能）

**使用 `api.bulk()` 接口** 处理大型数据集：

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

### 文档更新

1. **README.md**: 添加流式传输和 WebSocket 示例
2. **API 参考**: 记录所有新的方法和参数
3. **迁移指南**: 启用流式传输的分步指南
4. **示例**: 添加常用模式的示例脚本
5. **性能指南**: 记录预期的性能改进

### 弃用策略

**无弃用**. 所有现有的 API 均继续支持。 这是一个纯粹的增强。

## 时间线

### 第一周：基础
传输抽象层
重构现有的 REST 代码
传输层的单元测试
向后兼容性验证

### 第二周：WebSocket 传输
WebSocket 传输实现
连接管理和重连
请求复用
单元和集成测试

### 第三周：流式传输支持
向 LLM 方法添加流式传输参数
实现流式响应解析
添加流式传输块类型
流式传输集成测试

### 第四周：批量操作
添加批量导入/导出方法
实现基于迭代器的操作
性能测试
批量操作集成测试

### 第五周：功能对齐与文档
添加图嵌入查询
添加指标 API
综合文档
迁移指南
候选版本

### 第六周：发布
最终集成测试
性能基准测试
发布文档
社区公告

**总时长**: 6 周

## 开放问题

### API 设计问题

1. **异步支持**: ✅ **已解决** - 异步支持已包含在初始版本中
   所有接口都具有异步变体：`async_flow()`, `async_socket()`, `async_bulk()`, `async_metrics()`
   为同步和异步 API 提供完全的对称性
   对于现代异步框架（FastAPI, aiohttp）至关重要

2. **进度跟踪**: 批量操作是否应支持进度回调？
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   **建议**: 在第二阶段添加。对于初始发布，这不是关键。

3. **流式传输超时**: 我们应该如何处理流式传输操作的超时？
   **建议**: 使用与非流式传输相同的超时时间，但在接收每个数据块时重置。

4. **数据块缓冲**: 我们应该缓冲数据块，还是立即返回？
   **建议**: 立即返回，以获得最低延迟。

5. **WebSocket 上的全局服务**: `api.socket()` 是否应该支持全局服务（库、知识、集合、配置），或者仅支持作用域服务？
   **建议**: 仅从作用域服务开始（流式传输相关）。如果需要，可以在第二阶段添加全局服务。

### 实现问题

1. **WebSocket 库**: 我们应该使用 `websockets`、`websocket-client` 还是 `aiohttp`？
   **建议**: `websockets` (异步，成熟，维护良好)。使用 `asyncio.run()` 包装成同步接口。

2. **连接池**: 我们是否应该支持多个并发的 `Api` 实例共享连接池？
   **建议**: 延期到第二阶段。最初，每个 `Api` 实例都有自己的连接。

3. **连接重用**: `SocketClient` 和 `BulkClient` 是否应该共享同一个 WebSocket 连接，或者使用单独的连接？
   **建议**: 使用单独的连接。实现更简单，职责分离更清晰。

4. **延迟连接 vs 立即连接**: WebSocket 连接是在 `api.socket()` 中建立，还是在首次请求时建立？
   **建议**: 延迟到首次请求时建立。避免连接开销，如果用户仅使用 REST 方法。

### 测试问题

1. **模拟网关**: 我们是否应该创建一个轻量级的模拟网关进行测试，或者直接测试真实网关？
   **建议**: 都应该。使用模拟进行单元测试，使用真实网关进行集成测试。

2. **性能回归测试**: 我们是否应该将自动化性能回归测试添加到 CI 中？
   **建议**: 是的，但应设置宽松的阈值，以考虑 CI 环境的差异。

## 引用

### 相关技术规范
`docs/tech-specs/streaming-llm-responses.md` - 网关中的流式传输实现
`docs/tech-specs/rag-streaming-support.md` - RAG 流式传输支持

### 实现文件
`trustgraph-base/trustgraph/api/` - Python API 源代码
`trustgraph-flow/trustgraph/gateway/` - 网关源代码
`trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - WebSocket 多路复用参考实现

### 文档
`docs/apiSpecification.md` - 完整的 API 参考
`docs/api-status-summary.md` - API 状态摘要
`README.websocket` - WebSocket 协议文档
`STREAMING-IMPLEMENTATION-NOTES.txt` - 流式传输实现说明

### 外部库
`websockets` - Python WebSocket 库 (https://websockets.readthedocs.io/)
`requests` - Python HTTP 库 (现有)
