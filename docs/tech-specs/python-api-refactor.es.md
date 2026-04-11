# Especificación Técnica de Refactorización de la API de Python

## Resumen

Esta especificación describe una refactorización integral de la biblioteca de cliente de la API de Python de TrustGraph para lograr la paridad de funciones con la API Gateway y agregar soporte para patrones de comunicación en tiempo real modernos.

La refactorización aborda cuatro casos de uso principales:

1. **Interacciones de LLM en Streaming**: Habilitar el streaming en tiempo real de las respuestas de LLM (agente, RAG de grafos, RAG de documentos, finalización de texto, prompts) con una latencia significativamente menor (~60 veces menor, 500 ms frente a 30 s para el primer token).
2. **Operaciones de Datos Masivos**: Soporte para la importación/exportación eficiente de triples, incrustaciones de grafos e incrustaciones de documentos para la gestión de grafos de conocimiento a gran escala.
3. **Paridad de Funciones**: Asegurar que cada punto final de la API Gateway tenga un método de API de Python correspondiente, incluidas las consultas de incrustaciones de grafos.
4. **Conexiones Persistentes**: Habilitar la comunicación basada en WebSocket para solicitudes multiplexadas y una menor sobrecarga de conexión.

## Objetivos

**Paridad de Funciones**: Cada servicio de la API Gateway tiene un método de API de Python correspondiente.
**Soporte de Streaming**: Todos los servicios capaces de streaming (agente, RAG, finalización de texto, prompt) admiten el streaming en la API de Python.
**Transporte WebSocket**: Agregar una capa de transporte WebSocket opcional para conexiones persistentes y multiplexación.
**Operaciones Masivas**: Agregar importación/exportación masiva eficiente para triples, incrustaciones de grafos e incrustaciones de documentos.
**Soporte Completo Async**: Implementación completa de async/await para todas las interfaces (REST, WebSocket, operaciones masivas, métricas).
**Compatibilidad con Versiones Anteriores**: El código existente continúa funcionando sin modificaciones.
**Seguridad de Tipos**: Mantener interfaces con seguridad de tipos utilizando dataclasses y sugerencias de tipo.
**Mejora Progresiva**: El streaming y el async son opcionales a través de la selección explícita de la interfaz.
**Rendimiento**: Lograr una mejora de latencia de 60 veces para las operaciones de streaming.
**Python Moderno**: Soporte para paradigmas tanto síncronos como asíncronos para una máxima flexibilidad.

## Antecedentes

### Estado Actual

La API de Python (`trustgraph-base/trustgraph/api/`) es una biblioteca de cliente REST con los siguientes módulos:

`flow.py`: Gestión de flujos y servicios con ámbito de flujo (50 métodos).
`library.py`: Operaciones de la biblioteca de documentos (9 métodos).
`knowledge.py`: Gestión central de grafos (4 métodos).
`collection.py`: Metadatos de colecciones (3 métodos).
`config.py`: Gestión de configuración (6 métodos).
`types.py`: Definiciones de tipos de datos (5 dataclasses).

**Operaciones Totales**: 50/59 (cobertura del 85%).

### Limitaciones Actuales

**Operaciones Faltantes**:
Consulta de incrustaciones de grafos (búsqueda semántica sobre entidades de grafos).
Importación/exportación masiva para triples, incrustaciones de grafos, incrustaciones de documentos, contextos de entidades, objetos.
Punto final de métricas.

**Capacidades Faltantes**:
Soporte de streaming para servicios de LLM.
Transporte WebSocket.
Solicitudes concurrentes multiplexadas.
Conexiones persistentes.

**Problemas de Rendimiento**:
Alta latencia para las interacciones de LLM (~30 s para el primer token).
Transferencia de datos masiva ineficiente (solicitud REST por elemento).
Sobrecarga de conexión para múltiples operaciones secuenciales.

**Problemas de Experiencia de Usuario**:
Sin retroalimentación en tiempo real durante la generación de LLM.
No se pueden cancelar las operaciones de LLM de larga duración.
Mala escalabilidad para las operaciones masivas.

### Impacto

