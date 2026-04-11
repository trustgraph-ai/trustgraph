# Python API Refactor Technical Specification

## Overview

This specification describes a comprehensive refactor of the TrustGraph Python API client library to achieve feature parity with the API Gateway and add support for modern real-time communication patterns.

The refactor addresses four primary use cases:

1. **Streaming LLM Interactions**: Enable real-time streaming of LLM responses (agent, graph RAG, document RAG, text completion, prompts) with ~60x lower latency (500ms vs 30s for first token)
2. **Bulk Data Operations**: Support efficient bulk import/export of triples, graph embeddings, and document embeddings for large-scale knowledge graph management
3. **Feature Parity**: Ensure every API Gateway endpoint has a corresponding Python API method, including graph embeddings query
4. **Persistent Connections**: Enable WebSocket-based communication for multiplexed requests and reduced connection overhead

## Goals

**Feature Parity**: Every Gateway API service has a corresponding Python API method
**Streaming Support**: All streaming-capable services (agent, RAG, text completion, prompt) support streaming in Python API
**WebSocket Transport**: Add optional WebSocket transport layer for persistent connections and multiplexing
**Bulk Operations**: Add efficient bulk import/export for triples, graph embeddings, and document embeddings
**Full Async Support**: Complete async/await implementation for all interfaces (REST, WebSocket, bulk operations, metrics)
**Backward Compatibility**: Existing code continues to work without modification
**Type Safety**: Maintain type-safe interfaces with dataclasses and type hints
**Progressive Enhancement**: Streaming and async are opt-in via explicit interface selection
**Performance**: Achieve 60x latency improvement for streaming operations
**Modern Python**: Support for both sync and async paradigms for maximum flexibility

## Background

### Current State

The Python API (`trustgraph-base/trustgraph/api/`) is a REST-only client library with the following modules:

`flow.py`: Flow management and flow-scoped services (50 methods)
`library.py`: Document library operations (9 methods)
`knowledge.py`: KG core management (4 methods)
`collection.py`: Collection metadata (3 methods)
`config.py`: Configuration management (6 methods)
`types.py`: Data type definitions (5 dataclasses)

**Total Operations**: 50/59 (85% coverage)

### Current Limitations

**Missing Operations**:
Graph embeddings query (semantic search over graph entities)
Bulk import/export for triples, graph embeddings, document embeddings, entity contexts, objects
Metrics endpoint

**Missing Capabilities**:
Streaming support for LLM services
WebSocket transport
Multiplexed concurrent requests
Persistent connections

**Performance Issues**:
High latency for LLM interactions (~30s time-to-first-token)
Inefficient bulk data transfer (REST request per item)
Connection overhead for multiple sequential operations

**User Experience Issues**:
No real-time feedback during LLM generation
Cannot cancel long-running LLM operations
Poor scalability for bulk operations

### Impact

The November 2024 streaming enhancement to the Gateway API provided 60x latency improvement (500ms vs 30s first token) for LLM interactions, but Python API users cannot leverage this capability. This creates a significant experience gap between Python and non-Python users.

## Technical Design

### Architecture

The refactored Python API uses a **modular interface approach** with separate objects for different communication patterns. All interfaces are available in both **synchronous and asynchronous** variants:

1. **REST Interface** (existing, enhanced)
   **Sync**: `api.flow()`, `api.library()`, `api.knowledge()`, `api.collection()`, `api.config()`
   **Async**: `api.async_flow()`
   Synchronous/asynchronous request/response
   Simple connection model
   Default for backward compatibility

2. **WebSocket Interface** (new)
   **Sync**: `api.socket()`
   **Async**: `api.async_socket()`
   Persistent connection
   Multiplexed requests
   Streaming support
   Same method signatures as REST where functionality overlaps

3. **Bulk Operations Interface** (new)
   **Sync**: `api.bulk()`
   **Async**: `api.async_bulk()`
   WebSocket-based for efficiency
   Iterator/AsyncIterator-based import/export
   Handles large datasets

4. **Metrics Interface** (new)
   **Sync**: `api.metrics()`
   **Async**: `api.async_metrics()`
   Prometheus metrics access

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

