---
layout: default
title: "Python API Refactor Technical Specification"
parent: "Hebrew (Beta)"
---

# Python API Refactor Technical Specification

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

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

**עקרונות עיצוב מרכזיים:**
**כתובת URL זהה לכל הממשקים:** `Api(url="http://localhost:8088/")` עובד עבור כל
**סימטריה בין סינכרוני/אסינכרוני:** לכל ממשק יש גרסאות סינכרוניות ואסינכרוניות עם חתימות מתודות זהות.
**חתימות זהות:** כאשר יש חפיפה בפונקציונליות, חתימות המתודות זהות בין REST ו-WebSocket, סינכרוני ואסינכרוני.
**שיפור הדרגתי:** בחרו ממשק בהתאם לצרכים (REST לפשוט, WebSocket לסטרימינג, Bulk עבור מערכי נתונים גדולים, אסינכרוני עבור מסגרות עבודה מודרניות).
**כוונת שימוש מפורשת:** `api.socket()` מציין WebSocket, `api.async_socket()` מציין WebSocket אסינכרוני.
**תואם לאחור:** קוד קיים אינו משתנה.

### רכיבים

#### 1. מחלקת API מרכזית (משופרת)

מודול: `trustgraph-base/trustgraph/api/api.py`

**מחלקת API משופרת:**

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

#### 2. לקוח WebSocket סינכרוני

מודול: `trustgraph-base/trustgraph/api/socket_client.py` (חדש)

**מחלקה SocketClient**:

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

**תכונות עיקריות:**
חיבור עצלני (מתחבר רק כאשר מתקבלת בקשה ראשונה)
ריבוב בקשות (עד 15 בקשות בו-זמנית)
חיבור מחדש אוטומטי במקרה של ניתוק
ניתוח תגובה בשיטת סטרימינג
פעולה בטוחה לשימוש ב-threads
עטיפה סינכרונית עבור ספריית websockets אסינכרונית

#### 3. לקוח WebSocket אסינכרוני

מודול: `trustgraph-base/trustgraph/api/async_socket_client.py` (חדש)

**מחלקה AsyncSocketClient:**

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

**תכונות עיקריות:**
תמיכה מובנית ב-async/await
יעיל עבור יישומים אסינכרוניים (FastAPI, aiohttp)
ללא חסימת תהליכים
ממשק זהה לגרסה הסינכרונית
AsyncIterator עבור סטרימינג

#### 4. לקוח לפעולות סינכרוניות מרובות

מודול: `trustgraph-base/trustgraph/api/bulk_client.py` (חדש)

**מחלקה BulkClient:**

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

**תכונות עיקריות:**
מבוסס על איטרטור לשימוש קבוע בזיכרון
חיבורי WebSocket ייעודיים לכל פעולה
מעקב אחר התקדמות (אופציונלי, באמצעות פונקציית החזרה)
טיפול בשגיאות עם דיווח על הצלחה חלקית

#### 5. לקוח לפעולות אסינכרוניות מרובות

מודול: `trustgraph-base/trustgraph/api/async_bulk_client.py` (חדש)

**מחלקה: AsyncBulkClient**:

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

**תכונות עיקריות:**
מבוסס על AsyncIterator לשימוש קבוע בזיכרון
יעיל עבור יישומים אסינכרוניים
תמיכה מובנית ב-async/await
אותו ממשק כמו הגרסה הסינכרונית

#### 6. ממשק REST Flow (סינכרוני - ללא שינוי)

מודול: `trustgraph-base/trustgraph/api/flow.py`

ממשק REST Flow נשאר **ללא שינוי מוחלט** לצורך תאימות לאחור. כל השיטות הקיימות ממשיכות לעבוד:

`Flow.list()`, `Flow.start()`, `Flow.stop()`, וכו'.
`FlowInstance.agent()`, `FlowInstance.text_completion()`, `FlowInstance.graph_rag()`, וכו'.
כל החתימות וטיפוסי ההחזרה הקיימים נשמרו