La mejora de streaming de noviembre de 2024 en la API Gateway proporcionó una mejora de latencia de 60 veces (500 ms frente a 30 s para el primer token) para las interacciones de LLM, pero los usuarios de la API de Python no pueden aprovechar esta capacidad. Esto crea una brecha significativa de experiencia entre los usuarios de Python y los que no lo utilizan.

## Diseño Técnico

### Arquitectura

La API de Python refactorizada utiliza un **enfoque de interfaz modular** con objetos separados para diferentes patrones de comunicación. Todas las interfaces están disponibles tanto en variantes **síncronas como asíncronas**:

1. **Interfaz REST** (existente, mejorada).
   **Sync**: `api.flow()`, `api.library()`, `api.knowledge()`, `api.collection()`, `api.config()`.
   **Async**: `api.async_flow()`.
   Solicitud/respuesta síncrona/asíncrona.
   Modelo de conexión simple.
   Predeterminado para la compatibilidad con versiones anteriores.

2. **Interfaz WebSocket** (nueva).
   **Sync**: `api.socket()`.
   **Async**: `api.async_socket()`.
   Conexión persistente.
   Solicitudes multiplexadas.
   Soporte de streaming.
   Mismas firmas de método que REST donde la funcionalidad se superpone.

3. **Interfaz de Operaciones Masivas** (nueva).
   **Sync**: `api.bulk()`.
   **Async**: `api.async_bulk()`.
   Basado en WebSocket para la eficiencia.
   Importación/exportación basada en iterador/AsyncIterator.
   Maneja conjuntos de datos grandes.

4. **Interfaz de Métricas** (nueva).
   **Sync**: `api.metrics()`.
   **Async**: `api.async_metrics()`.
   Acceso a métricas de Prometheus.

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

**Principios clave de diseño:**
**Misma URL para todas las interfaces:** `Api(url="http://localhost:8088/")` funciona para todas.
**Simetría sincrónica/asincrónica:** Cada interfaz tiene variantes tanto sincrónicas como asincrónicas con firmas de método idénticas.
**Firmas idénticas:** Donde la funcionalidad se superpone, las firmas de los métodos son idénticas entre REST y WebSocket, sincrónicas y asincrónicas.
**Mejora progresiva:** Elija la interfaz según las necesidades (REST para tareas simples, WebSocket para transmisión, Bulk para conjuntos de datos grandes, asíncrono para marcos modernos).
**Intención explícita:** `api.socket()` indica WebSocket, `api.async_socket()` indica WebSocket asíncrono.
**Compatible con versiones anteriores:** El código existente no se modifica.

### Componentes

#### 1. Clase API principal (modificada)

Módulo: `trustgraph-base/trustgraph/api/api.py`

**Clase API mejorada:**

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

#### 2. Cliente WebSocket Síncrono

Módulo: `trustgraph-base/trustgraph/api/socket_client.py` (nuevo)

**Clase SocketClient**:

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

**Características principales:**
Conexión perezosa (solo se conecta cuando se envía la primera solicitud)
Multiplexación de solicitudes (hasta 15 concurrentes)
Reconexión automática en caso de desconexión
Análisis de respuesta en streaming
Operación segura para subprocesos
Envoltorio sincrónico alrededor de la biblioteca de websockets asíncrona

#### 3. Cliente WebSocket asíncrono

Módulo: `trustgraph-base/trustgraph/api/async_socket_client.py` (nuevo)

**Clase AsyncSocketClient:**

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

**Características principales**:
Soporte nativo para async/await
Eficiente para aplicaciones asíncronas (FastAPI, aiohttp)
Sin bloqueo de hilos
Misma interfaz que la versión síncrona
AsyncIterator para streaming

#### 4. Cliente de Operaciones Masivas Síncronas

Módulo: `trustgraph-base/trustgraph/api/bulk_client.py` (nuevo)

**Clase BulkClient**:

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

**Características principales:**
Basado en iteradores para un uso constante de memoria.
Conexiones WebSocket dedicadas por operación.
Seguimiento del progreso (callback opcional).
Manejo de errores con informes de éxito parcial.

#### 5. Cliente de operaciones masivas asíncronas

Módulo: `trustgraph-base/trustgraph/api/async_bulk_client.py` (nuevo)

**Clase AsyncBulkClient:**

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