**Основные принципы проектирования**:
**Одинаковый URL для всех интерфейсов**: `Api(url="http://localhost:8088/")` работает для всех.
**Симметрия синхронной/асинхронной работы**: Каждый интерфейс имеет как синхронные, так и асинхронные варианты с идентичными сигнатурами методов.
**Идентичные сигнатуры**: Там, где функциональность перекрывается, сигнатуры методов одинаковы для REST и WebSocket, а также для синхронных и асинхронных операций.
**Постепенное улучшение**: Выберите интерфейс в зависимости от потребностей (REST для простых задач, WebSocket для потоковой передачи данных, Bulk для больших наборов данных, асинхронный режим для современных фреймворков).
**Явное указание**: `api.socket()` указывает на WebSocket, `api.async_socket()` указывает на асинхронный WebSocket.
**Обратная совместимость**: Существующий код не изменяется.

### Компоненты

#### 1. Класс API (модифицированный)

Модуль: `trustgraph-base/trustgraph/api/api.py`

**Улучшенный класс API**:

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

#### 2. Синхронный WebSocket-клиент

Модуль: `trustgraph-base/trustgraph/api/socket_client.py` (новый)

**Класс SocketClient**:

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

**Основные характеристики:**
Ленивое подключение (устанавливается только при отправке первого запроса)
Мультиплексирование запросов (до 15 одновременных)
Автоматическое переподключение при разрыве соединения
Потоковая обработка ответа
Потокобезопасная работа
Синхронная обертка вокруг асинхронной библиотеки веб-сокетов

#### 3. Асинхронный клиент WebSocket

Модуль: `trustgraph-base/trustgraph/api/async_socket_client.py` (новый)

**Класс AsyncSocketClient:**

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

**Основные характеристики:**
Встроенная поддержка async/await
Эффективно для асинхронных приложений (FastAPI, aiohttp)
Отсутствие блокировок потоков
Тот же интерфейс, что и у синхронной версии
AsyncIterator для потоковой передачи

#### 4. Клиент для синхронных пакетных операций

Модуль: `trustgraph-base/trustgraph/api/bulk_client.py` (новый)

**Класс BulkClient:**

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

**Основные характеристики:**
Основан на итераторах для постоянного использования памяти.
Выделенные WebSocket-соединения для каждой операции.
Отслеживание прогресса (необязательный обратный вызов).
Обработка ошибок с частичным сообщением об успехе.

#### 5. Асинхронный клиент массовых операций

Модуль: `trustgraph-base/trustgraph/api/async_bulk_client.py` (новый)

**Класс AsyncBulkClient:**

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

**Основные характеристики:**
Основан на AsyncIterator для постоянного использования памяти.
Эффективен для асинхронных приложений.
Поддержка нативных асинхронных операций async/await.
Тот же интерфейс, что и у синхронной версии.

#### 6. REST Flow API (Синхронный - Без изменений)

Модуль: `trustgraph-base/trustgraph/api/flow.py`

REST Flow API остается **полностью неизменным** для обеспечения обратной совместимости. Все существующие методы продолжают работать:

`Flow.list()`, `Flow.start()`, `Flow.stop()` и т.д.
`FlowInstance.agent()`, `FlowInstance.text_completion()`, `FlowInstance.graph_rag()` и т.д.
Все существующие сигнатуры и типы возвращаемых значений сохранены.

**Новое:** Добавьте `graph_embeddings_query()` в REST FlowInstance для обеспечения соответствия функциональности:

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

#### 7. Асинхронный REST API

Модуль: `trustgraph-base/trustgraph/api/async_flow.py` (новый)

**Классы AsyncFlow и AsyncFlowInstance**:

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

**Основные характеристики:**
Асинхронные HTTP-запросы с использованием `aiohttp` или `httpx`
Те же сигнатуры методов, что и у синхронного REST API
Без потоковой передачи (используйте `async_socket()` для потоковой передачи)
Эффективно для асинхронных приложений

#### 8. API метрик

Модуль: `trustgraph-base/trustgraph/api/metrics.py` (новый)

**Синхронные метрики:**

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

**Асинхронные метрики**:

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

#### 9. Улучшенные типы

Модуль: `trustgraph-base/trustgraph/api/types.py` (изменен)

**Новые типы**:

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

#### 6. API метрик

Модуль: `trustgraph-base/trustgraph/api/metrics.py` (новый)

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

### Подход к реализации

#### Этап 1: Улучшение основного API (1 неделя)

1. Добавить методы `socket()`, `bulk()` и `metrics()` в класс `Api`
2. Реализовать ленивую инициализацию для WebSocket и пакетных клиентов
3. Добавить поддержку менеджеров контекста (`__enter__`, `__exit__`)
4. Добавить метод `close()` для очистки
5. Добавить модульные тесты для улучшений API
6. Проверить обратную совместимость