**חדש:** הוספת `graph_embeddings_query()` ל-REST FlowInstance לצורך התאמה:

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

#### 7. ממשק REST אסינכרוני

מודול: `trustgraph-base/trustgraph/api/async_flow.py` (חדש)

**מחלקות AsyncFlow ו-AsyncFlowInstance**:

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

**תכונות עיקריות:**
שימוש ב-HTTP אסינכרוני באמצעות `aiohttp` או `httpx`
אותם חתימות מתודות כמו ב-API REST סינכרוני
ללא סטרימינג (יש להשתמש ב-`async_socket()` עבור סטרימינג)
יעיל עבור יישומים אסינכרוניים

#### 8. ממשק API למדדים

מודול: `trustgraph-base/trustgraph/api/metrics.py` (חדש)

**מדדים סינכרוניים:**

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

**מדדי אסינכרוניים:**

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

#### 9. סוגים משופרים

מודול: `trustgraph-base/trustgraph/api/types.py` (ערוך)

**סוגים חדשים**:

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

#### 6. ממשק API למדדים

מודול: `trustgraph-base/trustgraph/api/metrics.py` (חדש)

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

### גישת יישום

#### שלב 1: שיפורי API מרכזיים (שבוע 1)

1. הוספת שיטות `socket()`, `bulk()` ו-`metrics()` למחלקה `Api`
2. יישום אתחול עצלני עבור לקוחות WebSocket ו-bulk
3. הוספת תמיכה במנהל הקשר (`__enter__`, `__exit__`)
4. הוספת שיטה `close()` לניקוי
5. הוספת בדיקות יחידה לשיפורי מחלקת API
6. אימות תאימות לאחור

**תאימות לאחור**: אין שינויים משמעותיים. רק שיטות חדשות.

#### שלב 2: לקוח WebSocket (שבועות 2-3)

1. יישום מחלקה `SocketClient` עם ניהול חיבור
2. יישום `SocketFlowInstance` עם אותם חתימות שיטה כמו `FlowInstance`
3. הוספת תמיכה בריבוי בקשות (עד 15 מקבילים)
4. הוספת ניתוח תגובה בסטרימינג עבור סוגי חלקים שונים
5. הוספת לוגיקת חיבור מחדש אוטומטית
6. הוספת בדיקות יחידה ושילוב
7. תיעוד דפוסי שימוש ב-WebSocket

**תאימות לאחור**: ממשק חדש בלבד. ללא השפעה על קוד קיים.

#### שלב 3: תמיכה בסטרימינג (שבועות 3-4)

1. הוספת מחלקות סוגי חלקים בסטרימינג (`AgentThought`, `AgentObservation`, `AgentAnswer`, `RAGChunk`)
2. יישום ניתוח תגובה בסטרימינג ב-`SocketClient`
3. הוספת פרמטר סטרימינג לכל שיטות LLM ב-`SocketFlowInstance`
4. טיפול במקרים שגויים במהלך סטרימינג
5. הוספת בדיקות יחידה ושילוב עבור סטרימינג
6. הוספת דוגמאות סטרימינג לתיעוד

**תאימות לאחור**: ממשק חדש בלבד. API REST קיים ללא שינוי.

#### שלב 4: פעולות Bulk (שבועות 4-5)

1. יישום מחלקה `BulkClient`
2. הוספת שיטות ייבוא/ייצוא bulk עבור משולשות, הטבעות, הקשרים, אובייקטים
3. יישום עיבוד מבוסס איטרטור עבור זיכרון קבוע
4. הוספת מעקב התקדמות (callback אופציונלי)
5. הוספת טיפול בשגיאות עם דיווח על הצלחה חלקית
6. הוספת בדיקות יחידה ושילוב
7. הוספת דוגמאות לפעולות bulk