**Características principales:**
Basado en AsyncIterator para un uso constante de memoria.
Eficiente para aplicaciones asíncronas.
Soporte nativo para async/await.
Misma interfaz que la versión síncrona.

#### 6. API de flujo REST (Síncrono - Sin cambios)

Módulo: `trustgraph-base/trustgraph/api/flow.py`

La API de flujo REST permanece **completamente sin cambios** para la compatibilidad con versiones anteriores. Todos los métodos existentes siguen funcionando:

`Flow.list()`, `Flow.start()`, `Flow.stop()`, etc.
`FlowInstance.agent()`, `FlowInstance.text_completion()`, `FlowInstance.graph_rag()`, etc.
Todas las firmas y tipos de retorno existentes se conservan.

**Nuevo:** Agregar `graph_embeddings_query()` a REST FlowInstance para la paridad de funciones:

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

#### 7. API de flujo REST asíncrono

Módulo: `trustgraph-base/trustgraph/api/async_flow.py` (nuevo)

**Clases AsyncFlow y AsyncFlowInstance:**

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

**Características principales:**
HTTP asíncrono nativo utilizando `aiohttp` o `httpx`
Mismas firmas de método que la API REST sincrónica
Sin transmisión (utilice `async_socket()` para la transmisión)
Eficiente para aplicaciones asíncronas

#### 8. API de métricas

Módulo: `trustgraph-base/trustgraph/api/metrics.py` (nuevo)

**Métricas sincrónicas:**

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

**Métricas Asíncronas**:

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

#### 9. Tipos Mejorados

Módulo: `trustgraph-base/trustgraph/api/types.py` (modificado)

**Nuevos Tipos**:

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

#### 6. API de métricas

Módulo: `trustgraph-base/trustgraph/api/metrics.py` (nuevo)

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

### Enfoque de Implementación

#### Fase 1: Mejora del API Central (Semana 1)

1. Agregar métodos `socket()`, `bulk()` y `metrics()` a la clase `Api`
2. Implementar inicialización perezosa para WebSocket y clientes masivos
3. Agregar soporte para administrador de contexto (`__enter__`, `__exit__`)
4. Agregar método `close()` para limpieza
5. Agregar pruebas unitarias para las mejoras del API
6. Verificar compatibilidad con versiones anteriores

**Compatibilidad con versiones anteriores**: No hay cambios que rompan la compatibilidad. Solo se agregan nuevos métodos.

#### Fase 2: Cliente WebSocket (Semanas 2-3)

1. Implementar clase `SocketClient` con gestión de conexión
2. Implementar `SocketFlowInstance` con las mismas firmas de método que `FlowInstance`
3. Agregar soporte para multiplexación de solicitudes (hasta 15 concurrentes)
4. Agregar análisis de respuesta en streaming para diferentes tipos de fragmentos
5. Agregar lógica de reconexión automática
6. Agregar pruebas unitarias e integrales
7. Documentar patrones de uso de WebSocket

**Compatibilidad con versiones anteriores**: Nueva interfaz solamente. No tiene impacto en el código existente.

#### Fase 3: Soporte de Streaming (Semanas 3-4)

1. Agregar clases de tipo de fragmento de streaming (`AgentThought`, `AgentObservation`, `AgentAnswer`, `RAGChunk`)
2. Implementar análisis de respuesta en streaming en `SocketClient`
3. Agregar parámetro de streaming a todos los métodos LLM en `SocketFlowInstance`
4. Manejar casos de error durante el streaming
5. Agregar pruebas unitarias e integrales para el streaming
6. Agregar ejemplos de streaming a la documentación

**Compatibilidad con versiones anteriores**: Nueva interfaz solamente. El API REST existente no se modifica.

#### Fase 4: Operaciones Masivas (Semanas 4-5)

1. Implementar clase `BulkClient`
2. Agregar métodos de importación/exportación masiva para triples, incrustaciones, contextos, objetos
3. Implementar procesamiento basado en iterador para un uso constante de memoria
4. Agregar seguimiento de progreso (callback opcional)
5. Agregar manejo de errores con informes de éxito parcial
6. Agregar pruebas unitarias e integrales
7. Agregar ejemplos de operaciones masivas