**Обратная совместимость**: Отсутствуют критические изменения. Только новые методы.

#### Этап 2: WebSocket клиент (2-3 недели)

1. Реализовать класс `SocketClient` с управлением подключением
2. Реализовать `SocketFlowInstance` с теми же сигнатурами методов, что и у `FlowInstance`
3. Добавить поддержку множественной отправки запросов (до 15 одновременных)
4. Добавить парсинг потоковых ответов для различных типов фрагментов
5. Добавить логику автоматического переподключения
6. Добавить модульные и интеграционные тесты
7. Добавить документацию по использованию WebSocket

**Обратная совместимость**: Новый интерфейс. Отсутствует влияние на существующий код.

#### Этап 3: Поддержка потоковой передачи (3-4 недели)

1. Добавить классы для типов фрагментов потоковой передачи (`AgentThought`, `AgentObservation`, `AgentAnswer`, `RAGChunk`)
2. Реализовать парсинг потоковых ответов в `SocketClient`
3. Добавить параметр потоковой передачи ко всем методам LLM в `SocketFlowInstance`
4. Обрабатывать ошибки во время потоковой передачи
5. Добавить модульные и интеграционные тесты для потоковой передачи
6. Добавить примеры потоковой передачи в документацию

**Обратная совместимость**: Новый интерфейс. Существующий REST API не изменен.

#### Этап 4: Пакетные операции (4-5 недели)

1. Реализовать класс `BulkClient`
2. Добавить методы пакетного импорта/экспорта для троек, векторов, контекстов, объектов
3. Реализовать обработку с использованием итераторов для экономии памяти
4. Добавить отслеживание прогресса (необязательный обратный вызов)
5. Добавить обработку ошибок с отчетом о частичном успехе
6. Добавить модульные и интеграционные тесты
7. Добавить примеры пакетных операций

**Обратная совместимость**: Новый интерфейс. Отсутствует влияние на существующий код.

#### Этап 5: Обеспечение совместимости и доработка (5 неделя)

1. Добавить `graph_embeddings_query()` в REST `FlowInstance`
2. Реализовать класс `Metrics`
3. Добавить комплексные интеграционные тесты
4. Проведение бенчмаркинга производительности
5. Обновить всю документацию
6. Создать руководство по миграции

**Обратная совместимость**: Только новые методы. Отсутствует влияние на существующий код.

### Модели данных

#### Выбор интерфейса

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

#### Типы ответов потоковой передачи

**Потоковая передача от агента**:

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

**Потоковая передача RAG**:

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

**Массовые операции (синхронные):**

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

**Массовые операции (асинхронные):**

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

**Пример асинхронного REST:**

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

**Пример асинхронной потоковой передачи данных через WebSocket:**

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

1. **Класс API для основных операций**:
   **Синхронный**:
     `Api.socket()` - Получить синхронного клиента WebSocket
     `Api.bulk()` - Получить синхронного клиента для пакетных операций
     `Api.metrics()` - Получить синхронного клиента для метрик
     `Api.close()` - Закрыть все синхронные соединения
     Поддержка менеджера контекста (`__enter__`, `__exit__`)
   **Асинхронный**:
     `Api.async_flow()` - Получить асинхронного клиента REST flow
     `Api.async_socket()` - Получить асинхронного клиента WebSocket
     `Api.async_bulk()` - Получить асинхронного клиента для пакетных операций
     `Api.async_metrics()` - Получить асинхронного клиента для метрик
     `Api.aclose()` - Закрыть все асинхронные соединения
     Поддержка асинхронного менеджера контекста (`__aenter__`, `__aexit__`)

