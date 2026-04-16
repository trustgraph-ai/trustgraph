---
layout: default
title: "Referencia de la API de Python de TrustGraph"
parent: "Spanish (Beta)"
---

# Referencia de la API de Python de TrustGraph

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Instalación

```bash
pip install trustgraph
```

## Inicio rápido

Todas las clases y tipos se importan del paquete `trustgraph.api`:

```python
from trustgraph.api import Api, Triple, ConfigKey

# Create API client
api = Api(url="http://localhost:8088/")

# Get a flow instance
flow = api.flow().id("default")

# Execute a graph RAG query
response = flow.graph_rag(
    query="What are the main topics?",
    user="trustgraph",
    collection="default"
)
```

## Tabla de Contenidos

### Núcleo

[Api](#api)

### Clientes de Flujo

[Flow](#flow)
[FlowInstance](#flowinstance)
[AsyncFlow](#asyncflow)
[AsyncFlowInstance](#asyncflowinstance)

### Clientes de WebSocket

[SocketClient](#socketclient)
[SocketFlowInstance](#socketflowinstance)
[AsyncSocketClient](#asyncsocketclient)
[AsyncSocketFlowInstance](#asyncsocketflowinstance)

### Operaciones Masivas

[BulkClient](#bulkclient)
[AsyncBulkClient](#asyncbulkclient)

### Métricas

[Metrics](#metrics)
[AsyncMetrics](#asyncmetrics)

### Tipos de Datos

[Triple](#triple)
[ConfigKey](#configkey)
[ConfigValue](#configvalue)
[DocumentMetadata](#documentmetadata)
[ProcessingMetadata](#processingmetadata)
[CollectionMetadata](#collectionmetadata)
[StreamingChunk](#streamingchunk)
[AgentThought](#agentthought)
[AgentObservation](#agentobservation)
[AgentAnswer](#agentanswer)
[RAGChunk](#ragchunk)

### Excepciones

[ProtocolException](#protocolexception)
[TrustGraphException](#trustgraphexception)
[AgentError](#agenterror)
[ConfigError](#configerror)
[DocumentRagError](#documentragerror)
[FlowError](#flowerror)
[GatewayError](#gatewayerror)
[GraphRagError](#graphragerror)
[LLMError](#llmerror)
[LoadError](#loaderror)
[LookupError](#lookuperror)
[NLPQueryError](#nlpqueryerror)
[RowsQueryError](#rowsqueryerror)
[RequestError](#requesterror)
[StructuredQueryError](#structuredqueryerror)
[UnexpectedError](#unexpectederror)
[ApplicationException](#applicationexception)

--

## `Api`

```python
from trustgraph.api import Api
```

Cliente principal de la API TrustGraph para operaciones sincrónicas y asincrónicas.

Esta clase proporciona acceso a todos los servicios de TrustGraph, incluyendo la gestión de flujos,
operaciones de grafos de conocimiento, procesamiento de documentos, consultas RAG y más. Soporta
tanto patrones de comunicación basados en REST como en WebSocket.

El cliente se puede utilizar como un administrador de contexto para la limpieza automática de recursos:
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### Métodos

### `__aenter__(self)`

Ingrese al administrador de contexto asíncrono.

### `__aexit__(self, *args)`

Salga del administrador de contexto asíncrono y cierre las conexiones.

### `__enter__(self)`

Ingrese al administrador de contexto síncrono.

### `__exit__(self, *args)`

Salga del administrador de contexto síncrono y cierre las conexiones.

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

Inicialice el cliente de la API TrustGraph.

**Argumentos:**

`url`: URL base para la API TrustGraph (por defecto: "http://localhost:8088/"")
`timeout`: Tiempo de espera de la solicitud en segundos (por defecto: 60)
`token`: Token de portador opcional para la autenticación

**Ejemplo:**

```python
# Local development
api = Api()

# Production with authentication
api = Api(
    url="https://trustgraph.example.com/",
    timeout=120,
    token="your-api-token"
)
```

### `aclose(self)`

Cerrar todas las conexiones de cliente asíncronas.

Este método cierra las conexiones asíncronas de WebSocket, las operaciones masivas y los flujos.
Se llama automáticamente al salir de un administrador de contexto asíncrono.

**Ejemplo:**

```python
api = Api()
async_socket = api.async_socket()
# ... use async_socket
await api.aclose()  # Clean up connections

# Or use async context manager (automatic cleanup)
async with Api() as api:
    async_socket = api.async_socket()
    # ... use async_socket
# Automatically closed
```

### `async_bulk(self)`

Obtenga un cliente para operaciones masivas asíncronas.

Proporciona operaciones de importación/exportación masivas en estilo async/await a través de WebSocket
para un manejo eficiente de grandes conjuntos de datos.

**Devuelve:** AsyncBulkClient: Cliente para operaciones masivas asíncronas.

**Ejemplo:**

```python
async_bulk = api.async_bulk()

# Export triples asynchronously
async for triple in async_bulk.export_triples(flow="default"):
    print(f"{triple.s} {triple.p} {triple.o}")

# Import with async generator
async def triple_gen():
    yield Triple(s="subj", p="pred", o="obj")
    # ... more triples

await async_bulk.import_triples(
    flow="default",
    triples=triple_gen()
)
```

### `async_flow(self)`

Obtenga un cliente de flujo basado en REST asíncrono.

Proporciona acceso al estilo async/await a las operaciones de flujo. Esto es preferible
para aplicaciones y marcos de trabajo de Python asíncronos (FastAPI, aiohttp, etc.).

**Devuelve:** AsyncFlow: Cliente de flujo asíncrono

**Ejemplo:**

```python
async_flow = api.async_flow()

# List flows
flow_ids = await async_flow.list()

# Execute operations
instance = async_flow.id("default")
result = await instance.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `async_metrics(self)`

Obtenga un cliente de métricas asíncrono.

Proporciona acceso al estilo async/await a las métricas de Prometheus.

**Retorna:** AsyncMetrics: Cliente de métricas asíncrono

**Ejemplo:**

```python
async_metrics = api.async_metrics()
prometheus_text = await async_metrics.get()
print(prometheus_text)
```

### `async_socket(self)`

Obtenga un cliente WebSocket asíncrono para operaciones de transmisión.

Proporciona acceso a WebSocket con estilo async/await y soporte para transmisión.
Este es el método preferido para la transmisión asíncrona en Python.

**Retorna:** AsyncSocketClient: Cliente WebSocket asíncrono

**Ejemplo:**

```python
async_socket = api.async_socket()
flow = async_socket.flow("default")

# Stream agent responses
async for chunk in flow.agent(
    question="Explain quantum computing",
    user="trustgraph",
    streaming=True
):
    if hasattr(chunk, 'content'):
        print(chunk.content, end='', flush=True)
```

### `bulk(self)`

Obtenga un cliente de operaciones masivas sincrónicas para la importación/exportación.

Las operaciones masivas permiten la transferencia eficiente de grandes conjuntos de datos a través de conexiones WebSocket,
incluyendo triples, incrustaciones, contextos de entidades y objetos.

**Devuelve:** BulkClient: Cliente de operaciones masivas sincrónicas.

**Ejemplo:**

```python
bulk = api.bulk()

# Export triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} {triple.p} {triple.o}")

# Import triples
def triple_generator():
    yield Triple(s="subj", p="pred", o="obj")
    # ... more triples

bulk.import_triples(flow="default", triples=triple_generator())
```

### `close(self)`

Cerrar todas las conexiones de cliente sincrónicas.

Este método cierra las conexiones de WebSocket y de operaciones masivas.
Se llama automáticamente al salir de un administrador de contexto.

**Ejemplo:**

```python
api = Api()
socket = api.socket()
# ... use socket
api.close()  # Clean up connections

# Or use context manager (automatic cleanup)
with Api() as api:
    socket = api.socket()
    # ... use socket
# Automatically closed
```

### `collection(self)`

Obtenga un cliente de Collection para administrar colecciones de datos.

Las colecciones organizan documentos y datos de grafos de conocimiento en
agrupaciones lógicas para el aislamiento y el control de acceso.

**Devuelve:** Collection: Cliente de administración de colecciones

**Ejemplo:**

```python
collection = api.collection()

# List collections
colls = collection.list_collections(user="trustgraph")

# Update collection metadata
collection.update_collection(
    user="trustgraph",
    collection="default",
    name="Default Collection",
    description="Main data collection"
)
```

### `config(self)`

Obtenga un cliente de Config para administrar la configuración.

**Retorna:** Config: Cliente de administración de configuración

**Ejemplo:**

```python
config = api.config()

# Get configuration values
values = config.get([ConfigKey(type="llm", key="model")])

# Set configuration
config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
```

### `flow(self)`

Obtenga un cliente de Flow para administrar e interactuar con flujos.

Los flujos son las unidades de ejecución principales en TrustGraph, y proporcionan acceso a
servicios como agentes, consultas RAG, incrustaciones y procesamiento de documentos.

**Devuelve:** Flow: Cliente de administración de flujos.

**Ejemplo:**

```python
flow_client = api.flow()

# List available blueprints
blueprints = flow_client.list_blueprints()

# Get a specific flow instance
flow_instance = flow_client.id("default")
response = flow_instance.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `knowledge(self)`

Obtenga un cliente de Knowledge para administrar los núcleos de grafos de conocimiento.

**Retorna:** Knowledge: Cliente de administración de grafos de conocimiento.

**Ejemplo:**

```python
knowledge = api.knowledge()

# List available KG cores
cores = knowledge.list_kg_cores(user="trustgraph")

# Load a KG core
knowledge.load_kg_core(id="core-123", user="trustgraph")
```

### `library(self)`

Obtenga un cliente de la biblioteca para la gestión de documentos.

La biblioteca proporciona almacenamiento de documentos, gestión de metadatos y
coordinación del flujo de trabajo de procesamiento.

**Devuelve:** Biblioteca: Cliente de gestión de la biblioteca de documentos

**Ejemplo:**

```python
library = api.library()

# Add a document
library.add_document(
    document=b"Document content",
    id="doc-123",
    metadata=[],
    user="trustgraph",
    title="My Document",
    comments="Test document"
)

# List documents
docs = library.get_documents(user="trustgraph")
```

### `metrics(self)`

Obtiene un cliente de métricas sincrónico para la monitorización.

Recupera métricas en formato Prometheus del servicio TrustGraph
para la monitorización y la observabilidad.

**Devuelve:** Métricas: Cliente de métricas sincrónico

**Ejemplo:**

```python
metrics = api.metrics()
prometheus_text = metrics.get()
print(prometheus_text)
```

### `request(self, path, request)`

Realizar una solicitud de API REST de bajo nivel.

Este método se utiliza principalmente para uso interno, pero se puede utilizar para acceder directamente
a la API cuando sea necesario.

**Argumentos:**

`path`: Ruta del punto final de la API (relativa a la URL base)
`request`: Carga útil de la solicitud como un diccionario

**Retorna:** dict: Objeto de respuesta

**Lanza:**

`ProtocolException`: Si el estado de la respuesta no es 200 o la respuesta no es JSON
`ApplicationException`: Si la respuesta contiene un error

**Ejemplo:**

```python
response = api.request("flow", {
    "operation": "list-flows"
})
```

### `socket(self)`

Obtenga un cliente WebSocket síncrono para operaciones de transmisión.

Las conexiones WebSocket proporcionan soporte de transmisión para respuestas en tiempo real
de agentes, consultas RAG y finalizaciones de texto. Este método devuelve un
envoltorio síncrono alrededor del protocolo WebSocket.

**Retorna:** SocketClient: Cliente WebSocket síncrono

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent responses
for chunk in flow.agent(
    question="Explain quantum computing",
    user="trustgraph",
    streaming=True
):
    if hasattr(chunk, 'content'):
        print(chunk.content, end='', flush=True)
```


--

## `Flow`

```python
from trustgraph.api import Flow
```

Cliente de gestión de flujo para operaciones de planos de flujo y instancias de flujo.

Esta clase proporciona métodos para administrar planos de flujo (plantillas) y
instancias de flujo (flujos en ejecución). Los planos definen la estructura y
los parámetros de los flujos, mientras que las instancias representan flujos activos que
pueden ejecutar servicios.

### Métodos

### `__init__(self, api)`

Inicializar el cliente de flujo.

**Argumentos:**

`api`: Instancia de Api principal para realizar solicitudes.

### `delete_blueprint(self, blueprint_name)`

Eliminar un plano de flujo.

**Argumentos:**

`blueprint_name`: Nombre del plano a eliminar.

**Ejemplo:**

```python
api.flow().delete_blueprint("old-blueprint")
```

### `get(self, id)`

Obtener la definición de una instancia de flujo en ejecución.

**Argumentos:**

`id`: ID de la instancia de flujo

**Retorna:** dict: Definición de la instancia de flujo

**Ejemplo:**

```python
flow_def = api.flow().get("default")
print(flow_def)
```

### `get_blueprint(self, blueprint_name)`

Obtener una definición de diagrama de flujo por nombre.

**Argumentos:**

`blueprint_name`: Nombre del diagrama de flujo a recuperar

**Retorna:** dict: Definición del diagrama de flujo como un diccionario

**Ejemplo:**

```python
blueprint = api.flow().get_blueprint("default")
print(blueprint)  # Blueprint configuration
```

### `id(self, id='default')`

Obtener una instancia de FlowInstance para ejecutar operaciones en un flujo específico.

**Argumentos:**

`id`: Identificador del flujo (predeterminado: "default")

**Retorna:** FlowInstance: Instancia de flujo para operaciones de servicio

**Ejemplo:**

```python
flow = api.flow().id("my-flow")
response = flow.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `list(self)`

Listar todas las instancias de flujo activas.

**Retorna:** list[str]: Lista de identificadores de instancias de flujo.

**Ejemplo:**

```python
flows = api.flow().list()
print(flows)  # ['default', 'flow-1', 'flow-2', ...]
```

### `list_blueprints(self)`

Listar todos los planos de flujo disponibles.

**Retorna:** list[str]: Lista de nombres de planos.

**Ejemplo:**

```python
blueprints = api.flow().list_blueprints()
print(blueprints)  # ['default', 'custom-flow', ...]
```

### `put_blueprint(self, blueprint_name, definition)`

Crear o actualizar un esquema de flujo.

**Argumentos:**

`blueprint_name`: Nombre para el esquema.
`definition`: Diccionario de definición del esquema.

**Ejemplo:**

```python
definition = {
    "services": ["text-completion", "graph-rag"],
    "parameters": {"model": "gpt-4"}
}
api.flow().put_blueprint("my-blueprint", definition)
```

### `request(self, path=None, request=None)`

Realizar una solicitud de API con ámbito de flujo.

**Argumentos:**

`path`: Sufijo de ruta opcional para los puntos finales de flujo.
`request`: Diccionario de carga útil de la solicitud.

**Retorna:** dict: Objeto de respuesta.

**Genera:**

`RuntimeError`: Si no se especifica el parámetro de solicitud.

### `start(self, blueprint_name, id, description, parameters=None)`

Iniciar una nueva instancia de flujo a partir de un plano.

**Argumentos:**

`blueprint_name`: Nombre del plano a instanciar.
`id`: Identificador único para la instancia de flujo.
`description`: Descripción legible por humanos.
`parameters`: Diccionario de parámetros opcionales.

**Ejemplo:**

```python
api.flow().start(
    blueprint_name="default",
    id="my-flow",
    description="My custom flow",
    parameters={"model": "gpt-4"}
)
```

### `stop(self, id)`

Detener una instancia de flujo en ejecución.

**Argumentos:**

`id`: ID de la instancia de flujo a detener.

**Ejemplo:**

```python
api.flow().stop("my-flow")
```


--

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

Cliente de instancia de flujo para ejecutar servicios en un flujo específico.

Esta clase proporciona acceso a todos los servicios de TrustGraph, incluyendo:
Completado de texto y embeddings
Operaciones de agentes con gestión de estado
Consultas RAG de gráficos y documentos
Operaciones de grafos de conocimiento (triples, objetos)
Carga y procesamiento de documentos
Conversión de lenguaje natural a consulta GraphQL
Análisis de datos estructurados y detección de esquemas
Ejecución de herramientas MCP
Plantillas de prompts

Los servicios se acceden a través de una instancia de flujo en ejecución identificada por ID.

### Métodos

### `__init__(self, api, id)`

Inicializar FlowInstance.

**Argumentos:**

`api`: Cliente de flujo padre
`id`: Identificador de la instancia de flujo

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

Ejecutar una operación de agente con capacidades de razonamiento y uso de herramientas.

Los agentes pueden realizar razonamiento en múltiples pasos, usar herramientas y mantener el
estado de la conversación en las interacciones. Esta es una versión síncrona no basada en streaming.

**Argumentos:**

`question`: Pregunta o instrucción del usuario
`user`: Identificador del usuario (por defecto: "trustgraph")
`state`: Diccionario de estado opcional para conversaciones con estado
`group`: Identificador de grupo opcional para contextos multiusuario
`history`: Historial de conversación opcional como lista de diccionarios de mensajes

**Retorna:** str: Respuesta final del agente

**Ejemplo:**

```python
flow = api.flow().id("default")

# Simple question
answer = flow.agent(
    question="What is the capital of France?",
    user="trustgraph"
)

# With conversation history
history = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
]
answer = flow.agent(
    question="Tell me about Paris",
    user="trustgraph",
    history=history
)
```

### `detect_type(self, sample)`

Detectar el tipo de datos de una muestra de datos estructurados.

**Argumentos:**

`sample`: Muestra de datos a analizar (contenido de cadena)

**Retorna:** diccionario con detected_type, confidence y metadatos opcionales.

### `diagnose_data(self, sample, schema_name=None, options=None)`

Realizar un diagnóstico de datos combinado: detectar el tipo y generar un descriptor.

**Argumentos:**

`sample`: Muestra de datos a analizar (contenido de cadena)
`schema_name`: Nombre de esquema de destino opcional para la generación del descriptor.
`options`: Parámetros opcionales (por ejemplo, delimitador para CSV).

**Retorna:** diccionario con detected_type, confidence, descriptor y metadatos.

### `document_embeddings_query(self, text, user, collection, limit=10)`

Consultar fragmentos de documentos utilizando similitud semántica.

Encuentra fragmentos de documentos cuyo contenido sea semánticamente similar al
texto de entrada, utilizando incrustaciones vectoriales.

**Argumentos:**

`text`: Texto de consulta para la búsqueda semántica.
`user`: Identificador de usuario/espacio de claves.
`collection`: Identificador de colección.
`limit`: Número máximo de resultados (por defecto: 10).

**Retorna:** diccionario: Resultados de la consulta con fragmentos que contienen chunk_id y score.

**Ejemplo:**

```python
flow = api.flow().id("default")
results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "doc1/p0/c0", "score": 0.95}, ...]}
```

### `document_rag(self, query, user='trustgraph', collection='default', doc_limit=10)`

Ejecutar una consulta de Generación Aumentada por Recuperación (RAG) basada en documentos.

RAG basada en documentos utiliza incrustaciones vectoriales para encontrar fragmentos de documentos relevantes,
y luego genera una respuesta utilizando un LLM con esos fragmentos como contexto.

**Argumentos:**

`query`: Consulta en lenguaje natural
`user`: Identificador de usuario/espacio de claves (por defecto: "trustgraph")
`collection`: Identificador de colección (por defecto: "default")
`doc_limit`: Número máximo de fragmentos de documentos a recuperar (por defecto: 10)

**Retorna:** str: Respuesta generada que incorpora el contexto del documento

**Ejemplo:**

```python
flow = api.flow().id("default")
response = flow.document_rag(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5
)
print(response)
```

### `embeddings(self, texts)`

Genera incrustaciones vectoriales para uno o más textos.

Convierte textos en representaciones vectoriales densas adecuadas para la
búsqueda semántica y la comparación de similitud.

**Argumentos:**

`texts`: Lista de textos de entrada para incrustar

**Retorna:** list[list[list[float]]]: Incrustaciones vectoriales, un conjunto por texto de entrada

**Ejemplo:**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

Generar un descriptor para el mapeo de datos estructurados a un esquema específico.

**Argumentos:**

`sample`: Muestra de datos a analizar (contenido de cadena)
`data_type`: Tipo de datos (csv, json, xml)
`schema_name`: Nombre del esquema de destino para la generación del descriptor
`options`: Parámetros opcionales (por ejemplo, delimitador para CSV)

**Retorna:** diccionario con el descriptor y metadatos

### `graph_embeddings_query(self, text, user, collection, limit=10)`

Consultar entidades de un grafo de conocimiento utilizando similitud semántica.

Encuentra entidades en el grafo de conocimiento cuyas descripciones son semánticamente
similares al texto de entrada, utilizando incrustaciones vectoriales.

**Argumentos:**

`text`: Texto de consulta para la búsqueda semántica
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`limit`: Número máximo de resultados (por defecto: 10)

**Retorna:** diccionario: Resultados de la consulta con entidades similares

**Ejemplo:**

```python
flow = api.flow().id("default")
results = flow.graph_embeddings_query(
    text="physicist who discovered radioactivity",
    user="trustgraph",
    collection="scientists",
    limit=5
)
# results contains {"entities": [{"entity": {...}, "score": 0.95}, ...]}
```

### `graph_rag(self, query, user='trustgraph', collection='default', entity_limit=50, triple_limit=30, max_subgraph_size=150, max_path_length=2)`

Ejecutar una consulta de Generación Aumentada por Recuperación (RAG) basada en grafos.

Graph RAG utiliza la estructura del grafo de conocimiento para encontrar el contexto relevante mediante
el recorrido de las relaciones entre entidades, y luego genera una respuesta utilizando un LLM.

**Argumentos:**

`query`: Consulta en lenguaje natural
`user`: Identificador de usuario/espacio de claves (por defecto: "trustgraph")
`collection`: Identificador de colección (por defecto: "default")
`entity_limit`: Número máximo de entidades a recuperar (por defecto: 50)
`triple_limit`: Número máximo de triples por entidad (por defecto: 30)
`max_subgraph_size`: Número máximo total de triples en el subgrafo (por defecto: 150)
`max_path_length`: Profundidad máxima de recorrido (por defecto: 2)

**Retorna:** str: Respuesta generada que incorpora el contexto del grafo

**Ejemplo:**

```python
flow = api.flow().id("default")
response = flow.graph_rag(
    query="Tell me about Marie Curie's discoveries",
    user="trustgraph",
    collection="scientists",
    entity_limit=20,
    max_path_length=3
)
print(response)
```

### `load_document(self, document, id=None, metadata=None, user=None, collection=None)`

Cargar un documento binario para su procesamiento.

Sube un documento (PDF, DOCX, imágenes, etc.) para la extracción y
procesamiento a través de la canalización de documentos del flujo.

**Argumentos:**

`document`: Contenido del documento como bytes
`id`: Identificador de documento opcional (se genera automáticamente si es None)
`metadata`: Metadatos opcionales (lista de Triples o objeto con método emit)
`user`: Identificador de usuario/espacio de claves (opcional)
`collection`: Identificador de colección (opcional)

**Retorna:** dict: Respuesta de procesamiento

**Lanza:**

`RuntimeError`: Si se proporcionan metadatos sin id

**Ejemplo:**

```python
flow = api.flow().id("default")

# Load a PDF document
with open("research.pdf", "rb") as f:
    result = flow.load_document(
        document=f.read(),
        id="research-001",
        user="trustgraph",
        collection="papers"
    )
```

### `load_text(self, text, id=None, metadata=None, charset='utf-8', user=None, collection=None)`

Cargar contenido de texto para su procesamiento.

Carga contenido de texto para la extracción y el procesamiento a través de la
canalización de texto del flujo.

**Argumentos:**

`text`: Contenido de texto como bytes
`id`: Identificador de documento opcional (se genera automáticamente si es None)
`metadata`: Metadatos opcionales (lista de Triples o objeto con método emit)
`charset`: Codificación de caracteres (predeterminado: "utf-8")
`user`: Identificador de usuario/espacio de claves (opcional)
`collection`: Identificador de colección (opcional)

**Retorna:** dict: Respuesta de procesamiento

**Genera:**

`RuntimeError`: Si se proporcionan metadatos sin id

**Ejemplo:**

```python
flow = api.flow().id("default")

# Load text content
text_content = b"This is the document content..."
result = flow.load_text(
    text=text_content,
    id="text-001",
    charset="utf-8",
    user="trustgraph",
    collection="documents"
)
```

### `mcp_tool(self, name, parameters={})`

Ejecutar una herramienta de Protocolo de Contexto de Modelo (MCP).

Las herramientas MCP proporcionan funcionalidades extensibles para agentes y flujos de trabajo,
permitiendo la integración con sistemas y servicios externos.

**Argumentos:**

`name`: Nombre/identificador de la herramienta
`parameters`: Diccionario de parámetros de la herramienta (por defecto: {})

**Retorna:** str o dict: Resultado de la ejecución de la herramienta

**Genera:**

`ProtocolException`: Si el formato de la respuesta no es válido

**Ejemplo:**

```python
flow = api.flow().id("default")

# Execute a tool
result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `nlp_query(self, question, max_results=100)`

Convertir una pregunta en lenguaje natural en una consulta GraphQL.

**Argumentos:**

`question`: Pregunta en lenguaje natural
`max_results`: Número máximo de resultados a devolver (por defecto: 100)

**Retorna:** diccionario con graphql_query, variables, detected_schemas, confidence

### `prompt(self, id, variables)`

Ejecutar una plantilla de prompt con sustitución de variables.

Las plantillas de solicitud permiten patrones de solicitud reutilizables con variables dinámicas.
de sustitución, útiles para una ingeniería de solicitudes consistente.

**Argumentos:**

`id`: Identificador de la plantilla de solicitud.
`variables`: Diccionario de mapeos de nombres de variables a valores.

**Retorna:** str o dict: Resultado de la solicitud renderizada (texto u objeto estructurado).

**Genera:**

`ProtocolException`: Si el formato de la respuesta no es válido.

**Ejemplo:**

```python
flow = api.flow().id("default")

# Text template
result = flow.prompt(
    id="summarize-template",
    variables={"topic": "quantum computing", "length": "brief"}
)

# Structured template
result = flow.prompt(
    id="extract-entities",
    variables={"text": "Marie Curie won Nobel Prizes"}
)
```

### `request(self, path, request)`

Realice una solicitud de servicio en esta instancia de flujo.

**Argumentos:**

`path`: Ruta del servicio (por ejemplo, "service/text-completion")
`request`: Diccionario de carga útil de la solicitud

**Retorna:** dict: Respuesta del servicio

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

Consulta datos de fila utilizando similitud semántica en campos indexados.

Encuentra filas cuyos valores de campo indexados son semánticamente similares al
texto de entrada, utilizando incrustaciones vectoriales. Esto permite la coincidencia difusa/semántica
en datos estructurados.

**Argumentos:**

`text`: Texto de consulta para la búsqueda semántica
`schema_name`: Nombre del esquema para buscar
`user`: Identificador de usuario/espacio de claves (predeterminado: "trustgraph")
`collection`: Identificador de colección (predeterminado: "default")
`index_name`: Nombre de índice opcional para filtrar la búsqueda a un índice específico
`limit`: Número máximo de resultados (predeterminado: 10)

**Retorna:** dict: Resultados de la consulta con coincidencias que contienen index_name, index_value, text y score

**Ejemplo:**

```python
flow = api.flow().id("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query, user='trustgraph', collection='default', variables=None, operation_name=None)`

Ejecutar una consulta GraphQL contra filas estructuradas en el grafo de conocimiento.

Consulta datos estructurados utilizando la sintaxis GraphQL, lo que permite consultas complejas
con filtrado, agregación y recorrido de relaciones.

**Argumentos:**

`query`: Cadena de consulta GraphQL
`user`: Identificador de usuario/espacio de claves (por defecto: "trustgraph")
`collection`: Identificador de colección (por defecto: "default")
`variables`: Diccionario opcional de variables de consulta
`operation_name`: Nombre de operación opcional para documentos de múltiples operaciones

**Retorna:** dict: Respuesta GraphQL con los campos 'data', 'errors' y/o 'extensions'

**Genera:**

`ProtocolException`: Si ocurre un error a nivel del sistema

**Ejemplo:**

```python
flow = api.flow().id("default")

# Simple query
query = '''
{
  scientists(limit: 10) {
    name
    field
    discoveries
  }
}
'''
result = flow.rows_query(
    query=query,
    user="trustgraph",
    collection="scientists"
)

# Query with variables
query = '''
query GetScientist($name: String!) {
  scientists(name: $name) {
    name
    nobelPrizes
  }
}
'''
result = flow.rows_query(
    query=query,
    variables={"name": "Marie Curie"}
)
```

### `schema_selection(self, sample, options=None)`

Seleccionar esquemas coincidentes para una muestra de datos utilizando análisis de consultas.

**Argumentos:**

`sample`: Muestra de datos a analizar (contenido de cadena)
`options`: Parámetros opcionales

**Retorna:** diccionario con el array schema_matches y metadatos

### `structured_query(self, question, user='trustgraph', collection='default')`

Ejecutar una pregunta en lenguaje natural contra datos estructurados.
Combina la conversión de consultas NLP y la ejecución de GraphQL.

**Argumentos:**

`question`: Pregunta en lenguaje natural
`user`: Identificador de keyspace de Cassandra (por defecto: "trustgraph")
`collection`: Identificador de colección de datos (por defecto: "default")

**Retorna:** diccionario con datos y posibles errores

### `text_completion(self, system, prompt)`

Ejecutar la finalización de texto utilizando el LLM del flujo.

**Argumentos:**

`system`: Prompt del sistema que define el comportamiento del asistente
`prompt`: Prompt/pregunta del usuario

**Retorna:** str: Texto de respuesta generado

**Ejemplo:**

```python
flow = api.flow().id("default")
response = flow.text_completion(
    system="You are a helpful assistant",
    prompt="What is quantum computing?"
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

Consultar tripletas del grafo de conocimiento utilizando la coincidencia de patrones.

Busca tripletas RDF que coincidan con los patrones de sujeto, predicado y/o
objeto dados. Los parámetros no especificados actúan como comodines.

**Argumentos:**

`s`: URI del sujeto (opcional, usar None para comodín)
`p`: URI del predicado (opcional, usar None para comodín)
`o`: URI del objeto o Literal (opcional, usar None para comodín)
`user`: Identificador de usuario/espacio de claves (opcional)
`collection`: Identificador de colección (opcional)
`limit`: Número máximo de resultados a devolver (por defecto: 10000)

**Devuelve:** list[Triple]: Lista de objetos Triple coincidentes

**Genera:**

`RuntimeError`: Si s o p no son un Uri, o o no es un Uri/Literal

**Ejemplo:**

```python
from trustgraph.knowledge import Uri, Literal

flow = api.flow().id("default")

# Find all triples about a specific subject
triples = flow.triples_query(
    s=Uri("http://example.org/person/marie-curie"),
    user="trustgraph",
    collection="scientists"
)

# Find all instances of a specific relationship
triples = flow.triples_query(
    p=Uri("http://example.org/ontology/discovered"),
    limit=100
)
```


--

## `AsyncFlow`

```python
from trustgraph.api import AsyncFlow
```

Cliente de gestión de flujos asíncronos que utiliza la API REST.

Proporciona operaciones de gestión de flujos basadas en async/await, incluyendo listar,
iniciar, detener flujos y gestionar definiciones de clases de flujos. También proporciona
acceso a servicios específicos del flujo, como agentes, RAG y consultas, a través de
puntos finales REST no basados en transmisión.

Nota: Para el soporte de transmisión, utilice AsyncSocketClient en su lugar.

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicializa el cliente de flujo asíncrono.

**Argumentos:**

`url`: URL base para la API de TrustGraph
`timeout`: Tiempo de espera de la solicitud en segundos
`token`: Token de portador opcional para la autenticación

### `aclose(self) -> None`

Cierra el cliente asíncrono y libera recursos.

Nota: La limpieza se gestiona automáticamente por los administradores de contexto de sesión de aiohttp.
Este método se proporciona para mantener la coherencia con otros clientes asíncronos.

### `delete_class(self, class_name: str)`

Elimina una definición de clase de flujo.

Elimina una plantilla de clase de flujo del sistema. No afecta a
instancias de flujo en ejecución.

**Argumentos:**

`class_name`: Nombre de la clase de flujo a eliminar

**Ejemplo:**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

Obtener la definición del flujo.

Recupera la configuración completa del flujo, incluyendo su nombre de clase,
descripción y parámetros.

**Argumentos:**

`id`: Identificador del flujo

**Retorna:** dict: Objeto de definición del flujo

**Ejemplo:**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

Obtener la definición de la clase de flujo.

Recupera la definición del esquema para una clase de flujo, incluyendo su
esquema de configuración y enlaces de servicio.

**Argumentos:**

`class_name`: Nombre de la clase de flujo

**Retorna:** dict: Objeto de definición de la clase de flujo

**Ejemplo:**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

Obtener una instancia de cliente de flujo asíncrono.

Devuelve un cliente para interactuar con los servicios de un flujo específico
(agente, RAG, consultas, incrustaciones, etc.).

**Argumentos:**

`flow_id`: Identificador del flujo

**Devuelve:** AsyncFlowInstance: Cliente para operaciones específicas del flujo

**Ejemplo:**

```python
async_flow = await api.async_flow()

# Get flow instance
flow = async_flow.id("default")

# Use flow services
result = await flow.graph_rag(
    query="What is TrustGraph?",
    user="trustgraph",
    collection="default"
)
```

### `list(self) -> List[str]`

Listar todos los identificadores de flujo.

Recupera los ID de todos los flujos actualmente implementados en el sistema.

**Retorna:** list[str]: Lista de identificadores de flujo.

**Ejemplo:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

Listar todos los nombres de las clases de flujo.

Recupera los nombres de todas las clases de flujo (plantillas) disponibles en el sistema.

**Retorna:** list[str]: Lista de nombres de clases de flujo.

**Ejemplo:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

Crear o actualizar una definición de clase de flujo.

Almacena un esquema de clase de flujo que se puede utilizar para instanciar flujos.

**Argumentos:**

`class_name`: Nombre de la clase de flujo
`definition`: Objeto de definición de la clase de flujo

**Ejemplo:**

```python
async_flow = await api.async_flow()

# Create a custom flow class
class_def = {
    "services": {
        "agent": {"module": "agent", "config": {...}},
        "graph-rag": {"module": "graph-rag", "config": {...}}
    }
}
await async_flow.put_class("custom-flow", class_def)
```

### `request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Realizar una solicitud HTTP POST asíncrona a la API de Gateway.

Método interno para realizar solicitudes autenticadas a la API de TrustGraph.

**Argumentos:**

`path`: Ruta de punto final de la API (relativa a la URL base)
`request_data`: Diccionario de carga útil de la solicitud

**Retorna:** dict: Objeto de respuesta de la API

**Genera:**

`ProtocolException`: Si el estado HTTP no es 200 o la respuesta no es un JSON válido
`ApplicationException`: Si la API devuelve una respuesta de error

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

Inicia una nueva instancia de flujo.

Crea e inicia un flujo a partir de una definición de clase de flujo con los
parámetros especificados.

**Argumentos:**

`class_name`: Nombre de la clase de flujo a instanciar
`id`: Identificador para la nueva instancia de flujo
`description`: Descripción legible por humanos del flujo
`parameters`: Parámetros de configuración opcionales para el flujo

**Ejemplo:**

```python
async_flow = await api.async_flow()

# Start a flow from a class
await async_flow.start(
    class_name="default",
    id="my-flow",
    description="Custom flow instance",
    parameters={"model": "claude-3-opus"}
)
```

### `stop(self, id: str)`

Detener un flujo en ejecución.

Detiene y elimina una instancia de flujo, liberando sus recursos.

**Argumentos:**

`id`: Identificador del flujo a detener

**Ejemplo:**

```python
async_flow = await api.async_flow()

# Stop a flow
await async_flow.stop("my-flow")
```


--

## `AsyncFlowInstance`

```python
from trustgraph.api import AsyncFlowInstance
```

Cliente de instancia de flujo asíncrono.

Proporciona acceso async/await a servicios con ámbito de flujo, incluyendo agentes,
consultas RAG, incrustaciones y consultas de grafos. Todas las operaciones devuelven
respuestas completas (no en streaming).

Nota: Para soporte de streaming, utilice AsyncSocketFlowInstance en su lugar.

### Métodos

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

Inicializa una instancia de flujo asíncrono.

**Argumentos:**

`flow`: Cliente AsyncFlow padre
`flow_id`: Identificador de flujo

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

Ejecuta una operación de agente (no en streaming).

Ejecuta un agente para responder a una pregunta, con un estado de conversación opcional y
historial. Devuelve la respuesta completa después de que el agente haya terminado de
procesar.

Nota: Este método no admite streaming. Para los pensamientos y observaciones del agente en tiempo real,
utilice AsyncSocketFlowInstance.agent() en su lugar.

**Argumentos:**

`question`: Pregunta o instrucción del usuario
`user`: Identificador del usuario
`state`: Diccionario de estado opcional para el contexto de la conversación
`group`: Identificador de grupo opcional para la gestión de sesiones
`history`: Lista de historial de conversación opcional
`**kwargs`: Parámetros adicionales específicos del servicio

**Devuelve:** dict: Respuesta completa del agente, incluyendo la respuesta y los metadatos

**Ejemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Execute agent
result = await flow.agent(
    question="What is the capital of France?",
    user="trustgraph"
)
print(f"Answer: {result.get('response')}")
```

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> str`

Ejecutar consulta RAG basada en documentos (no en streaming).

Realiza Generación Aumentada por Recuperación utilizando incrustaciones de documentos.
Recupera fragmentos de documentos relevantes mediante búsqueda semántica y luego genera
una respuesta basada en los documentos recuperados. Devuelve la respuesta completa.

Nota: Este método no admite el streaming. Para respuestas RAG en streaming,
utilice AsyncSocketFlowInstance.document_rag() en su lugar.

**Argumentos:**

`query`: Texto de la consulta del usuario
`user`: Identificador del usuario
`collection`: Identificador de la colección que contiene los documentos
`doc_limit`: Número máximo de fragmentos de documentos a recuperar (por defecto: 10)
`**kwargs`: Parámetros adicionales específicos del servicio

**Devuelve:** str: Respuesta generada completa basada en los datos del documento

**Ejemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Query documents
response = await flow.document_rag(
    query="What does the documentation say about authentication?",
    user="trustgraph",
    collection="docs",
    doc_limit=5
)
print(response)
```

### `embeddings(self, texts: list, **kwargs: Any)`

Generar incrustaciones (embeddings) para textos de entrada.

Convierte textos en representaciones vectoriales numéricas utilizando el modelo de incrustación configurado en el flujo. Útil para la búsqueda semántica y comparaciones de similitud.



**Argumentos:**

`texts`: Lista de textos de entrada para incrustar
`**kwargs`: Parámetros adicionales específicos del servicio

**Retorna:** dict: Respuesta que contiene vectores de incrustación

**Ejemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

Consulta incrustaciones de grafos para la búsqueda semántica de entidades.

Realiza una búsqueda semántica sobre las incrustaciones de entidades de grafos para encontrar entidades
más relevantes para el texto de entrada. Devuelve entidades clasificadas por similitud.

**Argumentos:**

`text`: Texto de consulta para la búsqueda semántica
`user`: Identificador de usuario
`collection`: Identificador de la colección que contiene las incrustaciones de grafos
`limit`: Número máximo de resultados a devolver (por defecto: 10)
`**kwargs`: Parámetros adicionales específicos del servicio

**Devuelve:** dict: Respuesta que contiene coincidencias de entidades clasificadas con puntuaciones de similitud

**Ejemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Find related entities
results = await flow.graph_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="tech-kb",
    limit=5
)

for entity in results.get("entities", []):
    print(f"{entity['name']}: {entity['score']}")
```

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> str`

Ejecutar consulta RAG basada en grafos (no en streaming).

Realiza la generación aumentada con recuperación utilizando datos de grafos de conocimiento.
Identifica entidades relevantes y sus relaciones, y luego genera una
respuesta basada en la estructura del grafo. Devuelve la respuesta completa.

Nota: Este método no admite el streaming. Para respuestas RAG en streaming,
utilice AsyncSocketFlowInstance.graph_rag() en su lugar.

**Argumentos:**

`query`: Texto de la consulta del usuario
`user`: Identificador del usuario
`collection`: Identificador de la colección que contiene el grafo de conocimiento
`max_subgraph_size`: Número máximo de triples por subgrafo (por defecto: 1000)
`max_subgraph_count`: Número máximo de subgrafos a recuperar (por defecto: 5)
`max_entity_distance`: Distancia máxima del grafo para la expansión de entidades (por defecto: 3)
`**kwargs`: Parámetros adicionales específicos del servicio

**Devuelve:** str: Respuesta completa generada basada en datos del grafo

**Ejemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Query knowledge graph
response = await flow.graph_rag(
    query="What are the relationships between these entities?",
    user="trustgraph",
    collection="medical-kb",
    max_subgraph_count=3
)
print(response)
```

### `request(self, service: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Realizar una solicitud a un servicio con ámbito de flujo.

Método interno para llamar a servicios dentro de esta instancia de flujo.

**Argumentos:**

`service`: Nombre del servicio (por ejemplo, "agent", "graph-rag", "triples")
`request_data`: Carga útil de la solicitud al servicio

**Retorna:** dict: Objeto de respuesta del servicio

**Lanza:**

`ProtocolException`: Si la solicitud falla o la respuesta es inválida
`ApplicationException`: Si el servicio devuelve un error

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

Consultar incrustaciones de filas para la búsqueda semántica en datos estructurados.

Realiza una búsqueda semántica sobre las incrustaciones del índice de filas para encontrar filas cuyas
valores de campo indexados sean más similares al texto de entrada. Permite
la coincidencia difusa/semántica en datos estructurados.

**Argumentos:**

`text`: Texto de consulta para la búsqueda semántica
`schema_name`: Nombre del esquema para buscar
`user`: Identificador de usuario (por defecto: "trustgraph")
`collection`: Identificador de colección (por defecto: "default")
`index_name`: Nombre de índice opcional para filtrar la búsqueda a un índice específico
`limit`: Número máximo de resultados a devolver (por defecto: 10)
`**kwargs`: Parámetros adicionales específicos del servicio

**Retorna:** dict: Respuesta que contiene coincidencias con index_name, index_value, text y score

**Ejemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Search for customers by name similarity
results = await flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

for match in results.get("matches", []):
    print(f"{match['index_name']}: {match['index_value']} (score: {match['score']})")
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs: Any)`

Ejecutar una consulta GraphQL en filas almacenadas.

Consulta filas de datos estructurados utilizando la sintaxis GraphQL. Soporta consultas complejas
con variables y operaciones con nombre.

**Argumentos:**

`query`: Cadena de consulta GraphQL
`user`: Identificador de usuario
`collection`: Identificador de la colección que contiene las filas
`variables`: Variables de consulta GraphQL opcionales
`operation_name`: Nombre de operación opcional para consultas con múltiples operaciones
`**kwargs`: Parámetros adicionales específicos del servicio

**Retorna:** dict: Respuesta GraphQL con datos y/o errores

**Ejemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Execute GraphQL query
query = '''
    query GetUsers($status: String!) {
        users(status: $status) {
            id
            name
            email
        }
    }
'''

result = await flow.rows_query(
    query=query,
    user="trustgraph",
    collection="users",
    variables={"status": "active"}
)

for user in result.get("data", {}).get("users", []):
    print(f"{user['name']}: {user['email']}")
```

### `text_completion(self, system: str, prompt: str, **kwargs: Any) -> str`

Generar finalización de texto (no en tiempo real).

Genera una respuesta de texto a partir de un modelo de lenguaje grande (LLM) dado un mensaje del sistema y un mensaje del usuario.
Devuelve el texto de la respuesta completo.

Nota: Este método no admite la transmisión. Para la generación de texto en tiempo real,
utilice AsyncSocketFlowInstance.text_completion() en su lugar.

**Argumentos:**

`system`: Mensaje del sistema que define el comportamiento del LLM.
`prompt`: Mensaje del usuario o pregunta.
`**kwargs`: Parámetros adicionales específicos del servicio.

**Devuelve:** str: Respuesta de texto generada completa.

**Ejemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate text
response = await flow.text_completion(
    system="You are a helpful assistant.",
    prompt="Explain quantum computing in simple terms."
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs: Any)`

Consultar triples RDF utilizando la coincidencia de patrones.

Busca triples que coincidan con los patrones especificados de sujeto, predicado y/o
objeto. Los patrones utilizan None como comodín para coincidir con cualquier valor.

**Argumentos:**

`s`: Patrón de sujeto (None para comodín)
`p`: Patrón de predicado (None para comodín)
`o`: Patrón de objeto (None para comodín)
`user`: Identificador de usuario (None para todos los usuarios)
`collection`: Identificador de colección (None para todas las colecciones)
`limit`: Número máximo de triples a devolver (por defecto: 100)
`**kwargs`: Parámetros adicionales específicos del servicio

**Devuelve:** dict: Respuesta que contiene los triples coincidentes

**Ejemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Find all triples with a specific predicate
results = await flow.triples_query(
    p="knows",
    user="trustgraph",
    collection="social",
    limit=50
)

for triple in results.get("triples", []):
    print(f"{triple['s']} knows {triple['o']}")
```


--

## `SocketClient`

```python
from trustgraph.api import SocketClient
```

Cliente WebSocket sincrónico para operaciones de transmisión.

Proporciona una interfaz sincrónica a los servicios TrustGraph basados en WebSocket,
envolviendo la biblioteca de WebSockets asíncronos con generadores sincrónicos para facilitar su uso.
Admite respuestas de transmisión de agentes, consultas RAG y finalizaciones de texto.

Nota: Este es un envoltorio sincrónico alrededor de operaciones de WebSocket asíncronas. Para
un soporte asíncrono real, utilice AsyncSocketClient en su lugar.

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicializa el cliente WebSocket sincrónico.

**Argumentos:**

`url`: URL base para la API de TrustGraph (HTTP/HTTPS se convertirá a WS/WSS)
`timeout`: Tiempo de espera de WebSocket en segundos
`token`: Token de portador opcional para la autenticación

### `close(self) -> None`

Cierra las conexiones WebSocket.

Nota: La limpieza se gestiona automáticamente por los administradores de contexto en el código asíncrono.

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

Obtiene una instancia de flujo para operaciones de transmisión de WebSocket.

**Argumentos:**

`flow_id`: Identificador de flujo

**Devuelve:** SocketFlowInstance: Instancia de flujo con métodos de transmisión

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent responses
for chunk in flow.agent(question="Hello", user="trustgraph", streaming=True):
    print(chunk.content, end='', flush=True)
```


--

## `SocketFlowInstance`

```python
from trustgraph.api import SocketFlowInstance
```

Instancia de flujo WebSocket sincrónico para operaciones de transmisión.

Proporciona la misma interfaz que FlowInstance de REST, pero con soporte de transmisión basado en WebSocket
para respuestas en tiempo real. Todos los métodos admiten un parámetro opcional
`streaming` para habilitar la entrega incremental de resultados.

### Métodos

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

Inicializar instancia de flujo de socket.

**Argumentos:**

`client`: SocketClient padre
`flow_id`: Identificador de flujo

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

Ejecutar una operación de agente con soporte de transmisión.

Los agentes pueden realizar razonamientos de varios pasos con el uso de herramientas. Este método siempre
devuelve fragmentos de transmisión (pensamientos, observaciones, respuestas) incluso cuando
streaming=False, para mostrar el proceso de razonamiento del agente.

**Argumentos:**

`question`: Pregunta o instrucción del usuario
`user`: Identificador del usuario
`state`: Diccionario de estado opcional para conversaciones con estado
`group`: Identificador de grupo opcional para contextos multiusuario
`history`: Historial de conversación opcional como lista de diccionarios de mensajes
`streaming`: Habilitar el modo de transmisión (predeterminado: False)
`**kwargs`: Parámetros adicionales pasados al servicio del agente

**Devuelve:** Iterator[StreamingChunk]: Flujo de pensamientos, observaciones y respuestas del agente

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent reasoning
for chunk in flow.agent(
    question="What is quantum computing?",
    user="trustgraph",
    streaming=True
):
    if isinstance(chunk, AgentThought):
        print(f"[Thinking] {chunk.content}")
    elif isinstance(chunk, AgentObservation):
        print(f"[Observation] {chunk.content}")
    elif isinstance(chunk, AgentAnswer):
        print(f"[Answer] {chunk.content}")
```

### `agent_explain(self, question: str, user: str, collection: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, **kwargs: Any) -> Iterator[trustgraph.api.types.StreamingChunk | trustgraph.api.types.ProvenanceEvent]`

Ejecutar una operación de agente con soporte de explicabilidad.

Transmite tanto los fragmentos de contenido (AgentThought, AgentObservation, AgentAnswer)
como los eventos de procedencia (ProvenanceEvent). Los eventos de procedencia contienen URIs
que se pueden recuperar utilizando ExplainabilityClient para obtener información detallada
sobre el proceso de razonamiento del agente.

El rastro del agente consiste en:
Sesión: La pregunta inicial y los metadatos de la sesión.
Iteraciones: Cada ciclo de pensamiento/acción/observación.
Conclusión: La respuesta final.

**Argumentos:**

`question`: Pregunta o instrucción del usuario.
`user`: Identificador del usuario.
`collection`: Identificador de la colección para el almacenamiento de la procedencia.
`state`: Diccionario de estado opcional para conversaciones con estado.
`group`: Identificador de grupo opcional para contextos multiusuario.
`history`: Historial de conversación opcional como una lista de diccionarios de mensajes.
`**kwargs`: Parámetros adicionales pasados al servicio del agente.
`Yields`: 
`Union[StreamingChunk, ProvenanceEvent]`: Fragmentos del agente y eventos de procedencia.

**Ejemplo:**

```python
from trustgraph.api import Api, ExplainabilityClient, ProvenanceEvent
from trustgraph.api import AgentThought, AgentObservation, AgentAnswer

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
for item in flow.agent_explain(
    question="What is the capital of France?",
    user="trustgraph",
    collection="default"
):
    if isinstance(item, AgentThought):
        print(f"[Thought] {item.content}")
    elif isinstance(item, AgentObservation):
        print(f"[Observation] {item.content}")
    elif isinstance(item, AgentAnswer):
        print(f"[Answer] {item.content}")
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.explain_id)

# Fetch session trace after completion
if provenance_ids:
    trace = explain_client.fetch_agent_trace(
        provenance_ids[0],  # Session URI is first
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="default"
    )
```

### `document_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Consultar fragmentos de documentos utilizando similitud semántica.

**Argumentos:**

`text`: Texto de consulta para la búsqueda semántica
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`limit`: Número máximo de resultados (por defecto: 10)
`**kwargs`: Parámetros adicionales pasados al servicio

**Retorna:** dict: Resultados de la consulta con los ID de los fragmentos de los documentos coincidentes

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "...", "score": 0.95}, ...]}
```

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Ejecutar una consulta RAG basada en documentos con transmisión opcional.

Utiliza incrustaciones vectoriales para encontrar fragmentos de documentos relevantes y luego genera
una respuesta utilizando un LLM. El modo de transmisión entrega resultados de forma incremental.

**Argumentos:**

`query`: Consulta en lenguaje natural
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`doc_limit`: Número máximo de fragmentos de documentos a recuperar (predeterminado: 10)
`streaming`: Habilitar el modo de transmisión (predeterminado: Falso)
`**kwargs`: Parámetros adicionales pasados al servicio

**Retorna:** Union[str, Iterator[str]]: Respuesta completa o flujo de fragmentos de texto

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming document RAG
for chunk in flow.document_rag(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5,
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `document_rag_explain(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

Ejecutar una consulta RAG basada en documentos con soporte para la explicabilidad.

Transmite tanto los fragmentos de contenido (RAGChunk) como los eventos de procedencia (ProvenanceEvent).
Los eventos de procedencia contienen URIs que se pueden recuperar utilizando ExplainabilityClient
para obtener información detallada sobre cómo se generó la respuesta.

El rastro RAG del documento consiste en:
Pregunta: La consulta del usuario
Exploración: Fragmentos recuperados de la tienda de documentos (chunk_count)
Síntesis: La respuesta generada

**Argumentos:**

`query`: Consulta en lenguaje natural
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`doc_limit`: Número máximo de fragmentos de documento a recuperar (por defecto: 10)
`**kwargs`: Parámetros adicionales pasados al servicio
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: Fragmentos de contenido y eventos de procedencia

**Ejemplo:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

for item in flow.document_rag_explain(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5
):
    if isinstance(item, RAGChunk):
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        # Fetch entity details
        entity = explain_client.fetch_entity(
            item.explain_id,
            graph=item.explain_graph,
            user="trustgraph",
            collection="research-papers"
        )
        print(f"Event: {entity}", file=sys.stderr)
```

### `embeddings(self, texts: list, **kwargs: Any) -> Dict[str, Any]`

Generar incrustaciones vectoriales para uno o más textos.

**Argumentos:**

`texts`: Lista de textos de entrada para incrustar.
`**kwargs`: Parámetros adicionales pasados al servicio.

**Retorna:** dict: Respuesta que contiene vectores (un conjunto por texto de entrada).

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Consultar entidades de un grafo de conocimiento utilizando similitud semántica.

**Argumentos:**

`text`: Texto de la consulta para la búsqueda semántica
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`limit`: Número máximo de resultados (por defecto: 10)
`**kwargs`: Parámetros adicionales pasados al servicio

**Retorna:** dict: Resultados de la consulta con entidades similares

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

results = flow.graph_embeddings_query(
    text="physicist who discovered radioactivity",
    user="trustgraph",
    collection="scientists",
    limit=5
)
```

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Ejecutar una consulta RAG basada en grafos con transmisión opcional.

Utiliza la estructura del grafo de conocimiento para encontrar el contexto relevante y luego genera
una respuesta utilizando un LLM. El modo de transmisión entrega los resultados de forma incremental.

**Argumentos:**

`query`: Consulta en lenguaje natural
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`max_subgraph_size`: Número máximo total de triples en el subgrafo (por defecto: 1000)
`max_subgraph_count`: Número máximo de subgrafos (por defecto: 5)
`max_entity_distance`: Profundidad máxima de recorrido (por defecto: 3)
`streaming`: Habilitar el modo de transmisión (por defecto: False)
`**kwargs`: Parámetros adicionales pasados al servicio

**Retorna:** Union[str, Iterator[str]]: Respuesta completa o flujo de fragmentos de texto

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming graph RAG
for chunk in flow.graph_rag(
    query="Tell me about Marie Curie",
    user="trustgraph",
    collection="scientists",
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `graph_rag_explain(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

Ejecutar consulta RAG basada en grafos con soporte de explicabilidad.

Transmite tanto fragmentos de contenido (RAGChunk) como eventos de procedencia (ProvenanceEvent).
Los eventos de procedencia contienen URIs que se pueden recuperar utilizando ExplainabilityClient
para obtener información detallada sobre cómo se generó la respuesta.

**Argumentos:**

`query`: Consulta en lenguaje natural
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`max_subgraph_size`: Número máximo total de triples en el subgrafo (predeterminado: 1000)
`max_subgraph_count`: Número máximo de subgrafos (predeterminado: 5)
`max_entity_distance`: Profundidad máxima de recorrido (predeterminado: 3)
`**kwargs`: Parámetros adicionales pasados al servicio
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: Fragmentos de contenido y eventos de procedencia

**Ejemplo:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
response_text = ""

for item in flow.graph_rag_explain(
    query="Tell me about Marie Curie",
    user="trustgraph",
    collection="scientists"
):
    if isinstance(item, RAGChunk):
        response_text += item.content
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.provenance_id)

# Fetch explainability details
for prov_id in provenance_ids:
    entity = explain_client.fetch_entity(
        prov_id,
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="scientists"
    )
    print(f"Entity: {entity}")
```

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]`

Ejecutar una herramienta de Protocolo de Contexto de Modelo (MCP).

**Argumentos:**

`name`: Nombre/identificador de la herramienta
`parameters`: Diccionario de parámetros de la herramienta
`**kwargs`: Parámetros adicionales pasados al servicio

**Retorna:** dict: Resultado de la ejecución de la herramienta

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Ejecutar una plantilla de prompt con transmisión opcional.

**Argumentos:**

`id`: Identificador de la plantilla de prompt.
`variables`: Diccionario de mapeos de nombres de variables a valores.
`streaming`: Habilitar el modo de transmisión (predeterminado: False).
`**kwargs`: Parámetros adicionales pasados al servicio.

**Retorna:** Union[str, Iterator[str]]: Respuesta completa o flujo de fragmentos de texto.

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming prompt execution
for chunk in flow.prompt(
    id="summarize-template",
    variables={"topic": "quantum computing", "length": "brief"},
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Consulta datos de filas utilizando la similitud semántica en campos indexados.

Encuentra filas cuyos valores de campos indexados son semánticamente similares a
el texto de entrada, utilizando incrustaciones vectoriales. Esto permite la coincidencia difusa/semántica
en datos estructurados.

**Argumentos:**

`text`: Texto de consulta para la búsqueda semántica
`schema_name`: Nombre del esquema para buscar
`user`: Identificador de usuario/espacio de claves (predeterminado: "trustgraph")
`collection`: Identificador de colección (predeterminado: "default")
`index_name`: Nombre de índice opcional para filtrar la búsqueda a un índice específico
`limit`: Número máximo de resultados (predeterminado: 10)
`**kwargs`: Parámetros adicionales pasados al servicio

**Retorna:** dict: Resultados de la consulta con coincidencias que contienen index_name, index_value, text y score

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict[str, Any] | None = None, operation_name: str | None = None, **kwargs: Any) -> Dict[str, Any]`

Ejecutar una consulta GraphQL contra filas estructuradas.

**Argumentos:**

`query`: Cadena de consulta GraphQL
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`variables`: Diccionario opcional de variables de consulta
`operation_name`: Nombre de operación opcional para documentos de múltiples operaciones
`**kwargs`: Parámetros adicionales pasados al servicio

**Retorna:** dict: Respuesta GraphQL con datos, errores y/o extensiones

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

query = '''
{
  scientists(limit: 10) {
    name
    field
    discoveries
  }
}
'''
result = flow.rows_query(
    query=query,
    user="trustgraph",
    collection="scientists"
)
```

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs) -> str | Iterator[str]`

Ejecutar la finalización de texto con transmisión opcional.

**Argumentos:**

`system`: Instrucción del sistema que define el comportamiento del asistente.
`prompt`: Instrucción/pregunta del usuario.
`streaming`: Habilitar el modo de transmisión (predeterminado: False).
`**kwargs`: Parámetros adicionales pasados al servicio.

**Retorna:** Union[str, Iterator[str]]: Respuesta completa o flujo de fragmentos de texto.

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Non-streaming
response = flow.text_completion(
    system="You are helpful",
    prompt="Explain quantum computing",
    streaming=False
)
print(response)

# Streaming
for chunk in flow.text_completion(
    system="You are helpful",
    prompt="Explain quantum computing",
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `triples_query(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, **kwargs: Any) -> List[Dict[str, Any]]`

Consultar triples del grafo de conocimiento utilizando la coincidencia de patrones.

**Argumentos:**

`s`: Filtro de sujeto - Cadena URI, diccionario de términos o None para comodín.
`p`: Filtro de predicado - Cadena URI, diccionario de términos o None para comodín.
`o`: Filtro de objeto - Cadena URI/literal, diccionario de términos o None para comodín.
`g`: Filtro de grafo con nombre - Cadena URI o None para todos los grafos.
`user`: Identificador de usuario/espacio de claves (opcional).
`collection`: Identificador de colección (opcional).
`limit`: Número máximo de resultados a devolver (por defecto: 100).
`**kwargs`: Parámetros adicionales pasados al servicio.

**Retorna:** List[Dict]: Lista de triples coincidentes en formato de cable.

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Find all triples about a specific subject
triples = flow.triples_query(
    s="http://example.org/person/marie-curie",
    user="trustgraph",
    collection="scientists"
)

# Query with named graph filter
triples = flow.triples_query(
    s="urn:trustgraph:session:abc123",
    g="urn:graph:retrieval",
    user="trustgraph",
    collection="default"
)
```

### `triples_query_stream(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, batch_size: int = 20, **kwargs: Any) -> Iterator[List[Dict[str, Any]]]`

Consultar triples del grafo de conocimiento con lotes de transmisión.

Produce lotes de triples a medida que llegan, reduciendo el tiempo para obtener el primer resultado
y la sobrecarga de memoria para conjuntos de resultados grandes.

**Argumentos:**

`s`: Filtro de sujeto - Cadena URI, diccionario de términos o None para comodín
`p`: Filtro de predicado - Cadena URI, diccionario de términos o None para comodín
`o`: Filtro de objeto - Cadena URI/literal, diccionario de términos o None para comodín
`g`: Filtro de grafo con nombre - Cadena URI o None para todos los grafos
`user`: Identificador de usuario/espacio de claves (opcional)
`collection`: Identificador de colección (opcional)
`limit`: Número máximo de resultados a devolver (por defecto: 100)
`batch_size`: Triples por lote (por defecto: 20)
`**kwargs`: Parámetros adicionales pasados al servicio
`Yields`: 
`List[Dict]`: Lotes de triples en formato de cable

**Ejemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

for batch in flow.triples_query_stream(
    user="trustgraph",
    collection="default"
):
    for triple in batch:
        print(triple["s"], triple["p"], triple["o"])
```


--

## `AsyncSocketClient`

```python
from trustgraph.api import AsyncSocketClient
```

Cliente WebSocket asíncrono

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None)`

Inicializar self. Consulte help(type(self)) para obtener la firma precisa.

### `aclose(self)`

Cerrar conexión WebSocket

### `flow(self, flow_id: str)`

Obtener la instancia de flujo asíncrono para operaciones de WebSocket


--

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

Flujo de WebSocket asíncrono.

### Métodos

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

Inicializar self. Consulte help(type(self)) para obtener la firma correcta.

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

Agente con transmisión opcional.

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

Documento RAG con transmisión opcional.

### `embeddings(self, texts: list, **kwargs)`

Generar incrustaciones de texto.

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

Consultar incrustaciones de grafos para búsqueda semántica.

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

RAG de grafos con transmisión opcional.

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

Ejecutar herramienta MCP.

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

Ejecutar prompt con transmisión opcional.

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

Consultar incrustaciones de filas para búsqueda semántica en datos estructurados.

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

Consulta GraphQL contra filas estructuradas.

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

Completar texto con transmisión opcional.

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

Consulta de patrones triples.


--

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

Construir un diccionario de términos en formato de cable a partir de un valor.

Reglas de detección automática (cuando term_type es None):
  Ya es un diccionario con la clave 't' -> devolver tal cual (ya es un Term)
  Comienza con http://, https://, urn: -> IRI
  Está encerrado entre < (por ejemplo, <http://...>) -> IRI (se eliminan los corchetes)
  Cualquier otra cosa -> literal

**Argumentos:**

`value`: El valor del término (cadena, diccionario o None).
`term_type`: Uno de 'iri', 'literal' o None para la detección automática.
`datatype`: Tipo de datos para objetos literales (por ejemplo, xsd:integer).
`language`: Etiqueta de idioma para objetos literales (por ejemplo, en).

**Devuelve:** dict: Diccionario de términos en formato de cable, o None si el valor es None.


--

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

Cliente para operaciones masivas sincrónicas para la importación/exportación.

Proporciona una transferencia de datos masiva eficiente a través de WebSocket para conjuntos de datos grandes.
Envuelve las operaciones asíncronas de WebSocket con generadores sincrónicos para facilitar su uso.

Nota: Para un soporte asíncrono real, utilice AsyncBulkClient en su lugar.

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicializa el cliente de operaciones masivas sincrónico.

**Argumentos:**

`url`: URL base para la API de TrustGraph (HTTP/HTTPS se convertirá a WS/WSS)
`timeout`: Tiempo de espera de WebSocket en segundos
`token`: Token de portador opcional para la autenticación

### `close(self) -> None`

Cierra las conexiones.

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Exporta masivamente las incrustaciones de documentos desde un flujo.

Descarga de forma eficiente todas las incrustaciones de fragmentos de documentos a través de la transmisión de WebSocket.

**Argumentos:**

`flow`: Identificador del flujo
`**kwargs`: Parámetros adicionales (reservados para uso futuro)

**Devuelve:** Iterator[Dict[str, Any]]: Flujo de diccionarios de incrustaciones

**Ejemplo:**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Exportación masiva de contextos de entidades desde un flujo.

Descarga de manera eficiente toda la información del contexto de la entidad a través de transmisión WebSocket.

**Argumentos:**

`flow`: Identificador del flujo.
`**kwargs`: Parámetros adicionales (reservados para uso futuro).

**Retorna:** Iterator[Dict[str, Any]]: Flujo de diccionarios de contexto.

**Ejemplo:**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Exportación masiva de incrustaciones de grafos desde un flujo.

Descarga de manera eficiente todas las incrustaciones de entidades de grafos a través de transmisión WebSocket.

**Argumentos:**

`flow`: Identificador del flujo.
`**kwargs`: Parámetros adicionales (reservados para uso futuro).

**Retorna:** Iterator[Dict[str, Any]]: Flujo de diccionarios de incrustaciones.

**Ejemplo:**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

Exportación masiva de triples RDF desde un flujo.

Descarga de manera eficiente todos los triples a través de transmisión WebSocket.

**Argumentos:**

`flow`: Identificador del flujo.
`**kwargs`: Parámetros adicionales (reservados para uso futuro).

**Retorna:** Iterator[Triple]: Flujo de objetos Triple.

**Ejemplo:**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Importación masiva de incrustaciones de documentos en un flujo.

Carga de manera eficiente las incrustaciones de fragmentos de documentos a través de transmisión WebSocket
para su uso en consultas RAG de documentos.

**Argumentos:**

`flow`: Identificador del flujo.
`embeddings`: Iterador que produce diccionarios de incrustaciones.
`**kwargs`: Parámetros adicionales (reservados para uso futuro).

**Ejemplo:**

```python
bulk = api.bulk()

# Generate document embeddings to import
def doc_embedding_generator():
    yield {"chunk_id": "doc1/p0/c0", "embedding": [0.1, 0.2, ...]}
    yield {"chunk_id": "doc1/p0/c1", "embedding": [0.3, 0.4, ...]}
    # ... more embeddings

bulk.import_document_embeddings(
    flow="default",
    embeddings=doc_embedding_generator()
)
```

### `import_entity_contexts(self, flow: str, contexts: Iterator[Dict[str, Any]], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

Importación masiva de contextos de entidades en un flujo.

Carga de manera eficiente la información del contexto de la entidad a través de transmisión WebSocket.
Los contextos de entidades proporcionan un contexto textual adicional sobre las entidades del gráfico
para mejorar el rendimiento de RAG.

**Argumentos:**

`flow`: Identificador del flujo.
`contexts`: Iterador que devuelve diccionarios de contexto.
`metadata`: Diccionario de metadatos con id, metadatos, usuario, colección.
`batch_size`: Número de contextos por lote (por defecto 100).
`**kwargs`: Parámetros adicionales (reservados para uso futuro).

**Ejemplo:**

```python
bulk = api.bulk()

# Generate entity contexts to import
def context_generator():
    yield {"entity": {"v": "entity1", "e": True}, "context": "Description..."}
    yield {"entity": {"v": "entity2", "e": True}, "context": "Description..."}
    # ... more contexts

bulk.import_entity_contexts(
    flow="default",
    contexts=context_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```

### `import_graph_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Importación masiva de incrustaciones de grafos en un flujo.

Carga de manera eficiente las incrustaciones de entidades de grafos a través de transmisión WebSocket.

**Argumentos:**

`flow`: Identificador del flujo.
`embeddings`: Iterador que produce diccionarios de incrustaciones.
`**kwargs`: Parámetros adicionales (reservados para uso futuro).

**Ejemplo:**

```python
bulk = api.bulk()

# Generate embeddings to import
def embedding_generator():
    yield {"entity": "entity1", "embedding": [0.1, 0.2, ...]}
    yield {"entity": "entity2", "embedding": [0.3, 0.4, ...]}
    # ... more embeddings

bulk.import_graph_embeddings(
    flow="default",
    embeddings=embedding_generator()
)
```

### `import_rows(self, flow: str, rows: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Importación masiva de filas estructuradas en un flujo.

Carga de manera eficiente datos estructurados a través de transmisión WebSocket
para su uso en consultas GraphQL.

**Argumentos:**

`flow`: Identificador del flujo
`rows`: Iterador que produce diccionarios de filas
`**kwargs`: Parámetros adicionales (reservados para uso futuro)

**Ejemplo:**

```python
bulk = api.bulk()

# Generate rows to import
def row_generator():
    yield {"id": "row1", "name": "Row 1", "value": 100}
    yield {"id": "row2", "name": "Row 2", "value": 200}
    # ... more rows

bulk.import_rows(
    flow="default",
    rows=row_generator()
)
```

### `import_triples(self, flow: str, triples: Iterator[trustgraph.api.types.Triple], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

Importación masiva de triples RDF en un flujo.

Carga de manera eficiente un gran número de triples a través de transmisión WebSocket.

**Argumentos:**

`flow`: Identificador del flujo.
`triples`: Iterador que produce objetos Triple.
`metadata`: Diccionario de metadatos con id, metadatos, usuario, colección.
`batch_size`: Número de triples por lote (por defecto 100).
`**kwargs`: Parámetros adicionales (reservados para uso futuro).

**Ejemplo:**

```python
from trustgraph.api import Triple

bulk = api.bulk()

# Generate triples to import
def triple_generator():
    yield Triple(s="subj1", p="pred", o="obj1")
    yield Triple(s="subj2", p="pred", o="obj2")
    # ... more triples

# Import triples
bulk.import_triples(
    flow="default",
    triples=triple_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```


--

## `AsyncBulkClient`

```python
from trustgraph.api import AsyncBulkClient
```

Cliente para operaciones masivas asíncronas.

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicializar self. Consulte help(type(self)) para obtener la firma precisa.

### `aclose(self) -> None`

Cerrar conexiones.

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Exportación masiva de incrustaciones de documentos a través de WebSocket.

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Exportación masiva de contextos de entidades a través de WebSocket.

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Exportación masiva de incrustaciones de grafos a través de WebSocket.

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

Exportación masiva de triples a través de WebSocket.

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Importación masiva de incrustaciones de documentos a través de WebSocket.

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Importación masiva de contextos de entidades a través de WebSocket.

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Importación masiva de incrustaciones de grafos a través de WebSocket.

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Importación masiva de filas a través de WebSocket.

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

Importación masiva de triples a través de WebSocket.


--

## `Metrics`

```python
from trustgraph.api import Metrics
```

Cliente de métricas sincrónicas

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicializar self. Consulte help(type(self)) para obtener la firma precisa.

### `get(self) -> str`

Obtener métricas de Prometheus como texto


--

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

Cliente de métricas asíncronas

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicializar self. Consulte help(type(self)) para obtener la firma correcta.

### `aclose(self) -> None`

Cerrar conexiones

### `get(self) -> str`

Obtener métricas de Prometheus como texto


--

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

Cliente para obtener entidades de explicabilidad con manejo de consistencia eventual.

Utiliza la detección de quiescencia: obtener, esperar, obtener de nuevo, comparar.
Si los resultados son los mismos, los datos son estables.

### Métodos

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

Inicializar el cliente de explicabilidad.

**Argumentos:**

`flow_instance`: Una instancia de SocketFlowInstance para consultar triples.
`retry_delay`: Retraso entre reintentos en segundos (por defecto: 0.2).
`max_retries`: Número máximo de intentos de reintento (por defecto: 10).

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

Detectar si una sesión es de tipo GraphRAG o Agent.

**Argumentos:**

`session_uri`: La URI de la sesión/pregunta.
`graph`: Grafo nombrado.
`user`: Identificador de usuario/espacio de claves.
`collection`: Identificador de colección.

**Retorna:** "graphrag" o "agent".

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Obtener el rastro completo del Agent a partir de una URI de sesión.

Sigue la cadena de procedencia: Pregunta -> Análisis(es) -> Conclusión.

**Argumentos:**

`session_uri`: La URI de la sesión/pregunta del agente.
`graph`: Grafo nombrado (por defecto: urn:graph:retrieval).
`user`: Identificador de usuario/espacio de claves.
`collection`: Identificador de colección.
`api`: Instancia de la API de TrustGraph para el acceso al bibliotecario (opcional).
`max_content`: Longitud máxima del contenido para la conclusión.

**Retorna:** Diccionario con la pregunta, las iteraciones (lista de Análisis) y las entidades de conclusión.

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Obtener el rastro completo de DocumentRAG a partir de una URI de pregunta.

Sigue la cadena de procedencia:
    Pregunta -> Fundamentación -> Exploración -> Síntesis.

**Argumentos:**

`question_uri`: La URI de la entidad de pregunta.
`graph`: Grafo nombrado (por defecto: urn:graph:retrieval).
`user`: Identificador de usuario/espacio de claves.
`collection`: Identificador de colección.
`api`: Instancia de la API de TrustGraph para el acceso al bibliotecario (opcional).
`max_content`: Longitud máxima del contenido para la síntesis.

**Retorna:** Diccionario con la pregunta, la fundamentación, la exploración y las entidades de síntesis.

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

Obtener contenido del bibliotecario por URI de documento.

**Argumentos:**

`document_uri`: La URI del documento en el bibliotecario.
`api`: Instancia de la API de TrustGraph para el acceso al bibliotecario.
`user`: Identificador de usuario para el bibliotecario.
`max_content`: Longitud máxima del contenido a retornar.

**Retorna:** El contenido del documento como una cadena.

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

Obtener una entidad de selección de borde (utilizada por Focus).

**Argumentos:**

`uri`: La URI de la selección de borde.
`graph`: Grafo nombrado a consultar.
`user`: Identificador de usuario/espacio de claves.
`collection`: Identificador de colección.

**Retorna:** EdgeSelection o None si no se encuentra.

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

Obtener una entidad de explicabilidad por URI con manejo de consistencia eventual.

Utiliza la detección de quiescencia:
1. Obtener triples para el URI
2. Si no hay resultados, reintentar
3. Si hay resultados, esperar y obtener de nuevo
4. Si los resultados son los mismos, los datos son estables: analizar y devolver
5. Si los resultados son diferentes, los datos aún se están escribiendo: reintentar

**Argumentos:**

`uri`: El URI de la entidad a obtener
`graph`: Grafo con nombre para consultar (por ejemplo, "urn:graph:retrieval")
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección

**Devuelve:** Subclase ExplainEntity o None si no se encuentra

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

Obtener una entidad Focus y todas sus selecciones de aristas.

**Argumentos:**

`uri`: El URI de la entidad Focus
`graph`: Grafo con nombre para consultar
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección

**Devuelve:** Focus con edge_selections pobladas, o None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Obtener el rastro completo de GraphRAG a partir de un URI de pregunta.

Sigue la cadena de procedencia: Pregunta -> Grounding -> Exploración -> Focus -> Síntesis

**Argumentos:**

`question_uri`: El URI de la entidad de pregunta
`graph`: Grafo (por defecto: urn:graph:retrieval)
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`api`: Instancia de la API TrustGraph para el acceso de bibliotecario (opcional)
`max_content`: Longitud máxima del contenido para la síntesis

**Devuelve:** Diccionario con las entidades de pregunta, grounding, exploración, focus y síntesis

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

Listar todas las sesiones de explicabilidad (preguntas) en una colección.

**Argumentos:**

`graph`: Grafo (por defecto: urn:graph:retrieval)
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección
`limit`: Número máximo de sesiones a devolver

**Devuelve:** Lista de entidades de Pregunta ordenadas por marca de tiempo (más reciente primero)

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

Resolver las etiquetas para todos los componentes de una tripleta de arista.

**Argumentos:**

`edge`: Diccionario con claves "s", "p" y "o"
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección

**Devuelve:** Tupla de (s_label, p_label, o_label)

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

Resolver rdfs:label para un URI, con almacenamiento en caché.

**Argumentos:**

`uri`: El URI para obtener la etiqueta
`user`: Identificador de usuario/espacio de claves
`collection`: Identificador de colección

**Devuelve:** La etiqueta si se encuentra, de lo contrario, el propio URI


--

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

Clase base para entidades de explicabilidad.

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '') -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `Question`

```python
from trustgraph.api import Question
```

Entidad de pregunta: la consulta del usuario que inició la sesión.

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`query`: <class 'str'>
`timestamp`: <class 'str'>
`question_type`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

Inicializar self. Consulte help(type(self)) para obtener la firma precisa.


--

## `Exploration`

```python
from trustgraph.api import Exploration
```

Entidad de exploración: bordes/fragmentos recuperados del almacén de conocimiento.

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`edge_count`: <class 'int'>
`chunk_count`: <class 'int'>
`entities`: typing.List[str]

### Métodos

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `Focus`

```python
from trustgraph.api import Focus
```

Entidad de enfoque: bordes seleccionados con razonamiento LLM (solo GraphRAG).

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`selected_edge_uris`: typing.List[str]
`edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### Métodos

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

Inicializa self. Consulta help(type(self)) para obtener la firma precisa.


--

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

Entidad de síntesis: la respuesta final.

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Inicializa self. Consulta help(type(self)) para obtener la firma precisa.


--

## `Analysis`

```python
from trustgraph.api import Analysis
```

Entidad de análisis: un ciclo de pensar/actuar/observar (solo para el Agente).

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`action`: <class 'str'>
`arguments`: <class 'str'>
`thought`: <class 'str'>
`observation`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma correcta.


--

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

Conclusión de la entidad - respuesta final (solo para el agente).

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Inicializa self. Consulta help(type(self)) para obtener la firma precisa.


--

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

Un borde seleccionado con razonamiento del paso GraphRAG Focus.

**Campos:**

`uri`: <class 'str'>
`edge`: typing.Dict[str, str] | None
`reasoning`: <class 'str'>

### Métodos

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

Inicializa self. Consulta help(type(self)) para obtener la firma precisa.


--

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

Convierte las triples en formato de cable a tuplas (s, p, o).


--

### `extract_term_value(term: Dict[str, Any]) -> Any`

Extrae el valor de un diccionario de términos en formato de cable.


--

## `Triple`

```python
from trustgraph.api import Triple
```

Triple RDF que representa una declaración de un grafo de conocimiento.

**Campos:**

`s`: <class 'str'>
`p`: <class 'str'>
`o`: <class 'str'>

### Métodos

### `__init__(self, s: str, p: str, o: str) -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `Uri`

```python
from trustgraph.api import Uri
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Crea un nuevo objeto de cadena a partir del objeto dado. Si se especifica encoding o
errors, entonces el objeto debe exponer un búfer de datos
que se decodificará utilizando la codificación y el controlador de errores especificados.
De lo contrario, devuelve el resultado de object.__str__() (si está definido)
o repr(object).
encoding tiene como valor predeterminado 'utf-8'.
errors tiene como valor predeterminado 'strict'.

### Métodos

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `Literal`

```python
from trustgraph.api import Literal
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Crea un nuevo objeto de cadena a partir del objeto dado. Si se especifica encoding o
errors, entonces el objeto debe exponer un búfer de datos
que se decodificará utilizando la codificación y el controlador de errores especificados.
De lo contrario, devuelve el resultado de object.__str__() (si está definido)
o repr(object).
encoding tiene como valor predeterminado 'utf-8'.
errors tiene como valor predeterminado 'strict'.

### Métodos

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

Identificador de clave de configuración.

**Campos:**

`type`: <class 'str'>
`key`: <class 'str'>

### Métodos

### `__init__(self, type: str, key: str) -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

Par clave-valor de configuración.

**Campos:**

`type`: <class 'str'>
`key`: <class 'str'>
`value`: <class 'str'>

### Métodos

### `__init__(self, type: str, key: str, value: str) -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

Metadatos para un documento en la biblioteca.

**Atributos:**

`parent_id: Parent document ID for child documents (empty for top`: level docs)

**Campos:**

`id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`kind`: <class 'str'>
`title`: <class 'str'>
`comments`: <class 'str'>
`metadata`: typing.List[trustgraph.api.types.Triple]
`user`: <class 'str'>
`tags`: typing.List[str]
`parent_id`: <class 'str'>
`document_type`: <class 'str'>

### Métodos

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

Inicializar self. Consulte help(type(self)) para obtener la firma correcta.


--

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

Metadatos para un trabajo de procesamiento de documentos activo.

**Campos:**

`id`: <class 'str'>
`document_id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`flow`: <class 'str'>
`user`: <class 'str'>
`collection`: <class 'str'>
`tags`: typing.List[str]

### Métodos

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma correcta.


--

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

Metadatos para una colección de datos.

Las colecciones proporcionan un agrupamiento lógico y un aislamiento para documentos y
datos de grafos de conocimiento.

**Atributos:**

`name: Human`: nombre de colección legible

**Campos:**

`user`: <class 'str'>
`collection`: <class 'str'>
`name`: <class 'str'>
`description`: <class 'str'>
`tags`: typing.List[str]

### Métodos

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

Inicializar self. Consulte help(type(self)) para obtener la firma precisa.


--

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

Clase base para fragmentos de respuesta de transmisión.

Se utiliza para operaciones de transmisión basadas en WebSocket, donde las respuestas se entregan
de forma incremental a medida que se generan.

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>

### Métodos

### `__init__(self, content: str, end_of_message: bool = False) -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

Fragmento del razonamiento/proceso de pensamiento del agente.

Representa el razonamiento interno o los pasos de planificación del agente durante la ejecución.
Estos fragmentos muestran cómo el agente está pensando sobre el problema.

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Métodos

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

Fragmento de observación de la ejecución de la herramienta del agente.

Representa el resultado u observación de la ejecución de una herramienta o acción.
Estos fragmentos muestran lo que el agente aprendió al usar herramientas.

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Métodos

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

Fragmento de la respuesta final del agente.

Representa la respuesta final del agente al usuario después de completar
su razonamiento y el uso de herramientas.

**Atributos:**

`chunk_type: Always "final`: answer"

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_dialog`: <class 'bool'>

### Métodos

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

Fragmento de transmisión RAG (Generación Aumentada por Recuperación).

Utilizado para transmitir respuestas de RAG de grafos, RAG de documentos, finalización de texto,
y otros servicios generativos.

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_stream`: <class 'bool'>
`error`: typing.Dict[str, str] | None

### Métodos

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

Inicializa self. Consulte help(type(self)) para obtener la firma precisa.


--

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

Evento de procedencia para la explicabilidad.

Emitido durante las consultas de GraphRAG cuando el modo de explicabilidad está habilitado.
Cada evento representa un nodo de procedencia creado durante el procesamiento de la consulta.

**Campos:**

`explain_id`: <class 'str'>
`explain_graph`: <class 'str'>
`event_type`: <class 'str'>

### Métodos

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

Inicializar self. Consulte help(type(self)) para obtener la firma precisa.


--

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

Se genera cuando ocurren errores en el protocolo WebSocket.


--

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

Clase base para todos los errores del servicio TrustGraph.


--

## `AgentError`

```python
from trustgraph.api import AgentError
```

Error en el servicio del agente


--

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

Error del servicio de configuración


--

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

Error de recuperación de documentos RAG.


--

## `FlowError`

```python
from trustgraph.api import FlowError
```

Error de gestión de flujo


--

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

Error de la API Gateway


--

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

Error de recuperación de Graph RAG.


--

## `LLMError`

```python
from trustgraph.api import LLMError
```

Error del servicio de modelo de lenguaje grande.


--

## `LoadError`

```python
from trustgraph.api import LoadError
```

Error de carga de datos


--

## `LookupError`

```python
from trustgraph.api import LookupError
```

Error de búsqueda/consulta


--

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

Error en el servicio de consulta de procesamiento del lenguaje natural.


--

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

Error en el servicio de consulta de filas.


--

## `RequestError`

```python
from trustgraph.api import RequestError
```

Error en el procesamiento de la solicitud.


--

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

Error en el servicio de consulta estructurada.


--

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

Error inesperado/desconocido


--

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

Clase base para todos los errores del servicio TrustGraph.


--