**Compatibilidad con versiones anteriores**: Nueva interfaz solamente. No tiene impacto en el código existente.

#### Fase 5: Paridad de Funciones y Pulido (Semana 5)

1. Agregar `graph_embeddings_query()` a REST `FlowInstance`
2. Implementar clase `Metrics`
3. Agregar pruebas de integración exhaustivas
4. Pruebas de rendimiento
5. Actualizar toda la documentación
6. Crear una guía de migración

**Compatibilidad con versiones anteriores**: Nuevos métodos solamente. No tiene impacto en el código existente.

### Modelos de Datos

#### Selección de Interfaz

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

#### Tipos de respuesta de transmisión

**Transmisión del agente**:

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

**Transmisión RAG**:

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

**Operaciones masivas (síncronas):**

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

**Operaciones masivas (asíncronas):**

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

**Ejemplo de REST asíncrono**:

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

**Ejemplo de transmisión WebSocket asíncrona:**

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

1. **Clase API Core**:
   **Síncrono**:
     `Api.socket()` - Obtener cliente WebSocket síncrono
     `Api.bulk()` - Obtener cliente de operaciones masivas síncrono
     `Api.metrics()` - Obtener cliente de métricas síncrono
     `Api.close()` - Cerrar todas las conexiones síncronas
     Soporte de administrador de contexto (`__enter__`, `__exit__`)
   **Asíncrono**:
     `Api.async_flow()` - Obtener cliente de flujo REST asíncrono
     `Api.async_socket()` - Obtener cliente WebSocket asíncrono
     `Api.async_bulk()` - Obtener cliente de operaciones masivas asíncrono
     `Api.async_metrics()` - Obtener cliente de métricas asíncrono
     `Api.aclose()` - Cerrar todas las conexiones asíncronas
     Soporte de administrador de contexto asíncrono (`__aenter__`, `__aexit__`)

2. **Cliente WebSocket Síncrono**:
   `SocketClient.flow(flow_id)` - Obtener instancia de flujo WebSocket
   `SocketFlowInstance.agent(..., streaming: bool = False)` - Agente con transmisión opcional
   `SocketFlowInstance.text_completion(..., streaming: bool = False)` - Completar texto con transmisión opcional
   `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - RAG de gráfico con transmisión opcional
   `SocketFlowInstance.document_rag(..., streaming: bool = False)` - RAG de documento con transmisión opcional
   `SocketFlowInstance.prompt(..., streaming: bool = False)` - Prompt con transmisión opcional
   `SocketFlowInstance.graph_embeddings_query()` - Consulta de incrustaciones de gráfico
   Todos los demás métodos de FlowInstance con firmas idénticas

3. **Cliente WebSocket Asíncrono**:
   `AsyncSocketClient.flow(flow_id)` - Obtener instancia de flujo WebSocket asíncrono
   `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - Agente asíncrono con transmisión opcional
   `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - Completar texto asíncrono con transmisión opcional
   `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - RAG de gráfico asíncrono con transmisión opcional
   `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - RAG de documento asíncrono con transmisión opcional
   `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - Prompt asíncrono con transmisión opcional
   `AsyncSocketFlowInstance.graph_embeddings_query()` - Consulta de incrustaciones de gráfico asíncrona
   Todos los demás métodos de FlowInstance como versiones asíncronas

4. **Cliente de Operaciones Masivas Síncrono**:
   `BulkClient.import_triples(flow, triples)` - Importación masiva de triples
   `BulkClient.export_triples(flow)` - Exportación masiva de triples
   `BulkClient.import_graph_embeddings(flow, embeddings)` - Importación masiva de incrustaciones de gráfico
   `BulkClient.export_graph_embeddings(flow)` - Exportación masiva de incrustaciones de gráfico
   `BulkClient.import_document_embeddings(flow, embeddings)` - Importación masiva de incrustaciones de documento
   `BulkClient.export_document_embeddings(flow)` - Exportación masiva de incrustaciones de documento
   `BulkClient.import_entity_contexts(flow, contexts)` - Importación masiva de contextos de entidades
   `BulkClient.export_entity_contexts(flow)` - Exportación masiva de contextos de entidades
   `BulkClient.import_objects(flow, objects)` - Importación masiva de objetos