2. **Синхронный клиент WebSocket**:
   `SocketClient.flow(flow_id)` - Получить экземпляр WebSocket flow
   `SocketFlowInstance.agent(..., streaming: bool = False)` - Агент с опциональной потоковой передачей
   `SocketFlowInstance.text_completion(..., streaming: bool = False)` - Завершение текста с опциональной потоковой передачей
   `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - Graph RAG с опциональной потоковой передачей
   `SocketFlowInstance.document_rag(..., streaming: bool = False)` - Document RAG с опциональной потоковой передачей
   `SocketFlowInstance.prompt(..., streaming: bool = False)` - Prompt с опциональной потоковой передачей
   `SocketFlowInstance.graph_embeddings_query()` - Запрос graph embeddings
   Все остальные методы FlowInstance с идентичными сигнатурами

3. **Асинхронный клиент WebSocket**:
   `AsyncSocketClient.flow(flow_id)` - Получить асинхронный экземпляр WebSocket flow
   `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - Асинхронный агент с опциональной потоковой передачей
   `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - Асинхронное завершение текста с опциональной потоковой передачей
   `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - Асинхронный graph RAG с опциональной потоковой передачей
   `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - Асинхронный document RAG с опциональной потоковой передачей
   `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - Асинхронный prompt с опциональной потоковой передачей
   `AsyncSocketFlowInstance.graph_embeddings_query()` - Асинхронный запрос graph embeddings
   Все остальные методы FlowInstance как асинхронные версии

4. **Синхронный клиент для пакетных операций**:
   `BulkClient.import_triples(flow, triples)` - Пакетный импорт триплетов
   `BulkClient.export_triples(flow)` - Пакетный экспорт триплетов
   `BulkClient.import_graph_embeddings(flow, embeddings)` - Пакетный импорт graph embeddings
   `BulkClient.export_graph_embeddings(flow)` - Пакетный экспорт graph embeddings
   `BulkClient.import_document_embeddings(flow, embeddings)` - Пакетный импорт document embeddings
   `BulkClient.export_document_embeddings(flow)` - Пакетный экспорт document embeddings
   `BulkClient.import_entity_contexts(flow, contexts)` - Пакетный импорт entity contexts
   `BulkClient.export_entity_contexts(flow)` - Пакетный экспорт entity contexts
   `BulkClient.import_objects(flow, objects)` - Пакетный импорт объектов

5. **Асинхронный клиент для пакетных операций**:
   `AsyncBulkClient.import_triples(flow, triples)` - Асинхронный пакетный импорт триплетов
   `AsyncBulkClient.export_triples(flow)` - Асинхронный пакетный экспорт триплетов
   `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - Асинхронный пакетный импорт graph embeddings
   `AsyncBulkClient.export_graph_embeddings(flow)` - Асинхронный пакетный экспорт graph embeddings
   `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - Асинхронный пакетный импорт document embeddings
   `AsyncBulkClient.export_document_embeddings(flow)` - Асинхронный пакетный экспорт document embeddings
   `AsyncBulkClient.import_entity_contexts(flow, contexts)` - Асинхронный пакетный импорт entity contexts
   `AsyncBulkClient.export_entity_contexts(flow)` - Асинхронный пакетный экспорт entity contexts
   `AsyncBulkClient.import_objects(flow, objects)` - Асинхронный пакетный импорт объектов

6. **Асинхронный клиент REST Flow API**:
   `AsyncFlow.list()` - Асинхронный список всех flows
   `AsyncFlow.get(id)` - Асинхронное получение определения flow
   `AsyncFlow.start(...)` - Асинхронный запуск flow
   `AsyncFlow.stop(id)` - Асинхронная остановка flow
   `AsyncFlow.id(flow_id)` - Получить асинхронный экземпляр flow
   `AsyncFlowInstance.agent(...)` - Асинхронное выполнение агента
   `AsyncFlowInstance.text_completion(...)` - Асинхронное завершение текста
   `AsyncFlowInstance.graph_rag(...)` - Асинхронный graph RAG
   Все остальные методы FlowInstance как асинхронные версии

7. **Клиенты для метрик**:
   `Metrics.get()` - Синхронные метрики Prometheus
   `AsyncMetrics.get()` - Асинхронные метрики Prometheus

8. **Улучшение REST Flow API**:
   `FlowInstance.graph_embeddings_query()` - Запрос graph embeddings (синхронная функциональность)
   `AsyncFlowInstance.graph_embeddings_query()` - Запрос graph embeddings (асинхронная функциональность)

#### Измененные API

1. **Конструктор** (незначительное улучшение):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   Добавлен параметр `token` (необязательный, для аутентификации).
   Если `None` не указан (по умолчанию): аутентификация не используется.
   Если указан: используется как токен доступа для REST (`Authorization: Bearer <token>`), параметр запроса для WebSocket (`?token=<token>`).
   Других изменений нет - полностью обратно совместимо.

2. **Отсутствие изменений, нарушающих обратную совместимость**:
   Все существующие методы REST API не изменены.
   Все существующие сигнатуры сохранены.
   Все существующие типы возвращаемых значений сохранены.