**תאימות לאחור**: ממשק חדש בלבד. ללא השפעה על קוד קיים.

#### שלב 5: התאמה וליטוש (שבוע 5)

1. הוספת `graph_embeddings_query()` ל-REST `FlowInstance`
2. יישום מחלקה `Metrics`
3. הוספת בדיקות שילוב מקיפות
4. ביצועי benchmark
5. עדכון כל התיעוד
6. יצירת מדריך מעבר

**תאימות לאחור**: שיטות חדשות בלבד. ללא השפעה על קוד קיים.

### מודלים של נתונים

#### בחירת ממשק

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

#### סוגי תגובות סטרימינג

**סטרימינג של סוכן:**

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

**סטרימינג RAG**:

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

**פעולות מרובות (סינכרוניות):**

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

**פעולות מרובות (אסינכרוניות):**

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

**דוגמה ל-REST אסינכרוני:**

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

**דוגמה לסטרימינג WebSocket אסינכרוני:**

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

### ממשקי API

#### ממשקי API חדשים

1. **מחלקה ראשית של ממשק API**:
   **סינכרוני**:
     `Api.socket()` - קבלת לקוח WebSocket סינכרוני
     `Api.bulk()` - קבלת לקוח פעולות אצווה סינכרוני
     `Api.metrics()` - קבלת לקוח מדדים סינכרוני
     `Api.close()` - סגירת כל החיבורים הסינכרוניים
     תמיכה במנהל הקשר (context manager) (`__enter__`, `__exit__`)
   **אסינכרוני**:
     `Api.async_flow()` - קבלת לקוח REST flow אסינכרוני
     `Api.async_socket()` - קבלת לקוח WebSocket אסינכרוני
     `Api.async_bulk()` - קבלת לקוח פעולות אצווה אסינכרוני
     `Api.async_metrics()` - קבלת לקוח מדדים אסינכרוני
     `Api.aclose()` - סגירת כל החיבורים האסינכרוניים
     תמיכה במנהל הקשר אסינכרוני (`__aenter__`, `__aexit__`)

2. **לקוח WebSocket סינכרוני**:
   `SocketClient.flow(flow_id)` - קבלת מופע WebSocket
   `SocketFlowInstance.agent(..., streaming: bool = False)` - סוכן עם סטרימינג אופציונלי
   `SocketFlowInstance.text_completion(..., streaming: bool = False)` - השלמת טקסט עם סטרימינג אופציונלי
   `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - Graph RAG עם סטרימינג אופציונלי
   `SocketFlowInstance.document_rag(..., streaming: bool = False)` - Document RAG עם סטרימינג אופציונלי
   `SocketFlowInstance.prompt(..., streaming: bool = False)` - הנחיה (prompt) עם סטרימינג אופציונלי
   `SocketFlowInstance.graph_embeddings_query()` - שאילתת הטמעות גרף
   כל שיטות FlowInstance אחרות עם חתימות זהות

3. **לקוח WebSocket אסינכרוני**:
   `AsyncSocketClient.flow(flow_id)` - קבלת מופע WebSocket אסינכרוני
   `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - סוכן אסינכרוני עם סטרימינג אופציונלי
   `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - השלמת טקסט אסינכרונית עם סטרימינג אופציונלי
   `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - Graph RAG אסינכרוני עם סטרימינג אופציונלי
   `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - Document RAG אסינכרוני עם סטרימינג אופציונלי
   `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - הנחיה (prompt) אסינכרונית עם סטרימינג אופציונלי
   `AsyncSocketFlowInstance.graph_embeddings_query()` - שאילתת הטמעות גרף אסינכרונית
   כל שיטות FlowInstance אחרות כגרסאות אסינכרוניות