5. **Cliente de Operaciones Masivas Asíncrono**:
   `AsyncBulkClient.import_triples(flow, triples)` - Importación asíncrona masiva de triples
   `AsyncBulkClient.export_triples(flow)` - Exportación asíncrona masiva de triples
   `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - Importación asíncrona masiva de incrustaciones de gráfico
   `AsyncBulkClient.export_graph_embeddings(flow)` - Exportación asíncrona masiva de incrustaciones de gráfico
   `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - Importación asíncrona masiva de incrustaciones de documento
   `AsyncBulkClient.export_document_embeddings(flow)` - Exportación asíncrona masiva de incrustaciones de documento
   `AsyncBulkClient.import_entity_contexts(flow, contexts)` - Importación asíncrona masiva de contextos de entidades
   `AsyncBulkClient.export_entity_contexts(flow)` - Exportación asíncrona masiva de contextos de entidades
   `AsyncBulkClient.import_objects(flow, objects)` - Importación asíncrona masiva de objetos

6. **Cliente de Flujo REST Asíncrono**:
   `AsyncFlow.list()` - Listar todos los flujos de forma asíncrona
   `AsyncFlow.get(id)` - Obtener definición de flujo de forma asíncrona
   `AsyncFlow.start(...)` - Iniciar flujo de forma asíncrona
   `AsyncFlow.stop(id)` - Detener flujo de forma asíncrona
   `AsyncFlow.id(flow_id)` - Obtener instancia de flujo de forma asíncrona
   `AsyncFlowInstance.agent(...)` - Ejecución de agente asíncrona
   `AsyncFlowInstance.text_completion(...)` - Completar texto de forma asíncrona
   `AsyncFlowInstance.graph_rag(...)` - RAG de gráfico asíncrono
   Todos los demás métodos de FlowInstance como versiones asíncronas

7. **Clientes de Métricas**:
   `Metrics.get()` - Métricas de Prometheus síncronas
   `AsyncMetrics.get()` - Métricas de Prometheus asíncronas

8. **Mejora de la API REST de Flujo**:
   `FlowInstance.graph_embeddings_query()` - Consulta de incrustaciones de gráfico (paridad de funciones síncronas)
   `AsyncFlowInstance.graph_embeddings_query()` - Consulta de incrustaciones de gráfico (paridad de funciones asíncronas)

#### APIs Modificadas

1. **Constructor** (pequeña mejora):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   Se agregó el parámetro `token` (opcional, para autenticación).
   Si `None` no se especifica (por defecto): No se utiliza autenticación.
   Si se especifica: Se utiliza como token de tipo "bearer" para REST (`Authorization: Bearer <token>`), parámetro de consulta para WebSocket (`?token=<token>`).
   No se realizaron otros cambios; es totalmente compatible con versiones anteriores.

2. **Sin cambios que rompan la compatibilidad**:
   Todos los métodos de la API REST existentes no se han modificado.
   Todas las firmas existentes se han conservado.
   Todos los tipos de retorno existentes se han conservado.

### Detalles de implementación

#### Manejo de errores

**Errores de conexión WebSocket**:
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

**Respaldo Elegante**:
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

**Errores de transmisión parcial**:
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

#### Gestión de Recursos

**Soporte para Administradores de Contexto**:
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

#### Concurrencia y Subprocesamiento

**Seguridad de Subprocesos**:
Cada instancia de `Api` mantiene su propia conexión.
El transporte WebSocket utiliza bloqueos para el multiplexado de solicitudes, que es seguro para subprocesos.
Múltiples subprocesos pueden compartir una instancia de `Api` de forma segura.
Los iteradores de transmisión no son seguros para subprocesos (se deben consumir desde un solo subproceso).

**Soporte Asíncrono** (consideración futura):
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

## Consideraciones de seguridad

### Autenticación

**Parámetro de token**:
```python
# No authentication (default)
api = Api(url="http://localhost:8088/")

# With authentication
api = Api(url="http://localhost:8088/", token="mytoken")
```

**Transporte REST**:
Token del portador a través del encabezado `Authorization`
Se aplica automáticamente a todas las solicitudes REST
Formato: `Authorization: Bearer <token>`