### Детали реализации

#### Обработка ошибок

**Ошибки подключения WebSocket**:
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

**Плавный переход на резервный вариант**:
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

**Частичные ошибки потоковой передачи**:
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

#### Управление ресурсами

**Поддержка контекстных менеджеров**:
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

#### Многопоточность и параллелизм

**Потоковая безопасность**:
Каждый экземпляр `Api` поддерживает собственное соединение.
Транспорт WebSocket использует блокировки для потокобезопасной мультиплексирования запросов.
Несколько потоков могут безопасно совместно использовать экземпляр `Api`.
Потоковые итераторы не являются потокобезопасными (используйте из одного потока).

**Асинхронная поддержка** (планируется к реализации в будущем):
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

## Соображения безопасности

### Аутентификация

**Параметр токена**:
```python
# No authentication (default)
api = Api(url="http://localhost:8088/")

# With authentication
api = Api(url="http://localhost:8088/", token="mytoken")
```

**REST-транспорт:**
Токен передается через заголовок `Authorization`
Применяется автоматически ко всем REST-запросам
Формат: `Authorization: Bearer <token>`

**WebSocket-транспорт:**
Токен передается через параметр запроса, добавляемый к URL WebSocket
Применяется автоматически во время установления соединения
Формат: `ws://localhost:8088/api/v1/socket?token=<token>`

**Реализация:**
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

**Пример:**
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")
flow = api.flow().id("default")
# All REST calls include: Authorization: Bearer mytoken

# WebSocket with auth
socket = api.socket()
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### Безопасная связь

Поддержка схем WS (WebSocket) и WSS (WebSocket Secure).
Проверка сертификатов TLS для соединений WSS.
Опциональное отключение проверки сертификатов для разработки (с предупреждением).

### Валидация входных данных

Проверка схем URL (http, https, ws, wss).
Проверка значений параметров передачи данных.
Проверка комбинаций параметров потоковой передачи.
Проверка типов данных для массового импорта.

## Вопросы производительности

### Оптимизация задержки

**Потоковые операции с LLM**:
**Время получения первого токена**: ~500 мс (против ~30 секунд без потоковой передачи).
**Улучшение**: Воспринимаемая производительность увеличена в 60 раз.
**Применимо к**: Agent, Graph RAG, Document RAG, Text Completion, Prompt.

**Постоянные соединения**:
**Накладные расходы на соединение**: Устранены для последующих запросов.
**Установление WebSocket-соединения**: Единоразовая операция (~100 мс).
**Применимо к**: Всем операциям при использовании транспорта WebSocket.

### Оптимизация пропускной способности

**Массовые операции**:
**Импорт триплетов**: ~10 000 триплетов/секунду (против ~100/секунду с REST для каждого элемента).
**Импорт векторов**: ~5 000 векторов/секунду (против ~50/секунду с REST для каждого элемента).
**Улучшение**: Пропускная способность увеличена в 100 раз для массовых операций.

**Множественная отправка запросов**:
**Параллельные запросы**: До 15 одновременных запросов через одно соединение.
**Повторное использование соединения**: Отсутствуют накладные расходы на соединение для параллельных операций.

### Вопросы использования памяти

**Потоковые ответы**:
Постоянное использование памяти (обработка фрагментов по мере их поступления).
Отсутствует буферизация полного ответа.
Подходит для очень длинных ответов (>1 МБ).

**Массовые операции**:
Обработка с использованием итераторов (постоянное использование памяти).
Отсутствует загрузка всего набора данных в память.
Подходит для наборов данных с миллионами элементов.

### Результаты тестирования (ожидаемые)

| Операция | REST (существующий) | WebSocket (потоковая передача) | Улучшение |
|-----------|----------------|----------------------|-------------|
| Agent (время получения первого токена) | 30с | 0.5с | 60x |
| Graph RAG (время получения первого токена) | 25с | 0.5с | 50x |
| Импорт 10K триплетов | 100с | 1с | 100x |
| Импорт 1M триплетов | 10 000с (2.7ч) | 100с (1.6м) | 100x |
| 10 параллельных небольших запросов | 5с (последовательно) | 0.5с (параллельно) | 10x |

## Стратегия тестирования

### Модульные тесты