4. **לקוח פעולות אצווה סינכרוני**:
   `BulkClient.import_triples(flow, triples)` - ייבוא אצווה של משולשות
   `BulkClient.export_triples(flow)` - ייצוא אצווה של משולשות
   `BulkClient.import_graph_embeddings(flow, embeddings)` - ייבוא אצווה של הטמעות גרף
   `BulkClient.export_graph_embeddings(flow)` - ייצוא אצווה של הטמעות גרף
   `BulkClient.import_document_embeddings(flow, embeddings)` - ייבוא אצווה של הטמעות מסמכים
   `BulkClient.export_document_embeddings(flow)` - ייצוא אצווה של הטמעות מסמכים
   `BulkClient.import_entity_contexts(flow, contexts)` - ייבוא אצווה של הקשרים של ישויות
   `BulkClient.export_entity_contexts(flow)` - ייצוא אצווה של הקשרים של ישויות
   `BulkClient.import_objects(flow, objects)` - ייבוא אצווה של אובייקטים

5. **לקוח פעולות אצווה אסינכרוני**:
   `AsyncBulkClient.import_triples(flow, triples)` - ייבוא אצווה אסינכרוני של משולשות
   `AsyncBulkClient.export_triples(flow)` - ייצוא אצווה אסינכרוני של משולשות
   `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - ייבוא אצווה אסינכרוני של הטמעות גרף
   `AsyncBulkClient.export_graph_embeddings(flow)` - ייצוא אצווה אסינכרוני של הטמעות גרף
   `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - ייבוא אצווה אסינכרוני של הטמעות מסמכים
   `AsyncBulkClient.export_document_embeddings(flow)` - ייצוא אצווה אסינכרוני של הטמעות מסמכים
   `AsyncBulkClient.import_entity_contexts(flow, contexts)` - ייבוא אצווה אסינכרוני של הקשרים של ישויות
   `AsyncBulkClient.export_entity_contexts(flow)` - ייצוא אצווה אסינכרוני של הקשרים של ישויות
   `AsyncBulkClient.import_objects(flow, objects)` - ייבוא אצווה אסינכרוני של אובייקטים

6. **לקוח REST Flow אסינכרוני**:
   `AsyncFlow.list()` - רשימת כל ה-flows (אסינכרוני)
   `AsyncFlow.get(id)` - קבלת הגדרת flow (אסינכרוני)
   `AsyncFlow.start(...)` - התחלת flow (אסינכרוני)
   `AsyncFlow.stop(id)` - עצירת flow (אסינכרוני)
   `AsyncFlow.id(flow_id)` - קבלת מופע flow (אסינכרוני)
   `AsyncFlowInstance.agent(...)` - הרצת סוכן (אסינכרוני)
   `AsyncFlowInstance.text_completion(...)` - השלמת טקסט (אסינכרונית)
   `AsyncFlowInstance.graph_rag(...)` - Graph RAG (אסינכרוני)
   כל שיטות FlowInstance אחרות כגרסאות אסינכרוניות

7. **לקוחות מדדים**:
   `Metrics.get()` - מדדי Prometheus סינכרוניים
   `AsyncMetrics.get()` - מדדי Prometheus אסינכרוניים

8. **שיפור ממשק API של REST Flow**:
   `FlowInstance.graph_embeddings_query()` - שאילתת הטמעות גרף (תאימות תכונות סינכרונית)
   `AsyncFlowInstance.graph_embeddings_query()` - שאילתת הטמעות גרף (תאימות תכונות אסינכרונית)

#### ממשקי API שעברו שינוי

1. **מבנה (Constructor)** (שיפור קל):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   הוסף פרמטר `token` (אופציונלי, לצורך אימות)
   אם `None` (ברירת מחדל): לא נעשה שימוש באימות
   אם צוין: משמש כטוקן bearer עבור REST (`Authorization: Bearer <token>`), כפרמטר שאילתה עבור WebSocket (`?token=<token>`)
   לא בוצעו שינויים אחרים - תואם לאחור לחלוטין