**Transporte WebSocket**:
Token a través de un parámetro de consulta adjunto a la URL de WebSocket
Se aplica automáticamente durante el establecimiento de la conexión
Formato: `ws://localhost:8088/api/v1/socket?token=<token>`

**Implementación**:
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

**Ejemplo:**
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")
flow = api.flow().id("default")
# All REST calls include: Authorization: Bearer mytoken

# WebSocket with auth
socket = api.socket()
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### Comunicación Segura

Soporta tanto los esquemas WS (WebSocket) como los de WSS (WebSocket Secure).
Validación de certificados TLS para conexiones WSS.
Verificación de certificados opcional para desarrollo (con advertencia).

### Validación de Datos de Entrada

Validar esquemas de URL (http, https, ws, wss).
Validar valores de parámetros de transporte.
Validar combinaciones de parámetros de transmisión.
Validar tipos de datos para la importación masiva.

## Consideraciones de Rendimiento

### Mejoras en la Latencia

**Operaciones de LLM en Transmisión**:
**Tiempo hasta el primer token**: ~500ms (vs ~30s sin transmisión)
**Mejora**: 60 veces más rápido en términos de rendimiento percibido.
**Aplicable a**: Agente, Graph RAG, Document RAG, Completar Texto, Prompt.

**Conexiones Persistentes**:
**Sobrecarga de la conexión**: Eliminada para solicitudes posteriores.
**Handshake de WebSocket**: Costo único (~100ms).
**Aplicable a**: Todas las operaciones al usar el transporte WebSocket.

### Mejoras en el Rendimiento (Throughput)

**Operaciones Masivas**:
**Importación de triples**: ~10,000 triples/segundo (vs ~100/segundo con REST por elemento).
**Importación de embeddings**: ~5,000 embeddings/segundo (vs ~50/segundo con REST por elemento).
**Mejora**: 100 veces más de rendimiento para operaciones masivas.

**Multiplexación de Solicitudes**:
**Solicitudes concurrentes**: Hasta 15 solicitudes simultáneas sobre una sola conexión.
**Reutilización de la conexión**: Sin sobrecarga de conexión para operaciones concurrentes.

### Consideraciones de Memoria

**Respuestas en Transmisión**:
Uso constante de memoria (procesa los fragmentos a medida que llegan).
No se almacena en búfer la respuesta completa.
Adecuado para salidas muy largas (>1MB).

**Operaciones Masivas**:
Procesamiento basado en iteradores (uso constante de memoria).
No se carga todo el conjunto de datos en la memoria.
Adecuado para conjuntos de datos con millones de elementos.

### Pruebas de Rendimiento (Esperadas)

| Operación | REST (existente) | WebSocket (en transmisión) | Mejora |
|-----------|----------------|----------------------|-------------|
| Agente (tiempo hasta el primer token) | 30s | 0.5s | 60x |
| Graph RAG (tiempo hasta el primer token) | 25s | 0.5s | 50x |
| Importar 10K triples | 100s | 1s | 100x |
| Importar 1M triples | 10,000s (2.7h) | 100s (1.6m) | 100x |
| 10 solicitudes pequeñas concurrentes | 5s (secuencial) | 0.5s (paralelo) | 10x |

## Estrategia de Pruebas

### Pruebas Unitarias

**Capa de Transporte** (`test_transport.py`):
Probar la solicitud/respuesta de transporte REST
Probar la conexión de transporte WebSocket
Probar la reconexión de transporte WebSocket
Probar el multiplexado de solicitudes
Probar el análisis de la respuesta de transmisión
Simular un servidor WebSocket para pruebas deterministas

**Métodos de la API** (`test_flow.py`, `test_library.py`, etc.):
Probar nuevos métodos con transporte simulado
Probar el manejo de parámetros de transmisión
Probar iteradores de operaciones masivas
Probar el manejo de errores

**Tipos** (`test_types.py`):
Probar nuevos tipos de fragmentos de transmisión
Probar la serialización/deserialización de tipos

### Pruebas de Integración

**REST de Extremo a Extremo** (`test_integration_rest.py`):
Probar todas las operaciones contra la puerta de enlace real (modo REST)
Verificar la compatibilidad con versiones anteriores
Probar condiciones de error