**Транспортный уровень** (`test_transport.py`):
Проверка запросов и ответов REST
Проверка подключения WebSocket
Проверка повторного подключения WebSocket
Проверка мультиплексирования запросов
Проверка разбора потоковых ответов
Эмуляция WebSocket-сервера для детерминированных тестов

**Методы API** (`test_flow.py`, `test_library.py` и т.д.):
Проверка новых методов с использованием эмулированного транспорта
Проверка обработки потоковых параметров
Проверка итераторов для пакетных операций
Проверка обработки ошибок

**Типы данных** (`test_types.py`):
Проверка новых типов данных для потоковой передачи
Проверка сериализации/десериализации типов данных

### Интеграционные тесты

**Комплексные тесты REST** (`test_integration_rest.py`):
Проверка всех операций против реального шлюза (режим REST)
Проверка обратной совместимости
Проверка условий ошибок

**Комплексные тесты WebSocket** (`test_integration_websocket.py`):
Проверка всех операций против реального шлюза (режим WebSocket)
Проверка операций потоковой передачи
Проверка пакетных операций
Проверка одновременных запросов
Проверка восстановления соединения

**Сервисы потоковой передачи** (`test_streaming_integration.py`):
Проверка потоковой передачи данных агента (мысли, наблюдения, ответы)
Проверка потоковой передачи данных RAG (инкрементные фрагменты)
Проверка потоковой передачи текста (по токенам)
Проверка потоковой передачи запросов
Проверка обработки ошибок во время потоковой передачи

**Пакетные операции** (`test_bulk_integration.py`):
Проверка пакетного импорта/экспорта троек (1K, 10K, 100K элементов)
Проверка пакетного импорта/экспорта векторных представлений
Проверка использования памяти во время пакетных операций
Проверка отслеживания прогресса

### Тесты производительности

**Бенчмарки задержки** (`test_performance_latency.py`):
Измерение времени до первого токена (потоковая передача против не потоковой передачи)
Измерение накладных расходов на подключение (REST против WebSocket)
Сравнение с ожидаемыми результатами

**Бенчмарки пропускной способности** (`test_performance_throughput.py`):
Измерение пропускной способности пакетного импорта
Измерение эффективности мультиплексирования запросов
Сравнение с ожидаемыми результатами

### Тесты совместимости

**Обратная совместимость** (`test_backward_compatibility.py`):
Запуск существующего набора тестов против рефакторингованного API
Проверка отсутствия изменений, нарушающих обратную совместимость
Проверка пути миграции для распространенных сценариев

## План миграции

### Этап 1: Прозрачная миграция (по умолчанию)

**Не требуется внесения изменений в код**. Существующий код продолжает работать:

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### Фаза 2: Опциональная потоковая передача (простая)

**Используйте интерфейс `api.socket()`** для включения потоковой передачи:

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

**Основные моменты:**
Один и тот же URL для REST и WebSocket.
Одинаковые сигнатуры методов (простое переключение).
Просто добавьте `.socket()` и `streaming=True`.

### Фаза 3: Массовые операции (Новая функциональность)

**Используйте интерфейс `api.bulk()`** для больших наборов данных:

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

### Обновления документации

1. **README.md**: Добавить примеры потоковой передачи и WebSockets
2. **Справочник API**: Описать все новые методы и параметры
3. **Руководство по миграции**: Пошаговое руководство по включению потоковой передачи
4. **Примеры**: Добавить примеры скриптов для распространенных сценариев
5. **Руководство по производительности**: Описать ожидаемые улучшения производительности

### Политика устаревания

**Нет устаревших функций**. Все существующие API остаются поддерживаемыми. Это чистое улучшение.

## План

### Неделя 1: Основа
Абстрактный слой транспорта
Рефакторинг существующего REST-кода
Юнит-тесты для слоя транспорта
Проверка обратной совместимости

### Неделя 2: Транспорт WebSockets
Реализация транспорта WebSockets
Управление соединениями и повторное подключение
Мультиплексирование запросов
Юнит-тесты и интеграционные тесты

### Неделя 3: Поддержка потоковой передачи
Добавить параметр потоковой передачи к методам LLM
Реализовать разбор потоковых ответов
Добавить типы потоковых фрагментов
Интеграционные тесты потоковой передачи

### Неделя 4: Массовые операции
Добавить методы массового импорта/экспорта
Реализовать операции на основе итераторов
Тестирование производительности
Интеграционные тесты массовых операций