2. **ללא שינויים שמשנים את הפעולה**:
   כל שיטות ה-API של REST הקיימות לא שונו
   כל החתימות הקיימות נשמרו
   כל סוגי ההחזרה הקיימים נשמרו

### פרטי יישום

#### טיפול בשגיאות

**שגיאות חיבור WebSocket**:
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

**מעבר חלק:**
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

**שגיאות סטרימינג חלקיות**:
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

#### ניהול משאבים

**תמיכה במנהל הקשר (Context Manager):**
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

#### תִּקְשׁוּר וּמְקַרְבֵּי מִקְבֵּל

**בְּטִיחוּת מִתְקַרְבֵּי מִקְבֵּל**:
כל מופע של `Api` שומר על חיבור משלו.
תעבורת WebSocket משתמשת במנעולים עבור ריבוב בקשות בטוח לחוטים.
מספר חוטים יכולים לשתף מופע של `Api` בצורה בטוחה.
איטרטורים של סטרימינג אינם בטוחים לחוטים (יש לצרוך מהחוט היחיד).

**תמיכה אסינכרונית** (שיקול עתידי):
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

## שיקולי אבטחה

### אימות

**פרמטר טוקן**:
```python
# No authentication (default)
api = Api(url="http://localhost:8088/")

# With authentication
api = Api(url="http://localhost:8088/", token="mytoken")
```

**שינוע REST**:
טוקן נושא דרך כותרת `Authorization`
מיושם אוטומטית על כל בקשות REST
פורמט: `Authorization: Bearer <token>`

**שינוע WebSocket**:
טוקן דרך פרמטר שאילתה המצורף לכתובת ה-WebSocket
מיושם אוטומטית במהלך יצירת החיבור
פורמט: `ws://localhost:8088/api/v1/socket?token=<token>`

**יישום**:
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

**דוגמה:**
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")
flow = api.flow().id("default")
# All REST calls include: Authorization: Bearer mytoken

# WebSocket with auth
socket = api.socket()
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### תקשורת מאובטחת

תמיכה הן בפרוטוקול WS (WebSocket) והן בפרוטוקול WSS (WebSocket Secure).
אימות תעודות TLS עבור חיבורי WSS.
אפשרות לביטול אימות תעודות לצורך פיתוח (עם אזהרה).

### אימות קלט

אימות סכימות כתובות URL (http, https, ws, wss).
אימות ערכי פרמטרים של העברת נתונים.
אימות שילובים של פרמטרים של העברה רציפה.
אימות סוגי נתונים לייבוא בכמות גדולה.

## שיקולי ביצועים

### שיפורי השהייה

**פעולות LLM רציפות (Streaming)**:
**זמן עד לקבלת הטוקן הראשון**: ~500ms (לעומת ~30 שניות ללא העברה רציפה).
**שיפור**: ביצועים תפיסיים מהירים פי 60.
**מתאים ל**: סוכן, Graph RAG, Document RAG, השלמת טקסט, הנחיה.

**חיבורים קבועים**:
**תקורה של חיבור**: מבוטלת עבור בקשות עוקבות.
**הדחיסה הראשונית של WebSocket**: עלות חד-פעמית (~100ms).
**מתאים ל**: כל הפעולות בעת שימוש בפרוטוקול WebSocket.

### שיפורי תפוקה

**פעולות בכמות גדולה**:
**ייבוא משולשות**: ~10,000 משולשות/שנייה (לעומת ~100/שנייה עם REST עבור כל פריט).
**ייבוא הטמעות (Embeddings)**: ~5,000 הטמעות/שנייה (לעומת ~50/שנייה עם REST עבור כל פריט).
**שיפור**: תפוקה גבוהה פי 100 עבור פעולות בכמות גדולה.

**ריבוב בקשות (Request Multiplexing)**:
**בקשות מקבילות**: עד 15 בקשות בו-זמנית על גבי חיבור יחיד.
**שימוש חוזר בחיבור**: אין תקורה של חיבור עבור פעולות מקבילות.