**WebSocket de Extremo a Extremo** (`test_integration_websocket.py`):
Probar todas las operaciones contra la puerta de enlace real (modo WebSocket)
Probar operaciones de transmisión
Probar operaciones masivas
Probar solicitudes concurrentes
Probar la recuperación de la conexión

**Servicios de Transmisión** (`test_streaming_integration.py`):
Probar la transmisión de agentes (pensamientos, observaciones, respuestas)
Probar la transmisión de RAG (fragmentos incrementales)
Probar la transmisión de finalización de texto (token por token)
Probar la transmisión de indicaciones
Probar el manejo de errores durante la transmisión

**Operaciones Masivas** (`test_bulk_integration.py`):
Probar la importación/exportación masiva de triples (1K, 10K, 100K elementos)
Probar la importación/exportación masiva de incrustaciones
Probar el uso de memoria durante las operaciones masivas
Probar el seguimiento del progreso

### Pruebas de Rendimiento

**Mediciones de Latencia** (`test_performance_latency.py`):
Medir el tiempo hasta el primer token (transmisión vs. no transmisión)
Medir la sobrecarga de la conexión (REST vs WebSocket)
Comparar con puntos de referencia esperados

**Mediciones de Rendimiento** (`test_performance_throughput.py`):
Medir el rendimiento de la importación masiva
Medir la eficiencia del multiplexado de solicitudes
Comparar con puntos de referencia esperados

### Pruebas de Compatibilidad

**Compatibilidad con Versiones Anteriores** (`test_backward_compatibility.py`):
Ejecutar el conjunto de pruebas existente contra la API refactorizada
Verificar la ausencia de cambios que rompan la compatibilidad
Probar la ruta de migración para patrones comunes

## Plan de Migración

### Fase 1: Migración Transparente (Predeterminada)

**No se requieren cambios en el código**. El código existente continúa funcionando:

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### Fase 2: Transmisión por demanda (Simple)

**Utilice la interfaz `api.socket()`** para habilitar la transmisión:

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

**Puntos clave:**
La misma URL para REST y WebSocket.
Las mismas firmas de métodos (migración sencilla).
Simplemente agregue `.socket()` y `streaming=True`.

### Fase 3: Operaciones masivas (Nueva funcionalidad)

**Utilice la interfaz `api.bulk()`** para conjuntos de datos grandes:

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

### Actualizaciones de la documentación

1. **README.md**: Agregar ejemplos de transmisión y WebSocket
2. **Referencia de la API**: Documentar todos los nuevos métodos y parámetros
3. **Guía de migración**: Guía paso a paso para habilitar la transmisión
4. **Ejemplos**: Agregar scripts de ejemplo para patrones comunes
5. **Guía de rendimiento**: Documentar las mejoras de rendimiento esperadas

### Política de obsolescencia

**No hay obsolescencias**. Todas las API existentes siguen siendo compatibles. Esto es una mejora pura.

## Cronograma

### Semana 1: Base
Capa de abstracción de transporte
Refactorizar código REST existente
Pruebas unitarias para la capa de transporte
Verificación de compatibilidad con versiones anteriores

### Semana 2: Transporte WebSocket
Implementación del transporte WebSocket
Gestión de conexiones y reconexión
Multiplexación de solicitudes
Pruebas unitarias e de integración

### Semana 3: Soporte de transmisión
Agregar parámetro de transmisión a los métodos de LLM
Implementar el análisis de respuestas de transmisión
Agregar tipos de fragmentos de transmisión
Pruebas de integración de transmisión

### Semana 4: Operaciones masivas
Agregar métodos de importación/exportación masivos
Implementar operaciones basadas en iteradores
Pruebas de rendimiento
Pruebas de integración de operaciones masivas

### Semana 5: Paridad de funciones y documentación
Agregar consulta de incrustaciones de grafos
Agregar API de métricas
Documentación completa
Guía de migración
Versión candidata

### Semana 6: Lanzamiento
Pruebas de integración finales
Pruebas de referencia de rendimiento
Documentación de lanzamiento
Anuncio a la comunidad

**Duración total**: 6 semanas

## Preguntas abiertas