### Неделя 5: Функциональная совместимость и документация
Добавить запрос графовых вложений
Добавить API метрик
Комплексная документация
Руководство по миграции
Кандидат в релиз

### Неделя 6: Релиз
Заключительное интеграционное тестирование
Бенчмаркинг производительности
Документация к релизу
Объявление для сообщества

**Общая продолжительность**: 6 недель

## Открытые вопросы

### Вопросы проектирования API

1. **Поддержка асинхронности**: ✅ **РЕШЕНО** - Полная поддержка асинхронности включена в первоначальный релиз
   Все интерфейсы имеют асинхронные варианты: `async_flow()`, `async_socket()`, `async_bulk()`, `async_metrics()`
   Обеспечивает полную симметрию между синхронными и асинхронными API
   Необходимо для современных асинхронных фреймворков (FastAPI, aiohttp)

2. **Отслеживание прогресса**: Должны ли массовые операции поддерживать обратные вызовы для отслеживания прогресса?
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   **Рекомендация**: Добавить на Фазе 2. Не критично для первоначального релиза.

3. **Таймаут потоковой передачи**: Как нам обрабатывать таймауты для операций потоковой передачи?
   **Рекомендация**: Использовать тот же таймаут, что и для не-потоковой передачи, но сбрасывать его при получении каждого фрагмента.

4. **Буферизация фрагментов**: Следует ли нам буферизовать фрагменты или выдавать их немедленно?
   **Рекомендация**: Выдавать немедленно для достижения минимальной задержки.

5. **Глобальные сервисы через WebSocket**: Должен ли `api.socket()` поддерживать глобальные сервисы (библиотека, знания, коллекция, конфигурация) или только сервисы, привязанные к потоку?
   **Рекомендация**: Начать только с сервисов, привязанных к потоку (где важна потоковая передача). Добавить глобальные сервисы, если это потребуется, на Фазе 2.

### Вопросы реализации

1. **Библиотека WebSocket**: Следует ли нам использовать `websockets`, `websocket-client` или `aiohttp`?
   **Рекомендация**: `websockets` (асинхронная, зрелая, хорошо поддерживаемая). Обернуть в синхронный интерфейс с использованием `asyncio.run()`.

2. **Пул соединений**: Следует ли нам поддерживать несколько одновременных экземпляров `Api`, использующих общий пул соединений?
   **Рекомендация**: Отложить до Фазы 2. Изначально каждый экземпляр `Api` имеет свои собственные соединения.

3. **Повторное использование соединений**: Должны ли `SocketClient` и `BulkClient` использовать одно и то же WebSocket-соединение или отдельные соединения?
   **Рекомендация**: Отдельные соединения. Более простая реализация, более четкое разделение ответственности.

4. **Ленивое vs. Активное соединение**: Должно ли WebSocket-соединение устанавливаться в `api.socket()` или при первом запросе?
   **Рекомендация**: Ленивое (при первом запросе). Избегает накладных расходов на соединение, если пользователь использует только методы REST.

### Вопросы тестирования

1. **Моковый шлюз**: Следует ли нам создать легковесный моковый шлюз для тестирования или тестировать против реального шлюза?
   **Рекомендация**: Оба варианта. Использовать моки для модульных тестов и реальный шлюз для интеграционных тестов.

2. **Автоматизированные тесты регрессии производительности**: Следует ли нам добавить автоматизированные тесты регрессии производительности в CI?
   **Рекомендация**: Да, но с достаточно большими допусками, чтобы учитывать изменчивость среды CI.

## Ссылки

### Связанные технические спецификации
`docs/tech-specs/streaming-llm-responses.md` - Реализация потоковой передачи в шлюзе
`docs/tech-specs/rag-streaming-support.md` - Поддержка потоковой передачи RAG

### Файлы реализации
`trustgraph-base/trustgraph/api/` - Исходный код API на Python
`trustgraph-flow/trustgraph/gateway/` - Исходный код шлюза
`trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - Пример реализации мультиплексора WebSocket

### Документация
`docs/apiSpecification.md` - Полная справочная документация API
`docs/api-status-summary.md` - Краткое описание статуса API
`README.websocket` - Документация протокола WebSocket
`STREAMING-IMPLEMENTATION-NOTES.txt` - Заметки о реализации потоковой передачи

### Внешние библиотеки
`websockets` - Библиотека WebSocket на Python (https://websockets.readthedocs.io/)
`requests` - HTTP-библиотека на Python (существующая)