### שיקולי זיכרון

**תגובות רציפות (Streaming)**:
שימוש קבוע בזיכרון (עיבוד מקטעים כשהם מגיעים).
אין אחסון זמני של תגובה שלמה.
מתאים לפלטים ארוכים מאוד (>1MB).

**פעולות בכמות גדולה**:
עיבוד מבוסס איטרטור (שימוש קבוע בזיכרון).
אין טעינה של קבוצת נתונים שלמה לתוך הזיכרון.
מתאים לקבוצות נתונים עם מיליוני פריטים.

### מדדי ביצוע (צפויים)

| פעולה | REST (קיים) | WebSocket (העברה רציפה) | שיפור |
|-----------|----------------|----------------------|-------------|
| סוכן (זמן עד לקבלת הטוקן הראשון) | 30 שניות | 0.5 שניות | 60x |
| Graph RAG (זמן עד לקבלת הטוקן הראשון) | 25 שניות | 0.5 שניות | 50x |
| ייבוא 10K משולשות | 100 שניות | 1 שניה | 100x |
| ייבוא 1M משולשות | 10,000 שניות (2.7 שעות) | 100 שניות (1.6 דקות) | 100x |
| 10 בקשות קטנות במקביל | 5 שניות (רציף) | 0.5 שניות (מקביל) | 10x |

## אסטרטגיית בדיקות

### בדיקות יחידה

**שכבת התעבורה** (`test_transport.py`):
בדיקת בקשה/תגובה של פרוטוקול REST
בדיקת חיבור פרוטוקול WebSocket
בדיקת חיבור מחדש של פרוטוקול WebSocket
בדיקת ריבוי בקשות
בדיקת ניתוח תגובה בסטרימינג
שרת WebSocket מדמה לבדיקות דטרמיניסטיות