### Preguntas de diseño de la API

1. **Soporte asíncrono**: ✅ **RESUELTO** - Soporte asíncrono completo incluido en el lanzamiento inicial
   Todas las interfaces tienen variantes asíncronas: `async_flow()`, `async_socket()`, `async_bulk()`, `async_metrics()`
   Proporciona una simetría completa entre las API sincrónicas y asíncronas
   Esencial para marcos de trabajo asíncronos modernos (FastAPI, aiohttp)

2. **Seguimiento del progreso**: ¿Deben las operaciones masivas admitir devoluciones de llamada de progreso?
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   **Recomendación**: Agregar en la Fase 2. No es crítico para la versión inicial.

3. **Tiempo de espera de la transmisión**: ¿Cómo debemos manejar los tiempos de espera para las operaciones de transmisión?
   **Recomendación**: Utilizar el mismo tiempo de espera que para las operaciones no de transmisión, pero restablecerlo cada vez que se recibe un fragmento.

4. **Almacenamiento en búfer de fragmentos**: ¿Debemos almacenar los fragmentos en búfer o devolverlos inmediatamente?
   **Recomendación**: Devolverlos inmediatamente para lograr la menor latencia.

5. **Servicios globales a través de WebSocket**: ¿Debería `api.socket()` admitir servicios globales (biblioteca, conocimiento, colección, configuración) o solo servicios específicos del flujo?
   **Recomendación**: Comenzar solo con servicios específicos del flujo (donde la transmisión es importante). Agregar servicios globales si es necesario en la Fase 2.

### Preguntas de implementación

1. **Biblioteca de WebSocket**: ¿Debemos usar `websockets`, `websocket-client` o `aiohttp`?
   **Recomendación**: `websockets` (asíncrono, maduro, bien mantenido). Envolverlo en una interfaz síncrona utilizando `asyncio.run()`.

2. **Grupo de conexiones**: ¿Debemos admitir múltiples instancias concurrentes de `Api` que compartan un grupo de conexiones?
   **Recomendación**: Dejar para la Fase 2. Cada instancia de `Api` tendrá sus propias conexiones inicialmente.

3. **Reutilización de conexiones**: ¿Deben `SocketClient` y `BulkClient` compartir la misma conexión de WebSocket, o usar conexiones separadas?
   **Recomendación**: Conexiones separadas. Implementación más sencilla, separación de responsabilidades más clara.

4. **Conexión perezosa vs. activa**: ¿Se debe establecer la conexión de WebSocket en `api.socket()` o en la primera solicitud?
   **Recomendación**: Perezosa (en la primera solicitud). Evita la sobrecarga de la conexión si el usuario solo utiliza métodos REST.

### Preguntas de prueba

1. **Pasarela de simulación**: ¿Debemos crear una pasarela de simulación ligera para las pruebas, o probar contra la pasarela real?
   **Recomendación**: Ambos. Utilizar simulaciones para pruebas unitarias, y la pasarela real para pruebas de integración.

2. **Pruebas de regresión de rendimiento**: ¿Debemos agregar pruebas de regresión de rendimiento automatizadas a CI?
   **Recomendación**: Sí, pero con umbrales amplios para tener en cuenta la variabilidad del entorno de CI.

## Referencias

### Especificaciones técnicas relacionadas
`docs/tech-specs/streaming-llm-responses.md` - Implementación de transmisión en la pasarela
`docs/tech-specs/rag-streaming-support.md` - Soporte de transmisión RAG

### Archivos de implementación
`trustgraph-base/trustgraph/api/` - Código fuente de la API de Python
`trustgraph-flow/trustgraph/gateway/` - Código fuente de la pasarela
`trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - Implementación de referencia de multiplexor de WebSocket

### Documentación
`docs/apiSpecification.md` - Referencia completa de la API
`docs/api-status-summary.md` - Resumen del estado de la API
`README.websocket` - Documentación del protocolo WebSocket
`STREAMING-IMPLEMENTATION-NOTES.txt` - Notas de implementación de transmisión

### Bibliotecas externas
`websockets` - Biblioteca de WebSocket de Python (https://websockets.readthedocs.io/)
`requests` - Biblioteca HTTP de Python (existente)