**שיטות API** (`test_flow.py`, `test_library.py`, וכו'):
בדיקת שיטות חדשות עם שכבת תעבורה מדמה
בדיקת טיפול בפרמטרים בסטרימינג
בדיקת איטרטורים לפעולות אצווה
בדיקת טיפול בשגיאות

**טיפוסים** (`test_types.py`):
בדיקת טיפוסי סטרימינג חדשים
בדיקת סריאליזציה/דה-סריאליזציה של טיפוסים

### בדיקות אינטגרציה

**REST מקצה לקצה** (`test_integration_rest.py`):
בדיקת כל הפעולות מול שער אמיתי (מצב REST)
אימות תאימות לאחור
בדיקת תנאי שגיאה

**WebSocket מקצה לקצה** (`test_integration_websocket.py`):
בדיקת כל הפעולות מול שער אמיתי (מצב WebSocket)
בדיקת פעולות סטרימינג
בדיקת פעולות אצווה
בדיקת בקשות מקבילות
בדיקת התאוששות חיבור

**שירותי סטרימינג** (`test_streaming_integration.py`):
בדיקת סטרימינג של סוכן (מחשבות, תצפיות, תשובות)
בדיקת סטרימינג של RAG (חלקים מצטברים)
בדיקת סטרימינג של השלמת טקסט (טוקן אחר טוקן)
בדיקת סטרימינג של הנחיה
בדיקת טיפול בשגיאות במהלך סטרימינג

**פעולות אצווה** (`test_bulk_integration.py`):
בדיקת ייבוא/ייצוא אצווה של טריפלטים (1K, 10K, 100K פריטים)
בדיקת ייבוא/ייצוא אצווה של הטמעות
בדיקת שימוש בזיכרון במהלך פעולות אצווה
בדיקת מעקב אחר התקדמות

### בדיקות ביצועים

**מדדי השהייה** (`test_performance_latency.py`):
מדידת זמן עד לטוקן הראשון (סטרימינג לעומת לא סטרימינג)
מדידת תקורה של חיבור (REST לעומת WebSocket)
השוואה למדדים צפויים

**מדדי תפוקה** (`test_performance_throughput.py`):
מדידת תפוקת ייבוא אצווה
מדידת יעילות ריבוי בקשות
השוואה למדדים צפויים

### בדיקות תאימות

**תאימות לאחור** (`test_backward_compatibility.py`):
הרצת סט בדיקות קיים מול API שעבר שינוי מבני
אימות היעדר שינויים שוברים
בדיקת נתיב מעבר עבור תבניות נפוצות

## תוכנית מעבר

### שלב 1: מעבר שקוף (ברירת מחדל)

**לא נדרשים שינויי קוד**. קוד קיים ממשיך לעבוד:

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### שלב 2: הפעלת סטרימינג (פשוט)

**השתמשו בממשק `api.socket()`** כדי להפעיל סטרימינג:

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

**נקודות עיקריות:**
אותה כתובת URL עבור REST ו-WebSocket
אותם חתימות מתודות (מעבר קל)
פשוט הוסיפו את `.socket()` ו-`streaming=True`

### שלב 3: פעולות בכמות גדולה (יכולת חדשה)

**השתמשו בממשק `api.bulk()`** עבור מערכי נתונים גדולים:

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

### עדכוני תיעוד

1. **README.md**: הוספת דוגמאות סטרימינג ו-WebSocket
2. **הפניה ל-API**: תיעוד של כל השיטות והפרמטרים החדשים
3. **מדריך מעבר**: מדריך שלב אחר שלב להפעלת סטרימינג
4. **דוגמאות**: הוספת סקריפטים לדוגמה לתבניות נפוצות
5. **מדריך ביצועים**: תיעוד של שיפורי ביצועים צפויים

### מדיניות הפסקה

**ללא הפסקות**. כל ה-APIs הקיימים נתמכים. זוהי שיפור משמעותי בלבד.

## ציר זמן

### שבוע 1: יסודות
שכבת הפשטה של העברת נתונים
שיפור קוד REST קיים
בדיקות יחידה לשכבת העברת הנתונים
אימות תאימות לאחור

### שבוע 2: העברת WebSocket
יישום העברת WebSocket
ניהול חיבורים וחיבור מחדש
ריבוב בקשות
בדיקות יחידה ושילוב

### שבוע 3: תמיכה בסטרימינג
הוספת פרמטר סטרימינג לשיטות LLM
יישום ניתוח תגובות סטרימינג
הוספת סוגי חלקי סטרימינג
בדיקות שילוב סטרימינג

### שבוע 4: פעולות מרובות
הוספת שיטות ייבוא/ייצוא מרובות
יישום פעולות מבוססות איטרטור
בדיקות ביצועים
בדיקות שילוב לפעולות מרובות

### שבוע 5: התאמה ותיעוד
הוספת שאילתת הטמעות גרף
הוספת API למדדים
תיעוד מקיף
מדריך מעבר
גרסה מועמדת

### שבוע 6: שחרור
בדיקות שילוב סופיות
מדידת ביצועים
תיעוד לשחרור
הודעה לקהילה

**משך כולל**: 6 שבועות

## שאלות פתוחות

### שאלות עיצוב API

1. **תמיכה אסינכרונית**: ✅ **נפתר** - תמיכה אסינכרונית מלאה כלולה בשחרור הראשוני
   לכל הממשקים יש גרסאות אסינכרוניות: `async_flow()`, `async_socket()`, `async_bulk()`, `async_metrics()`
   מספק סימטריה מלאה בין ממשקי סנכרון ואסינכרון
   חיוני למסגרות אסינכרוניות מודרניות (FastAPI, aiohttp)

2. **מעקב אחר התקדמות**: האם פעולות מרובות צריכות לתמוך בפונקציות החזרה של התקדמות?
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   **המלצה**: להוסיף בשלב 2. לא קריטי לשחרור הראשוני.

3. **זמן המתנה (Timeout) לסטרימינג**: איך עלינו לטפל בזמני המתנה עבור פעולות סטרימינג?
   **המלצה**: להשתמש באותו זמן המתנה כמו בפעולות שאינן סטרימינג, אך לאפס אותו בכל פעם שמתקבל חלק.

4. **ביצוע אחסון של חלקים (Chunk Buffering)**: האם עלינו לאחסן חלקים או להחזיר מידע מיד?
   **המלצה**: להחזיר מיד כדי להשיג השהייה נמוכה ביותר.

5. **שירותים גלובליים דרך WebSocket**: האם `api.socket()` צריך לתמוך בשירותים גלובליים (ספרייה, ידע, אוסף, תצורה) או רק בשירותים המוגבלים ל-flow?
   **המלצה**: להתחיל רק עם שירותים המוגבלים ל-flow (שם הסטרימינג חשוב). להוסיף שירותים גלובליים במידת הצורך בשלב 2.

### שאלות יישום

1. **ספריית WebSocket**: האם עלינו להשתמש ב-`websockets`, `websocket-client`, או `aiohttp`?
   **המלצה**: `websockets` (אסינכרוני, בשל, מתוחזק היטב). לעטוף בממשק סינכרוני באמצעות `asyncio.run()`.

2. **ניהול חיבורים (Connection Pooling)**: האם עלינו לתמוך במספר מופעים מקבילים של `Api` המשתפים בריכת חיבורים?
   **המלצה**: לדחות לשלב 2. לכל מופע של `Api` יהיו חיבורים משלו בתחילה.

3. **שימוש חוזר בחיבורים**: האם `SocketClient` ו-`BulkClient` צריכים לשתף את אותו חיבור WebSocket, או להשתמש בחיבורים נפרדים?
   **המלצה**: חיבורים נפרדים. יישום פשוט יותר, הפרדה ברורה יותר של נושאים.

4. **חיבור עצלני לעומת חיבור מוקדם**: האם החיבור WebSocket צריך להיות מוקם ב-`api.socket()` או בבקשה הראשונה?
   **המלצה**: עצלני (בבקשה הראשונה). נמנע מעלות נוספת של חיבור אם המשתמש משתמש רק בשיטות REST.

### שאלות בדיקה

1. **שער מדמה (Mock Gateway)**: האם עלינו ליצור שער מדמה קל משקל לבדיקות, או לבדוק מול שער אמיתי?
   **המלצה**: שניהם. להשתמש במדמים לבדיקות יחידה, ושער אמיתי לבדיקות אינטגרציה.

2. **בדיקות רגרסיה לביצועים**: האם עלינו להוסיף בדיקות רגרסיה אוטומטיות לביצועים ל-CI?
   **המלצה**: כן, אך עם ספים נדיבים כדי להתחשב בשונות בסביבת ה-CI.

## הפניות

### מפרטי טכנולוגיה קשורים
`docs/tech-specs/streaming-llm-responses.md` - יישום סטרימינג בשער
`docs/tech-specs/rag-streaming-support.md` - תמיכה בסטרימינג של RAG

### קבצי יישום
`trustgraph-base/trustgraph/api/` - קוד מקור של API בפייתון
`trustgraph-flow/trustgraph/gateway/` - קוד מקור של השער
`trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - יישום התייחסות של מולטיפלקסר WebSocket

### תיעוד
`docs/apiSpecification.md` - הפניה מלאה ל-API
`docs/api-status-summary.md` - סיכום סטטוס API
`README.websocket` - תיעוד פרוטוקול WebSocket
`STREAMING-IMPLEMENTATION-NOTES.txt` - הערות על יישום סטרימינג

### ספריות חיצוניות
`websockets` - ספריית WebSocket בפייתון (https://websockets.readthedocs.io/)
`requests` - ספריית HTTP בפייתון (קיימת)
