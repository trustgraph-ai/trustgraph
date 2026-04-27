---
layout: default
title: "Справочник API TrustGraph на Python"
parent: "Russian (Beta)"
---

# Справочник API TrustGraph на Python

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Установка

```bash
pip install trustgraph
```

## Быстрый старт

Все классы и типы импортируются из пакета `trustgraph.api`:

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

## Оглавление

### Основное

[Api](#api)

### Клиенты потоков

[Flow](#flow)
[FlowInstance](#flowinstance)
[AsyncFlow](#asyncflow)
[AsyncFlowInstance](#asyncflowinstance)

### Клиенты WebSocket

[SocketClient](#socketclient)
[SocketFlowInstance](#socketflowinstance)
[AsyncSocketClient](#asyncsocketclient)
[AsyncSocketFlowInstance](#asyncsocketflowinstance)

### Операции пакетной обработки

[BulkClient](#bulkclient)
[AsyncBulkClient](#asyncbulkclient)

### Метрики

[Metrics](#metrics)
[AsyncMetrics](#asyncmetrics)

### Типы данных

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

### Исключения

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

Основной клиент API TrustGraph для синхронных и асинхронных операций.

Этот класс предоставляет доступ ко всем сервисам TrustGraph, включая управление потоками,
операции с графом знаний, обработку документов, запросы RAG и многое другое. Он поддерживает
как коммуникационные модели на основе REST, так и на основе WebSocket.

Клиент может использоваться как менеджер контекста для автоматической очистки ресурсов:
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### Методы

### `__aenter__(self)`

Войдите в асинхронный контекстный менеджер.

### `__aexit__(self, *args)`

Выйдите из асинхронного контекстного менеджера и закройте соединения.

### `__enter__(self)`

Войдите в синхронный контекстный менеджер.

### `__exit__(self, *args)`

Выйдите из синхронного контекстного менеджера и закройте соединения.

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

Инициализируйте клиент API TrustGraph.

**Аргументы:**

`url`: Базовый URL для API TrustGraph (по умолчанию: "http://localhost:8088/"")
`timeout`: Время ожидания запроса в секундах (по умолчанию: 60)
`token`: Необязательный токен для аутентификации

**Пример:**

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

Закройте все асинхронные клиентские соединения.

Этот метод закрывает асинхронные WebSocket-соединения, пакетные операции и потоковые соединения.
Он автоматически вызывается при выходе из асинхронного контекстного менеджера.

**Пример:**

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

Получите клиент для асинхронных пакетных операций.

Предоставляет пакетные операции импорта/экспорта в стиле async/await через WebSocket
для эффективной обработки больших наборов данных.

**Возвращает:** AsyncBulkClient: Асинхронный клиент для пакетных операций.

**Пример:**

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

Получите асинхронный клиент потоковой передачи на основе REST.

Предоставляет доступ к операциям потоковой передачи в стиле async/await. Это предпочтительно
для асинхронных приложений и фреймворков Python (FastAPI, aiohttp и т.д.).

**Возвращает:** AsyncFlow: Асинхронный клиент потоковой передачи

**Пример:**

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

Получите асинхронного клиента для сбора метрик.

Предоставляет доступ к метрикам Prometheus в стиле async/await.

**Возвращает:** AsyncMetrics: Асинхронный клиент для сбора метрик.

**Пример:**

```python
async_metrics = api.async_metrics()
prometheus_text = await async_metrics.get()
print(prometheus_text)
```

### `async_socket(self)`

Получите асинхронный WebSocket-клиент для операций потоковой передачи.

Предоставляет доступ к WebSocket в стиле async/await с поддержкой потоковой передачи.
Это предпочтительный метод для асинхронной потоковой передачи в Python.

**Возвращает:** AsyncSocketClient: Асинхронный WebSocket-клиент

**Пример:**

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

Получите клиент для синхронных пакетных операций импорта/экспорта.

Пакетные операции позволяют эффективно передавать большие наборы данных через соединения WebSocket,
включая тройки, вложения, контексты сущностей и объекты.

**Возвращает:** BulkClient: Клиент для синхронных пакетных операций.

**Пример:**

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

Закройте все синхронные клиентские соединения.

Этот метод закрывает соединения WebSocket и пакетных операций.
Он автоматически вызывается при выходе из контекстного менеджера.

**Пример:**

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

Получите клиент Collection для управления наборами данных.

Коллекции организуют документы и данные графа знаний в
логические группы для изоляции и контроля доступа.

**Возвращает:** Collection: Клиент для управления коллекциями.

**Пример:**

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

Получите клиент Config для управления настройками конфигурации.

**Возвращает:** Config: Клиент для управления конфигурацией.

**Пример:**

```python
config = api.config()

# Get configuration values
values = config.get([ConfigKey(type="llm", key="model")])

# Set configuration
config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
```

### `flow(self)`

Получите клиент Flow для управления и взаимодействия с потоками.

Потоки являются основными единицами выполнения в TrustGraph, предоставляя доступ к
сервисам, таким как агенты, запросы RAG, встраивания и обработка документов.

**Возвращает:** Flow: Клиент для управления потоками.

**Пример:**

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

Получите клиент Knowledge для управления ядрами графов знаний.

**Возвращает:** Клиент Knowledge для управления графами знаний.

**Пример:**

```python
knowledge = api.knowledge()

# List available KG cores
cores = knowledge.list_kg_cores(user="trustgraph")

# Load a KG core
knowledge.load_kg_core(id="core-123", user="trustgraph")
```

### `library(self)`

Получите клиент библиотеки для управления документами.

Библиотека предоставляет хранение документов, управление метаданными и
координацию рабочих процессов.

**Возвращает:** Library: Клиент для управления библиотекой документов

**Пример:**

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

Получите синхронный клиент для сбора метрик для мониторинга.

Получает метрики в формате Prometheus из сервиса TrustGraph
для мониторинга и обеспечения наблюдаемости.

**Возвращает:** Метрики: Синхронный клиент для сбора метрик.

**Пример:**

```python
metrics = api.metrics()
prometheus_text = metrics.get()
print(prometheus_text)
```

### `request(self, path, request)`

Выполнить запрос REST API на низком уровне.

Этот метод предназначен в основном для внутреннего использования, но может использоваться для прямого
доступа к API, когда это необходимо.

**Аргументы:**

`path`: Путь к API (относительно базового URL)
`request`: Текстовые данные запроса в виде словаря

**Возвращает:** dict: Объект ответа

**Вызывает исключения:**

`ProtocolException`: Если код состояния ответа не равен 200 или ответ не является JSON
`ApplicationException`: Если ответ содержит ошибку

**Пример:**

```python
response = api.request("flow", {
    "operation": "list-flows"
})
```

### `socket(self)`

Получите синхронного клиента WebSocket для операций потоковой передачи.

Соединения WebSocket обеспечивают поддержку потоковой передачи для ответов в режиме реального времени
от агентов, запросов RAG и завершения текста. Этот метод возвращает
синхронную обертку вокруг протокола WebSocket.

**Возвращает:** SocketClient: Синхронный клиент WebSocket

**Пример:**

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

Клиент для управления потоками, предназначенный для операций с шаблонами и экземплярами потоков.

Этот класс предоставляет методы для управления шаблонами потоков и
экземплярами потоков (запущенными потоками). Шаблоны определяют структуру и
параметры потоков, в то время как экземпляры представляют активные потоки, которые могут
выполнять сервисы.

### Методы

### `__init__(self, api)`

Инициализация клиента потоков.

**Аргументы:**

`api`: Родительский экземпляр API для выполнения запросов.

### `delete_blueprint(self, blueprint_name)`

Удаление шаблона потока.

**Аргументы:**

`blueprint_name`: Имя шаблона, который необходимо удалить.

**Пример:**

```python
api.flow().delete_blueprint("old-blueprint")
```

### `get(self, id)`

Получить определение экземпляра активного процесса.

**Аргументы:**

`id`: Идентификатор экземпляра процесса

**Возвращает:** dict: Определение экземпляра процесса

**Пример:**

```python
flow_def = api.flow().get("default")
print(flow_def)
```

### `get_blueprint(self, blueprint_name)`

Получить определение схемы по имени.

**Аргументы:**

`blueprint_name`: Имя схемы, которую необходимо получить.

**Возвращает:** dict: Определение схемы в виде словаря.

**Пример:**

```python
blueprint = api.flow().get_blueprint("default")
print(blueprint)  # Blueprint configuration
```

### `id(self, id='default')`

Получение объекта FlowInstance для выполнения операций над определенным потоком.

**Аргументы:**

`id`: Идентификатор потока (по умолчанию: "default")

**Возвращает:** FlowInstance: Объект Flow для операций сервиса.

**Пример:**

```python
flow = api.flow().id("my-flow")
response = flow.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `list(self)`

Перечислить все активные экземпляры потоков.

**Возвращает:** list[str]: Список идентификаторов экземпляров потоков.

**Пример:**

```python
flows = api.flow().list()
print(flows)  # ['default', 'flow-1', 'flow-2', ...]
```

### `list_blueprints(self)`

Перечислить все доступные шаблоны потоков.

**Возвращает:** list[str]: Список имен шаблонов.

**Пример:**

```python
blueprints = api.flow().list_blueprints()
print(blueprints)  # ['default', 'custom-flow', ...]
```

### `put_blueprint(self, blueprint_name, definition)`

Создать или обновить шаблон потока.

**Аргументы:**

`blueprint_name`: Имя для шаблона
`definition`: Словарь определения шаблона

**Пример:**

```python
definition = {
    "services": ["text-completion", "graph-rag"],
    "parameters": {"model": "gpt-4"}
}
api.flow().put_blueprint("my-blueprint", definition)
```

### `request(self, path=None, request=None)`

Отправьте API-запрос в рамках одного потока.

**Аргументы:**

`path`: Необязательный суффикс пути для конечных точек потока.
`request`: Словарь, содержащий полезную нагрузку запроса.

**Возвращает:** dict: Объект ответа.

**Вызывает исключение:**

`RuntimeError`: Если параметр запроса не указан.

### `start(self, blueprint_name, id, description, parameters=None)`

Запустите новый экземпляр потока из шаблона.

**Аргументы:**

`blueprint_name`: Имя шаблона для создания экземпляра.
`id`: Уникальный идентификатор экземпляра потока.
`description`: Описание, понятное человеку.
`parameters`: Необязательный словарь параметров.

**Пример:**

```python
api.flow().start(
    blueprint_name="default",
    id="my-flow",
    description="My custom flow",
    parameters={"model": "gpt-4"}
)
```

### `stop(self, id)`

Остановить запущенный экземпляр потока.

**Аргументы:**

`id`: Идентификатор экземпляра потока, который необходимо остановить.

**Пример:**

```python
api.flow().stop("my-flow")
```


--

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

Клиент экземпляра потока для выполнения сервисов в определенном потоке.

Этот класс предоставляет доступ ко всем сервисам TrustGraph, включая:
Завершение текста и создание векторных представлений
Операции агентов с управлением состоянием
Запросы RAG к графам и документам
Операции с графами знаний (тройки, объекты)
Загрузка и обработка документов
Преобразование естественного языка в запрос GraphQL
Анализ структурированных данных и обнаружение схемы
Выполнение инструмента MCP
Шаблонизация запросов

Сервисы доступны через работающий экземпляр потока, идентифицированный по ID.

### Методы

### `__init__(self, api, id)`

Инициализация FlowInstance.

**Аргументы:**

`api`: Родительский клиент потока
`id`: Идентификатор экземпляра потока

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

Выполнение операции агента с возможностями рассуждения и использования инструментов.

Агенты могут выполнять многоступенчатое рассуждение, использовать инструменты и поддерживать
состояние разговора в течение взаимодействий. Это синхронная версия без потоковой передачи.

**Аргументы:**

`question`: Вопрос или инструкция пользователя
`user`: Идентификатор пользователя (по умолчанию: "trustgraph")
`state`: Необязательный словарь состояния для разговоров с состоянием
`group`: Необязательный идентификатор группы для многопользовательских контекстов
`history`: Необязательная история разговора в виде списка словарей сообщений

**Возвращает:** str: Окончательный ответ агента

**Пример:**

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

Определить тип данных для образца структурированных данных.

**Аргументы:**

`sample`: Образец данных для анализа (текстовое содержимое)

**Возвращает:** словарь с информацией о типе, уверенности и необязательных метаданных.

### `diagnose_data(self, sample, schema_name=None, options=None)`

Выполнить комплексную диагностику данных: определить тип и сгенерировать описание.

**Аргументы:**

`sample`: Образец данных для анализа (текстовое содержимое)
`schema_name`: Необязательное имя целевой схемы для генерации описания.
`options`: Необязательные параметры (например, разделитель для CSV).

**Возвращает:** словарь с информацией о типе, уверенности, описании и метаданных.

### `document_embeddings_query(self, text, user, collection, limit=10)`

Запрос фрагментов документов с использованием семантического сходства.

Находит фрагменты документов, содержимое которых семантически похоже на
входной текст, используя векторные представления.

**Аргументы:**

`text`: Текст запроса для семантического поиска.
`user`: Идентификатор пользователя/пространства.
`collection`: Идентификатор коллекции.
`limit`: Максимальное количество результатов (по умолчанию: 10).

**Возвращает:** словарь: Результаты запроса с фрагментами, содержащими chunk_id и score.

**Пример:**

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

Выполнение запроса Retrieval-Augmented Generation (RAG), основанного на документах.

RAG на основе документов использует векторные представления для поиска соответствующих фрагментов документов,
а затем генерирует ответ с использованием LLM, используя эти фрагменты в качестве контекста.

**Аргументы:**

`query`: Запрос на естественном языке
`user`: Идентификатор пользователя/пространства (по умолчанию: "trustgraph")
`collection`: Идентификатор коллекции (по умолчанию: "default")
`doc_limit`: Максимальное количество фрагментов документов для извлечения (по умолчанию: 10)

**Возвращает:** str: Сгенерированный ответ, включающий контекст документа

**Пример:**

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

Генерирует векторные представления для одного или нескольких текстов.

Преобразует тексты в плотные векторные представления, подходящие для семантического
поиска и сравнения схожести.

**Аргументы:**

`texts`: Список входных текстов для создания векторных представлений.

**Возвращает:** list[list[list[float]]]: Векторные представления, один набор для каждого входного текста.

**Пример:**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

Создать описание для сопоставления структурированных данных с определенной схемой.

**Аргументы:**

`sample`: Пример данных для анализа (текстовое содержимое)
`data_type`: Тип данных (csv, json, xml)
`schema_name`: Имя целевой схемы для создания описания
`options`: Необязательные параметры (например, разделитель для CSV)

**Возвращает:** словарь с описанием и метаданными

### `graph_embeddings_query(self, text, user, collection, limit=10)`

Запрос сущностей графа знаний с использованием семантического сходства.

Находит сущности в графе знаний, описания которых семантически
схожи с входным текстом, используя векторные представления.

**Аргументы:**

`text`: Текст запроса для семантического поиска
`user`: Идентификатор пользователя/пространства ключей
`collection`: Идентификатор коллекции
`limit`: Максимальное количество результатов (по умолчанию: 10)

**Возвращает:** словарь: Результаты запроса с похожими сущностями

**Пример:**

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

Выполнение запроса на основе графов для генерации ответов с использованием извлеченной информации (RAG).

Graph RAG использует структуру графа знаний для поиска релевантного контекста путем
обхода связей между сущностями, а затем генерирует ответ с использованием большой языковой модели (LLM).

**Аргументы:**

`query`: Запрос на естественном языке
`user`: Идентификатор пользователя/пространства (по умолчанию: "trustgraph")
`collection`: Идентификатор коллекции (по умолчанию: "default")
`entity_limit`: Максимальное количество сущностей для извлечения (по умолчанию: 50)
`triple_limit`: Максимальное количество троек на сущность (по умолчанию: 30)
`max_subgraph_size`: Максимальное общее количество троек в подграфе (по умолчанию: 150)
`max_path_length`: Максимальная глубина обхода (по умолчанию: 2)

**Возвращает:** str: Сгенерированный ответ, включающий контекст графа

**Пример:**

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

Загрузка двоичного документа для обработки.

Загрузка документа (PDF, DOCX, изображений и т.д.) для извлечения и
обработки через конвейер документов.

**Аргументы:**

`document`: Содержимое документа в виде байтов
`id`: Необязательный идентификатор документа (генерируется автоматически, если None)
`metadata`: Необязательные метаданные (список троек или объект с методом emit)
`user`: Идентификатор пользователя/пространства ключей (необязательно)
`collection`: Идентификатор коллекции (необязательно)

**Возвращает:** dict: Ответ обработки

**Вызывает исключения:**

`RuntimeError`: Если предоставлены метаданные без идентификатора

**Пример:**

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

Загрузка текстового контента для обработки.

Загрузка текстового контента для извлечения и обработки через конвейер текста.


**Аргументы:**

`text`: Текстовый контент в виде байтов
`id`: Необязательный идентификатор документа (генерируется автоматически, если None)
`metadata`: Необязательные метаданные (список троек или объект с методом emit)
`charset`: Кодировка символов (по умолчанию: "utf-8")
`user`: Идентификатор пользователя/пространства ключей (необязательно)
`collection`: Идентификатор коллекции (необязательно)

**Возвращает:** dict: Ответ обработки

**Вызывает исключения:**

`RuntimeError`: Если предоставлены метаданные без идентификатора

**Пример:**

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

Выполнить инструмент протокола контекста модели (Model Context Protocol, MCP).

Инструменты MCP предоставляют расширяемую функциональность для агентов и рабочих процессов,
позволяя интеграцию с внешними системами и сервисами.

**Аргументы:**

`name`: Имя/идентификатор инструмента
`parameters`: Словарь параметров инструмента (по умолчанию: {})

**Возвращает:** str или dict: Результат выполнения инструмента

**Вызывает исключение:**

`ProtocolException`: Если формат ответа недействителен

**Пример:**

```python
flow = api.flow().id("default")

# Execute a tool
result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `nlp_query(self, question, max_results=100)`

Преобразование вопроса на естественном языке в запрос GraphQL.

**Аргументы:**

`question`: Вопрос на естественном языке
`max_results`: Максимальное количество возвращаемых результатов (по умолчанию: 100)

**Возвращает:** словарь с полями graphql_query, variables, detected_schemas, confidence

### `prompt(self, id, variables)`

Выполнение шаблона запроса с подстановкой переменных.

Шаблоны запросов позволяют использовать многократно шаблоны запросов с динамическими переменными.
Это полезно для обеспечения согласованности при разработке запросов.

**Аргументы:**

`id`: Идентификатор шаблона запроса.
`variables`: Словарь, содержащий соответствия между именами переменных и их значениями.

**Возвращает:** str или dict: Результат отрисованного запроса (текст или структурированный объект).

**Вызывает исключение:**

`ProtocolException`: Если формат ответа недействителен.

**Пример:**

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

Отправьте запрос на создание сервиса для этого экземпляра потока.

**Аргументы:**

`path`: Путь к сервису (например, "service/text-completion")
`request`: Словарь с данными запроса

**Возвращает:** dict: Ответ сервиса

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

Запрос данных строк с использованием семантического сходства по индексированным полям.

Находит строки, значения индексированных полей которых семантически схожи с
входным текстом, используя векторные представления. Это обеспечивает нечеткое/семантическое сопоставление
структурированных данных.

**Аргументы:**

`text`: Текст запроса для семантического поиска
`schema_name`: Имя схемы для поиска
`user`: Идентификатор пользователя/пространства ключей (по умолчанию: "trustgraph")
`collection`: Идентификатор коллекции (по умолчанию: "default")
`index_name`: Необязательное имя индекса для фильтрации поиска по определенному индексу
`limit`: Максимальное количество результатов (по умолчанию: 10)

**Возвращает:** dict: Результаты запроса с совпадениями, содержащими index_name, index_value, text и score

**Пример:**

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

Выполнение запроса GraphQL к структурированным данным в графе знаний.

Запросы структурированных данных с использованием синтаксиса GraphQL, что позволяет выполнять сложные запросы
с фильтрацией, агрегацией и обходом связей.

**Аргументы:**

`query`: Строка запроса GraphQL
`user`: Идентификатор пользователя/пространства (по умолчанию: "trustgraph")
`collection`: Идентификатор коллекции (по умолчанию: "default")
`variables`: Необязательный словарь переменных запроса
`operation_name`: Необязательное имя операции для документов с несколькими операциями

**Возвращает:** dict: Ответ GraphQL с полями 'data', 'errors' и/или 'extensions'

**Вызывает исключение:**

`ProtocolException`: Если возникает системная ошибка

**Пример:**

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

Выберите соответствующие схемы для образца данных, используя анализ запросов.

**Аргументы:**

`sample`: Образец данных для анализа (текстовое содержимое)
`options`: Необязательные параметры

**Возвращает:** словарь с массивом schema_matches и метаданными

### `structured_query(self, question, user='trustgraph', collection='default')`

Выполните запрос на естественном языке к структурированным данным.
Объединяет преобразование запроса NLP и выполнение GraphQL.

**Аргументы:**

`question`: Запрос на естественном языке
`user`: Идентификатор пространства ключей Cassandra (по умолчанию: "trustgraph")
`collection`: Идентификатор набора данных (по умолчанию: "default")

**Возвращает:** словарь с данными и, возможно, ошибками

### `text_completion(self, system, prompt)`

Выполните текстовое завершение с использованием LLM потока.

**Аргументы:**

`system`: Системная подсказка, определяющая поведение помощника
`prompt`: Подсказка/вопрос пользователя

**Возвращает:** str: Сгенерированный текст ответа

**Пример:**

```python
flow = api.flow().id("default")
response = flow.text_completion(
    system="You are a helpful assistant",
    prompt="What is quantum computing?"
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

Запрос троек знаний графа с использованием сопоставления с образцом.

Поиск троек RDF, соответствующих заданным шаблонам субъекта, предиката и/или
объекта. Неуказанные параметры действуют как подстановочные знаки.

**Аргументы:**

`s`: URI субъекта (необязательно, используйте None для подстановочного знака)
`p`: URI предиката (необязательно, используйте None для подстановочного знака)
`o`: URI объекта или литерала (необязательно, используйте None для подстановочного знака)
`user`: Идентификатор пользователя/пространства ключей (необязательно)
`collection`: Идентификатор коллекции (необязательно)
`limit`: Максимальное количество возвращаемых результатов (по умолчанию: 10000)

**Возвращает:** list[Triple]: Список объектов Triple, соответствующих условиям.

**Вызывает исключение:**

`RuntimeError`: Если s или p не являются Uri, или o не является Uri/Literal

**Пример:**

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

Клиент для управления асинхронными процессами с использованием REST API.

Предоставляет операции управления процессами на основе async/await, включая перечисление,
запуск, остановку процессов и управление определениями классов процессов. Также предоставляет
доступ к сервисам, связанным с процессами, таким как агенты, RAG и запросы, через REST-интерфейсы без потоковой передачи.


Обратите внимание: для поддержки потоковой передачи используйте AsyncSocketClient.

### Методы

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Инициализация асинхронного клиента для управления процессами.

**Аргументы:**

`url`: Базовый URL для API TrustGraph.
`timeout`: Время ожидания запроса в секундах.
`token`: Необязательный токен для аутентификации.

### `aclose(self) -> None`

Закрытие асинхронного клиента и освобождение ресурсов.

Обратите внимание: очистка выполняется автоматически менеджерами контекста сессии aiohttp.
Этот метод предоставляется для обеспечения согласованности с другими асинхронными клиентами.

### `delete_class(self, class_name: str)`

Удаление определения класса процесса.

Удаляет шаблон класса процесса из системы. Не влияет на
работающие экземпляры процессов.

**Аргументы:**

`class_name`: Имя класса процесса для удаления.

**Пример:**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

Получение определения потока.

Получает полную конфигурацию потока, включая его имя класса,
описание и параметры.

**Аргументы:**

`id`: Идентификатор потока

**Возвращает:** dict: Объект определения потока

**Пример:**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

Получение определения класса потока.

Получает определение шаблона для класса потока, включая его
схему конфигурации и привязки к сервисам.

**Аргументы:**

`class_name`: Имя класса потока

**Возвращает:** dict: Объект определения класса потока

**Пример:**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

Получение экземпляра клиента асинхронного потока.

Возвращает клиент для взаимодействия со службами конкретного потока (агент, RAG, запросы, встраивания и т.д.).


**Аргументы:**

`flow_id`: Идентификатор потока

**Возвращает:** AsyncFlowInstance: Клиент для операций, специфичных для потока

**Пример:**

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

Перечислить все идентификаторы потоков.

Получает идентификаторы всех потоков, которые в настоящее время развернуты в системе.

**Возвращает:** list[str]: Список идентификаторов потоков

**Пример:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

Перечислите все имена классов потоков.

Получает имена всех классов потоков (шаблонов), доступных в системе.

**Возвращает:** list[str]: Список имен классов потоков.

**Пример:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

Создать или обновить определение класса потока.

Хранит шаблон класса потока, который можно использовать для создания экземпляров потоков.

**Аргументы:**

`class_name`: Имя класса потока
`definition`: Объект определения класса потока

**Пример:**

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

Выполнить асинхронный HTTP POST-запрос к API шлюза.

Внутренний метод для выполнения аутентифицированных запросов к API TrustGraph.

**Аргументы:**

`path`: Путь к API (относительно базового URL)
`request_data`: Словарь с данными запроса

**Возвращает:** dict: Объект ответа от API

**Вызывает исключения:**

`ProtocolException`: Если HTTP-статус не 200 или ответ не является допустимым JSON
`ApplicationException`: Если API возвращает ответ об ошибке

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

Запустить новый экземпляр потока.

Создает и запускает поток из определения класса потока с указанными
параметрами.

**Аргументы:**

`class_name`: Имя класса потока для создания экземпляра
`id`: Идентификатор нового экземпляра потока
`description`: Человекочитаемое описание потока
`parameters`: Необязательные параметры конфигурации для потока

**Пример:**

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

Остановить выполняющийся процесс.

Останавливает и удаляет экземпляр процесса, освобождая его ресурсы.

**Аргументы:**

`id`: Идентификатор процесса, который необходимо остановить.

**Пример:**

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

Клиент экземпляра асинхронного потока.

Предоставляет доступ с использованием async/await к сервисам, связанным с потоком, включая агентов,
запросы RAG, эмбеддинги и запросы к графу. Все операции возвращают полные
ответы (без потоковой передачи).

Обратите внимание: для поддержки потоковой передачи используйте AsyncSocketFlowInstance.

### Методы

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

Инициализация асинхронного экземпляра потока.

**Аргументы:**

`flow`: Родительский клиент AsyncFlow
`flow_id`: Идентификатор потока

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

Выполнение операции агента (без потоковой передачи).

Запускает агента для ответа на вопрос, с необязательным состоянием разговора и
историей. Возвращает полный ответ после завершения обработки агентом.


Обратите внимание: этот метод не поддерживает потоковую передачу. Для получения мыслей и наблюдений агента в режиме реального времени используйте AsyncSocketFlowInstance.agent().


**Аргументы:**

`question`: Вопрос или инструкция пользователя
`user`: Идентификатор пользователя
`state`: Необязательный словарь состояния для контекста разговора
`group`: Необязательный идентификатор группы для управления сеансом
`history`: Необязательный список истории разговоров
`**kwargs`: Дополнительные параметры, специфичные для сервиса

**Возвращает:** dict: Полный ответ агента, включая ответ и метаданные

**Пример:**

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

Выполнение запроса RAG на основе документов (без потоковой передачи).

Выполняет генерацию с использованием информации, полученной из документов.
Извлекает соответствующие фрагменты документов с помощью семантического поиска, а затем генерирует
ответ, основанный на извлеченных документах. Возвращает полный ответ.

Обратите внимание: этот метод не поддерживает потоковую передачу. Для получения потоковых ответов RAG используйте AsyncSocketFlowInstance.document_rag().


**Аргументы:**

`query`: Текст запроса пользователя
`user`: Идентификатор пользователя
`collection`: Идентификатор коллекции, содержащей документы
`doc_limit`: Максимальное количество фрагментов документов для извлечения (по умолчанию: 10)
`**kwargs`: Дополнительные параметры, специфичные для сервиса

**Возвращает:** str: Полный сгенерированный ответ, основанный на данных документов

**Пример:**

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

Генерирует векторные представления для входных текстов.

Преобразует тексты в числовые векторные представления, используя
настроенную модель для создания векторных представлений. Полезно для семантического поиска и
сравнения схожести.

**Аргументы:**

`texts`: Список входных текстов для создания векторных представлений.
`**kwargs`: Дополнительные параметры, специфичные для сервиса.

**Возвращает:** dict: Ответ, содержащий векторные представления.

**Пример:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

Выполняет поиск векторных представлений графов для семантического поиска сущностей.

Выполняет семантический поиск по векторным представлениям сущностей графа для поиска сущностей,
наиболее релевантных входному тексту. Возвращает сущности, отсортированные по степени схожести.

**Аргументы:**

`text`: Текст запроса для семантического поиска
`user`: Идентификатор пользователя
`collection`: Идентификатор коллекции, содержащей векторные представления графа
`limit`: Максимальное количество возвращаемых результатов (по умолчанию: 10)
`**kwargs`: Дополнительные параметры, специфичные для сервиса

**Возвращает:** dict: Ответ, содержащий отсортированные совпадения сущностей с оценками схожести

**Пример:**

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

Выполнение запроса RAG на основе графа (без потоковой передачи).

Выполняет генерацию с использованием информации, полученной из графа знаний.
Определяет соответствующие сущности и их взаимосвязи, а затем генерирует
ответ, основанный на структуре графа. Возвращает полный ответ.

Обратите внимание: этот метод не поддерживает потоковую передачу. Для получения потоковых ответов RAG используйте AsyncSocketFlowInstance.graph_rag().


**Аргументы:**

`query`: Текст запроса пользователя
`user`: Идентификатор пользователя
`collection`: Идентификатор коллекции, содержащей граф знаний
`max_subgraph_size`: Максимальное количество троек на подграфе (по умолчанию: 1000)
`max_subgraph_count`: Максимальное количество подграфов для извлечения (по умолчанию: 5)
`max_entity_distance`: Максимальное расстояние графа для расширения сущностей (по умолчанию: 3)
`**kwargs`: Дополнительные параметры, специфичные для сервиса

**Возвращает:** str: Полный сгенерированный ответ, основанный на данных графа

**Пример:**

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

Отправка запроса к сервису, доступному в рамках текущего потока.

Внутренний метод для вызова сервисов в пределах текущего экземпляра потока.

**Аргументы:**

`service`: Имя сервиса (например, "agent", "graph-rag", "triples")
`request_data`: Тело запроса к сервису

**Возвращает:** dict: Объект ответа от сервиса

**Вызывает исключения:**

`ProtocolException`: Если запрос не удался или ответ недействителен
`ApplicationException`: Если сервис вернул ошибку

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

Запрос векторных представлений строк для семантического поиска в структурированных данных.

Выполняет семантический поиск по векторным представлениям индексов строк для поиска строк, чьи
значения индексированных полей наиболее близки к входному тексту. Обеспечивает
нечеткое/семантическое сопоставление в структурированных данных.

**Аргументы:**

`text`: Текст запроса для семантического поиска
`schema_name`: Имя схемы для поиска
`user`: Идентификатор пользователя (по умолчанию: "trustgraph")
`collection`: Идентификатор коллекции (по умолчанию: "default")
`index_name`: Необязательное имя индекса для фильтрации поиска по конкретному индексу
`limit`: Максимальное количество возвращаемых результатов (по умолчанию: 10)
`**kwargs`: Дополнительные параметры, специфичные для сервиса

**Возвращает:** dict: Ответ, содержащий совпадения с index_name, index_value, text и score

**Пример:**

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

Выполнение запроса GraphQL к сохраненным строкам.

Запросы структурированные данные строк, используя синтаксис GraphQL. Поддерживает сложные
запросы с переменными и именованными операциями.

**Аргументы:**

`query`: Строка запроса GraphQL
`user`: Идентификатор пользователя
`collection`: Идентификатор коллекции, содержащей строки
`variables`: Необязательные переменные запроса GraphQL
`operation_name`: Необязательное имя операции для запросов с несколькими операциями
`**kwargs`: Дополнительные параметры, специфичные для сервиса

**Возвращает:** dict: Ответ GraphQL с данными и/или ошибками

**Пример:**

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

Генерирует текстовое завершение (не в режиме потоковой передачи).

Генерирует текстовый ответ от LLM на основе системной подсказки и пользовательской подсказки.
Возвращает полный текст ответа.

Обратите внимание: этот метод не поддерживает потоковую передачу. Для генерации текста в режиме потоковой передачи используйте AsyncSocketFlowInstance.text_completion().


**Аргументы:**

`system`: Системная подсказка, определяющая поведение LLM.
`prompt`: Пользовательская подсказка или вопрос.
`**kwargs`: Дополнительные параметры, специфичные для сервиса.

**Возвращает:** str: Полный сгенерированный текст ответа.

**Пример:**

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

Запрос RDF-тройств с использованием сопоставления с образцом.

Поиск тройств, соответствующих указанным шаблонам субъекта, предиката и/или
объекта. Шаблоны используют "None" в качестве подстановочного знака для сопоставления с любым значением.

**Аргументы:**

`s`: Шаблон субъекта (None для подстановочного знака)
`p`: Шаблон предиката (None для подстановочного знака)
`o`: Шаблон объекта (None для подстановочного знака)
`user`: Идентификатор пользователя (None для всех пользователей)
`collection`: Идентификатор коллекции (None для всех коллекций)
`limit`: Максимальное количество тройств для возврата (по умолчанию: 100)
`**kwargs`: Дополнительные параметры, специфичные для сервиса

**Возвращает:** dict: Ответ, содержащий соответствующие тройства

**Пример:**

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

Синхронный WebSocket-клиент для потоковых операций.

Предоставляет синхронный интерфейс для сервисов TrustGraph, основанных на WebSocket,
обертывая асинхронную библиотеку websockets с использованием синхронных генераторов для удобства использования.
Поддерживает потоковые ответы от агентов, запросы RAG и текстовые подсказки.

Обратите внимание: это синхронная обертка вокруг асинхронных операций WebSocket. Для
полной асинхронной поддержки используйте AsyncSocketClient.

### Методы

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Инициализация синхронного WebSocket-клиента.

**Аргументы:**

`url`: Базовый URL для API TrustGraph (HTTP/HTTPS будет преобразован в WS/WSS)
`timeout`: Время ожидания WebSocket в секундах
`token`: Необязательный токен для аутентификации

### `close(self) -> None`

Закрытие WebSocket-соединений.

Обратите внимание: очистка выполняется автоматически с помощью менеджеров контекста в асинхронном коде.

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

Получение экземпляра потока для потоковых операций WebSocket.

**Аргументы:**

`flow_id`: Идентификатор потока

**Возвращает:** SocketFlowInstance: Экземпляр потока с методами потоковой передачи

**Пример:**

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

Экземпляр потока WebSocket для операций потоковой передачи.

Предоставляет тот же интерфейс, что и FlowInstance REST, но с поддержкой потоковой передачи на основе WebSocket
для получения ответов в реальном времени. Все методы поддерживают необязательный
параметр `streaming` для включения постепенной доставки результатов.

### Методы

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

Инициализация экземпляра потока сокета.

**Аргументы:**

`client`: Родительский SocketClient
`flow_id`: Идентификатор потока

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

Выполнение операции агента с поддержкой потоковой передачи.

Агенты могут выполнять многоэтапные рассуждения с использованием инструментов. Этот метод всегда
возвращает потоковые фрагменты (мысли, наблюдения, ответы), даже когда
streaming=False, чтобы показать процесс рассуждений агента.

**Аргументы:**

`question`: Вопрос или инструкция пользователя
`user`: Идентификатор пользователя
`state`: Необязательный словарь состояния для разговоров с состоянием
`group`: Необязательный идентификатор группы для многопользовательских контекстов
`history`: Необязательная история разговоров в виде списка словарей сообщений
`streaming`: Включить режим потоковой передачи (по умолчанию: False)
`**kwargs`: Дополнительные параметры, передаваемые службе агента

**Возвращает:** Iterator[StreamingChunk]: Поток мыслей, наблюдений и ответов агента

**Пример:**

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

Выполнение операции агента с поддержкой объяснимости.

Передает как фрагменты контента (AgentThought, AgentObservation, AgentAnswer),
так и события, связанные с происхождением (ProvenanceEvent). События, связанные с происхождением, содержат URI,
которые можно получить с помощью ExplainabilityClient для получения подробной информации
о процессе рассуждений агента.

Трассировка агента состоит из:
Сессия: Исходный вопрос и метаданные сессии.
Итерации: Каждый цикл мыслей/действий/наблюдений.
Заключение: Окончательный ответ.

**Аргументы:**

`question`: Вопрос или инструкция пользователя.
`user`: Идентификатор пользователя.
`collection`: Идентификатор коллекции для хранения данных о происхождении.
`state`: Необязательный словарь состояния для разговоров с сохранением состояния.
`group`: Необязательный идентификатор группы для многопользовательских контекстов.
`history`: Необязательная история разговоров в виде списка словарей сообщений.
`**kwargs`: Дополнительные параметры, передаваемые службе агента.
`Yields`: 
`Union[StreamingChunk, ProvenanceEvent]`: Фрагменты агента и события, связанные с происхождением.

**Пример:**

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

Запрос фрагментов документов с использованием семантического сходства.

**Аргументы:**

`text`: Текст запроса для семантического поиска
`user`: Идентификатор пользователя/пространства ключей
`collection`: Идентификатор коллекции
`limit`: Максимальное количество результатов (по умолчанию: 10)
`**kwargs`: Дополнительные параметры, передаваемые сервису

**Возвращает:** dict: Результаты запроса с идентификаторами фрагментов соответствующих фрагментов документов

**Пример:**

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

Выполнение запроса RAG на основе документов с возможностью опциональной потоковой передачи.

Использует векторные представления для поиска релевантных фрагментов документов, а затем генерирует
ответ с использованием LLM. Режим потоковой передачи предоставляет результаты постепенно.

**Аргументы:**

`query`: Запрос на естественном языке
`user`: Идентификатор пользователя/пространства
`collection`: Идентификатор коллекции
`doc_limit`: Максимальное количество фрагментов документов для извлечения (по умолчанию: 10)
`streaming`: Включить режим потоковой передачи (по умолчанию: False)
`**kwargs`: Дополнительные параметры, передаваемые службе

**Возвращает:** Union[str, Iterator[str]]: Полный ответ или поток текстовых фрагментов

**Пример:**

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

Выполнение запроса RAG на основе документов с поддержкой объяснимости.

Передает как фрагменты контента (RAGChunk), так и события, связанные с происхождением (ProvenanceEvent).
События, связанные с происхождением, содержат URI, которые можно получить с помощью ExplainabilityClient,
чтобы получить подробную информацию о том, как был сгенерирован ответ.

Трассировка RAG для документа состоит из:
Вопрос: Запрос пользователя
Исследование: Фрагменты, извлеченные из хранилища документов (chunk_count)
Синтез: Сгенерированный ответ

**Аргументы:**

`query`: Запрос на естественном языке
`user`: Идентификатор пользователя/пространства ключей
`collection`: Идентификатор коллекции
`doc_limit`: Максимальное количество фрагментов документов для извлечения (по умолчанию: 10)
`**kwargs`: Дополнительные параметры, передаваемые службе
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: Фрагменты контента и события, связанные с происхождением

**Пример:**

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

Создание векторных представлений для одного или нескольких текстов.

**Аргументы:**

`texts`: Список входных текстов для создания векторных представлений.
`**kwargs`: Дополнительные параметры, передаваемые сервису.

**Возвращает:** dict: Ответ, содержащий векторы (один набор для каждого входного текста).

**Пример:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Запрос сущностей графа знаний с использованием семантического сходства.

**Аргументы:**

`text`: Текст запроса для семантического поиска
`user`: Идентификатор пользователя/пространства
`collection`: Идентификатор коллекции
`limit`: Максимальное количество результатов (по умолчанию: 10)
`**kwargs`: Дополнительные параметры, передаваемые сервису

**Возвращает:** dict: Результаты запроса с похожими сущностями

**Пример:**

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

Выполнение запроса RAG на основе графа с возможностью потоковой передачи.

Использует структуру графа знаний для поиска релевантного контекста, а затем генерирует
ответ с использованием LLM. Режим потоковой передачи предоставляет результаты постепенно.

**Аргументы:**

`query`: Запрос на естественном языке
`user`: Идентификатор пользователя/пространства
`collection`: Идентификатор коллекции
`max_subgraph_size`: Максимальное общее количество троек в подграфе (по умолчанию: 1000)
`max_subgraph_count`: Максимальное количество подграфов (по умолчанию: 5)
`max_entity_distance`: Максимальная глубина обхода (по умолчанию: 3)
`streaming`: Включить режим потоковой передачи (по умолчанию: False)
`**kwargs`: Дополнительные параметры, передаваемые службе

**Возвращает:** Union[str, Iterator[str]]: Полный ответ или поток текстовых фрагментов

**Пример:**

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

Выполнение запроса RAG на основе графов с поддержкой объяснимости.

Передает как фрагменты контента (RAGChunk), так и события, связанные с происхождением (ProvenanceEvent).
События, связанные с происхождением, содержат URI, которые можно получить с помощью ExplainabilityClient,
чтобы получить подробную информацию о том, как был сгенерирован ответ.

**Аргументы:**

`query`: Запрос на естественном языке
`user`: Идентификатор пользователя/пространства
`collection`: Идентификатор коллекции
`max_subgraph_size`: Максимальное общее количество троек в подграфе (по умолчанию: 1000)
`max_subgraph_count`: Максимальное количество подграфов (по умолчанию: 5)
`max_entity_distance`: Максимальная глубина обхода (по умолчанию: 3)
`**kwargs`: Дополнительные параметры, передаваемые службе
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: Фрагменты контента и события, связанные с происхождением

**Пример:**

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

Запустить инструмент протокола контекста модели (MCP).

**Аргументы:**

`name`: Имя/идентификатор инструмента
`parameters`: Словарь параметров инструмента
`**kwargs`: Дополнительные параметры, передаваемые сервису

**Возвращает:** dict: Результат выполнения инструмента

**Пример:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Выполнение шаблона запроса с возможностью потоковой передачи.

**Аргументы:**

`id`: Идентификатор шаблона запроса
`variables`: Словарь, содержащий соответствия между именами переменных и их значениями
`streaming`: Включить режим потоковой передачи (по умолчанию: False)
`**kwargs`: Дополнительные параметры, передаваемые службе

**Возвращает:** Union[str, Iterator[str]]: Полный ответ или поток текстовых фрагментов

**Пример:**

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

Запрос данных строк с использованием семантического сходства по индексированным полям.

Находит строки, значения индексированных полей которых семантически схожи с
входным текстом, используя векторные представления. Это обеспечивает нечеткое/семантическое сопоставление
структурированных данных.

**Аргументы:**

`text`: Текст запроса для семантического поиска
`schema_name`: Имя схемы для поиска
`user`: Идентификатор пользователя/пространства ключей (по умолчанию: "trustgraph")
`collection`: Идентификатор коллекции (по умолчанию: "default")
`index_name`: Необязательное имя индекса для фильтрации поиска по определенному индексу
`limit`: Максимальное количество результатов (по умолчанию: 10)
`**kwargs`: Дополнительные параметры, передаваемые службе

**Возвращает:** dict: Результаты запроса, содержащие соответствия, включая index_name, index_value, text и score

**Пример:**

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

Выполнение запроса GraphQL к структурированным строкам.

**Аргументы:**

`query`: Строка запроса GraphQL
`user`: Идентификатор пользователя/пространства ключей
`collection`: Идентификатор коллекции
`variables`: Необязательный словарь переменных запроса
`operation_name`: Необязательное имя операции для документов с несколькими операциями
`**kwargs`: Дополнительные параметры, передаваемые службе

**Возвращает:** dict: Ответ GraphQL с данными, ошибками и/или расширениями

**Пример:**

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

Выполнить завершение текста с возможностью потоковой передачи.

**Аргументы:**

`system`: Системная подсказка, определяющая поведение ассистента.
`prompt`: Подсказка/вопрос пользователя.
`streaming`: Включить режим потоковой передачи (по умолчанию: False).
`**kwargs`: Дополнительные параметры, передаваемые сервису.

**Возвращает:** Union[str, Iterator[str]]: Полный ответ или поток текстовых фрагментов.

**Пример:**

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

Запрос троек графа знаний с использованием сопоставления с образцом.

**Аргументы:**

`s`: Фильтр по субъекту - строка URI, словарь терминов или None для подстановки
`p`: Фильтр по предикату - строка URI, словарь терминов или None для подстановки
`o`: Фильтр по объекту - строка URI/литерала, словарь терминов или None для подстановки
`g`: Фильтр по именованному графу - строка URI или None для всех графов
`user`: Идентификатор пользователя/пространства ключей (необязательно)
`collection`: Идентификатор коллекции (необязательно)
`limit`: Максимальное количество возвращаемых результатов (по умолчанию: 100)
`**kwargs`: Дополнительные параметры, передаваемые сервису

**Возвращает:** List[Dict]: Список соответствующих троек в формате передачи данных

**Пример:**

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

Запрос троек знаний с использованием потоковых пакетов.

Возвращает пакеты троек по мере их поступления, что сокращает время получения первого результата
и объем используемой памяти для больших наборов результатов.

**Аргументы:**

`s`: Фильтр по субъекту - URI строка, словарь терминов или None для подстановки
`p`: Фильтр по предикату - URI строка, словарь терминов или None для подстановки
`o`: Фильтр по объекту - URI/строка литерала, словарь терминов или None для подстановки
`g`: Фильтр по именованному графу - URI строка или None для всех графов
`user`: Идентификатор пользователя/пространства ключей (необязательно)
`collection`: Идентификатор коллекции (необязательно)
`limit`: Максимальное количество возвращаемых результатов (по умолчанию: 100)
`batch_size`: Количество троек в пакете (по умолчанию: 20)
`**kwargs`: Дополнительные параметры, передаваемые сервису
`Yields`: 
`List[Dict]`: Пакеты троек в формате передачи данных

**Пример:**

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

Асинхронный WebSocket клиент

### Методы

### `__init__(self, url: str, timeout: int, token: str | None)`

Инициализация объекта `self`.  См. `help(type(self))` для получения точного определения.

### `aclose(self)`

Закрытие WebSocket соединения

### `flow(self, flow_id: str)`

Получение асинхронной реализации для операций с WebSocket


--

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

Экземпляр асинхронного потока WebSocket.

### Методы

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

Инициализация объекта `self`.  См. `help(type(self))` для получения точного определения.

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

Агент с опциональной потоковой передачей.

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

Документирование RAG с опциональной потоковой передачей.

### `embeddings(self, texts: list, **kwargs)`

Генерация текстовых векторных представлений.

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

Запрос векторных представлений графа для семантического поиска.

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

Граф RAG с опциональной потоковой передачей.

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

Выполнение инструмента MCP.

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

Выполнение запроса с опциональной потоковой передачей.

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

Запрос векторных представлений строк для семантического поиска структурированных данных.

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

Запрос GraphQL для структурированных строк.

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

Автозаполнение текста с опциональной потоковой передачей.

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

Запрос шаблона триплетов.


--

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

Создание словаря Term в формате двоичных данных из значения.

Правила автоматического определения (когда `term_type` равен None):
  Уже является словарем с ключом 't' -> возвращается как есть (уже является Term).
  Начинается с http://, https://, urn: -> IRI.
  Ограничено символами < (например, <http://...>) -> IRI (символы угловых скобок удаляются).
  Все остальное -> литерал.

**Аргументы:**

`value`: Значение Term (строка, словарь или None).
`term_type`: Один из вариантов: 'iri', 'literal' или None для автоматического определения.
`datatype`: Тип данных для литеральных объектов (например, xsd:integer).
`language`: Языковой тег для литеральных объектов (например, en).

**Возвращает:** dict: Словарь Term в формате двоичных данных или None, если значение равно None.


--

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

Клиент для синхронных массовых операций импорта/экспорта.

Обеспечивает эффективную массовую передачу данных через WebSocket для больших наборов данных.
Оборачивает асинхронные операции WebSocket в синхронные генераторы для удобства использования.

Примечание: Для полной поддержки асинхронности используйте AsyncBulkClient.

### Методы

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Инициализация синхронного клиента для массовых операций.

**Аргументы:**

`url`: Базовый URL для API TrustGraph (HTTP/HTTPS будут преобразованы в WS/WSS)
`timeout`: Время ожидания WebSocket в секундах
`token`: Необязательный токен для аутентификации

### `close(self) -> None`

Закрытие соединений

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Массовый экспорт векторных представлений документов из потока.

Эффективно загружает все векторные представления фрагментов документов через потоковую передачу WebSocket.

**Аргументы:**

`flow`: Идентификатор потока
`**kwargs`: Дополнительные параметры (зарезервированы для будущего использования)

**Возвращает:** Iterator[Dict[str, Any]]: Поток словарей векторных представлений

**Пример:**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Массовый экспорт контекстов сущностей из потока.

Эффективно загружает всю информацию о контексте сущностей через потоковую передачу WebSocket.

**Аргументы:**

`flow`: Идентификатор потока
`**kwargs`: Дополнительные параметры (зарезервированы для будущего использования)

**Возвращает:** Iterator[Dict[str, Any]]: Поток словарей контекста

**Пример:**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Массовый экспорт векторных представлений графов из потока.

Эффективно загружает все векторные представления сущностей графа через потоковую передачу WebSocket.

**Аргументы:**

`flow`: Идентификатор потока
`**kwargs`: Дополнительные параметры (зарезервировано для будущих версий)

**Возвращает:** Iterator[Dict[str, Any]]: Поток словарей векторных представлений

**Пример:**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

Массовый экспорт RDF-тройств из потока.

Эффективно загружает все тройства через потоковую передачу WebSocket.

**Аргументы:**

`flow`: Идентификатор потока
`**kwargs`: Дополнительные параметры (зарезервированы для будущего использования)

**Возвращает:** Iterator[Triple]: Поток объектов Triple

**Пример:**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Импорт большого количества векторных представлений документов в поток.

Эффективная загрузка векторных представлений фрагментов документов через потоковую передачу WebSocket
для использования в запросах RAG (Retrieval-Augmented Generation) к документам.

**Аргументы:**

`flow`: Идентификатор потока
`embeddings`: Итератор, возвращающий словари векторных представлений
`**kwargs`: Дополнительные параметры (зарезервированы для будущего использования)

**Пример:**

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

Импорт большого количества сущностей в контекст потока.

Эффективная загрузка информации о контексте сущностей через потоковую передачу WebSocket.
Контексты сущностей предоставляют дополнительный текстовый контекст о сущностях графа
для повышения производительности RAG.

**Аргументы:**

`flow`: Идентификатор потока
`contexts`: Итератор, возвращающий словари контекста
`metadata`: Словарь метаданных с id, метаданными, пользователем, коллекцией
`batch_size`: Количество контекстов в пакете (по умолчанию 100)
`**kwargs`: Дополнительные параметры (зарезервированы для будущего использования)

**Пример:**

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

Импорт графовых представлений в поток.

Эффективная загрузка представлений графовых сущностей через потоковую передачу WebSocket.

**Аргументы:**

`flow`: Идентификатор потока
`embeddings`: Итератор, возвращающий словари представлений
`**kwargs`: Дополнительные параметры (зарезервированы для будущего использования)

**Пример:**

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

Импорт структурированных строк в поток.

Эффективная загрузка структурированных данных в виде строк через потоковую передачу WebSocket
для использования в запросах GraphQL.

**Аргументы:**

`flow`: Идентификатор потока
`rows`: Итератор, возвращающий словари строк
`**kwargs`: Дополнительные параметры (зарезервированы для будущего использования)

**Пример:**

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

Импорт большого количества RDF-тройств в поток.

Эффективно загружает большое количество тройств через потоковую передачу WebSocket.

**Аргументы:**

`flow`: Идентификатор потока
`triples`: Итератор, возвращающий объекты Triple
`metadata`: Словарь метаданных с id, метаданными, пользователем, коллекцией
`batch_size`: Количество тройств в пакете (по умолчанию 100)
`**kwargs`: Дополнительные параметры (зарезервировано для будущего использования)

**Пример:**

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

Клиент для асинхронных пакетных операций.

### Методы

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Инициализация объекта `self`.  См. `help(type(self))` для получения точного определения.

### `aclose(self) -> None`

Закрытие соединений.

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Пакетный экспорт векторных представлений документов через WebSocket.

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Пакетный экспорт контекстов сущностей через WebSocket.

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Пакетный экспорт векторных представлений графа через WebSocket.

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

Пакетный экспорт троек через WebSocket.

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Пакетный импорт векторных представлений документов через WebSocket.

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Пакетный импорт контекстов сущностей через WebSocket.

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Пакетный импорт векторных представлений графа через WebSocket.

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Пакетный импорт строк через WebSocket.

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

Пакетный импорт троек через WebSocket.


--

## `Metrics`

```python
from trustgraph.api import Metrics
```

Клиент для синхронных метрик

### Методы

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.

### `get(self) -> str`

Получение метрик Prometheus в виде текста


--

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

Асинхронный клиент для работы с метриками.

### Методы

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Инициализация объекта.  См. help(type(self)) для получения точного определения.

### `aclose(self) -> None`

Закрытие соединений.

### `get(self) -> str`

Получение метрик Prometheus в текстовом формате.


--

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

Клиент для получения сущностей объяснимости с обеспечением конечной согласованности.

Использует обнаружение состояния покоя: получение, ожидание, повторное получение, сравнение.
Если результаты одинаковы, данные стабильны.

### Методы

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

Инициализация клиента объяснимости.

**Аргументы:**

`flow_instance`: Экземпляр SocketFlowInstance для запроса троек.
`retry_delay`: Задержка между повторными попытками в секундах (по умолчанию: 0.2).
`max_retries`: Максимальное количество повторных попыток (по умолчанию: 10).

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

Определяет, является ли сессия типом GraphRAG или Agent.

**Аргументы:**

`session_uri`: URI сессии/вопроса.
`graph`: Именованный граф.
`user`: Идентификатор пользователя/пространства ключей.
`collection`: Идентификатор коллекции.

**Возвращает:** "graphrag" или "agent".

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Получает полный трассировочный файл Agent, начиная с URI сессии.

Отслеживает цепочку происхождения: Вопрос -> Анализ(ы) -> Вывод.

**Аргументы:**

`session_uri`: URI сессии/вопроса Agent.
`graph`: Именованный граф (по умолчанию: urn:graph:retrieval).
`user`: Идентификатор пользователя/пространства ключей.
`collection`: Идентификатор коллекции.
`api`: Экземпляр TrustGraph Api для доступа к библиотекарю (необязательно).
`max_content`: Максимальная длина содержимого для вывода.

**Возвращает:** Словарь с вопросом, итерациями (список Анализов), сущностями вывода.

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Получает полный трассировочный файл DocumentRAG, начиная с URI вопроса.

Отслеживает цепочку происхождения:
    Вопрос -> Базирование -> Исследование -> Синтез.

**Аргументы:**

`question_uri`: URI сущности вопроса.
`graph`: Именованный граф (по умолчанию: urn:graph:retrieval).
`user`: Идентификатор пользователя/пространства ключей.
`collection`: Идентификатор коллекции.
`api`: Экземпляр TrustGraph Api для доступа к библиотекарю (необязательно).
`max_content`: Максимальная длина содержимого для синтеза.

**Возвращает:** Словарь с вопросом, базированием, исследованием, сущностями синтеза.

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

Получает содержимое из библиотеки по URI документа.

**Аргументы:**

`document_uri`: URI документа в библиотеке.
`api`: Экземпляр TrustGraph Api для доступа к библиотеке.
`user`: Идентификатор пользователя для библиотеки.
`max_content`: Максимальная длина содержимого для возврата.

**Возвращает:** Содержимое документа в виде строки.

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

Получает сущность выбора ребра (используется Focus).

**Аргументы:**

`uri`: URI выбора ребра.
`graph`: Именованный граф для запроса.
`user`: Идентификатор пользователя/пространства ключей.
`collection`: Идентификатор коллекции.

**Возвращает:** EdgeSelection или None, если не найдено.

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

Получение сущности объяснимости по URI с обработкой обеспечения согласованности.

Использует обнаружение состояния покоя:
1. Получение троек для URI
2. Если результатов нет, повторить попытку
3. Если результатов больше нуля, подождать и получить снова
4. Если результаты совпадают, данные стабильны - разобрать и вернуть
5. Если результаты отличаются, данные все еще записываются - повторить попытку

**Аргументы:**

`uri`: URI сущности для получения
`graph`: Именованный граф для запроса (например, "urn:graph:retrieval")
`user`: Идентификатор пользователя/пространства имен
`collection`: Идентификатор коллекции

**Возвращает:** Подкласс ExplainEntity или None, если не найдено

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

Получение сущности Focus и всех ее выбранных ребер.

**Аргументы:**

`uri`: URI сущности Focus
`graph`: Именованный граф для запроса
`user`: Идентификатор пользователя/пространства имен
`collection`: Идентификатор коллекции

**Возвращает:** Focus с заполненными edge_selections или None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Получение полной трассировки GraphRAG, начиная с URI вопроса.

Отслеживает цепочку происхождения: Вопрос -> Основание -> Исследование -> Focus -> Синтез

**Аргументы:**

`question_uri`: URI сущности вопроса
`graph`: Именованный граф (по умолчанию: urn:graph:retrieval)
`user`: Идентификатор пользователя/пространства имен
`collection`: Идентификатор коллекции
`api`: Экземпляр TrustGraph Api для доступа к библиотеке (необязательно)
`max_content`: Максимальная длина содержимого для синтеза

**Возвращает:** Словарь с сущностями вопроса, основания, исследования, Focus и синтеза

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

Перечисление всех сессий объяснимости (вопросов) в коллекции.

**Аргументы:**

`graph`: Именованный граф (по умолчанию: urn:graph:retrieval)
`user`: Идентификатор пользователя/пространства имен
`collection`: Идентификатор коллекции
`limit`: Максимальное количество сессий для возврата

**Возвращает:** Список сущностей Question, отсортированный по времени (самые новые в начале)

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

Разрешение меток для всех компонентов тройки ребра.

**Аргументы:**

`edge`: Словарь с ключами "s", "p", "o"
`user`: Идентификатор пользователя/пространства имен
`collection`: Идентификатор коллекции

**Возвращает:** Кортеж (s_label, p_label, o_label)

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

Разрешение rdfs:label для URI с использованием кэширования.

**Аргументы:**

`uri`: URI, для которого необходимо получить метку
`user`: Идентификатор пользователя/пространства имен
`collection`: Идентификатор коллекции

**Возвращает:** Метка, если найдена, в противном случае сам URI


--

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

Базовый класс для сущностей, обеспечивающих понятность.

**Поля:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>

### Методы

### `__init__(self, uri: str, entity_type: str = '') -> None`

Инициализация объекта self.  См. help(type(self)) для получения точного определения.


--

## `Question`

```python
from trustgraph.api import Question
```

Вопрос (Question entity) - запрос пользователя, который инициировал сессию.

**Поля (Fields):**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`query`: <class 'str'>
`timestamp`: <class 'str'>
`question_type`: <class 'str'>

### Методы (Methods)

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `Exploration`

```python
from trustgraph.api import Exploration
```

Объект исследования - ребра/фрагменты, извлеченные из хранилища знаний.

**Поля:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`edge_count`: <class 'int'>
`chunk_count`: <class 'int'>
`entities`: typing.List[str]

### Методы

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `Focus`

```python
from trustgraph.api import Focus
```

Объект фокусировки - выбранные ребра с использованием логического вывода на основе больших языковых моделей (только для GraphRAG).

**Поля:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`selected_edge_uris`: typing.List[str]
`edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### Методы

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

Синтетическая сущность - окончательный ответ.

**Поля:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Методы

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `Analysis`

```python
from trustgraph.api import Analysis
```

Аналитическая сущность - один цикл мышления/действия/наблюдения (только для Агента).

**Поля:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`action`: <class 'str'>
`arguments`: <class 'str'>
`thought`: <class 'str'>
`observation`: <class 'str'>

### Методы

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

Заключительная сущность - окончательный ответ (только для агента).

**Поля:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Методы

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

Выбранный ребро с обоснованием из шага GraphRAG Focus.

**Поля:**

`uri`: <class 'str'>
`edge`: typing.Dict[str, str] | None
`reasoning`: <class 'str'>

### Методы

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

Преобразование троек в формате "wire" в кортежи (s, p, o).


--

### `extract_term_value(term: Dict[str, Any]) -> Any`

Извлечение значения из словаря Term в формате "wire".


--

## `Triple`

```python
from trustgraph.api import Triple
```

Тройка RDF, представляющая утверждение графа знаний.

**Поля:**

`s`: <class 'str'>
`p`: <class 'str'>
`o`: <class 'str'>

### Методы

### `__init__(self, s: str, p: str, o: str) -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `Uri`

```python
from trustgraph.api import Uri
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Создает новый строковый объект из заданного объекта. Если указаны параметры encoding или
errors, то объект должен предоставлять буфер данных, который будет декодирован с использованием указанной кодировки и обработчика ошибок.
В противном случае возвращается результат object.__str__() (если определен)
или repr(object).
encoding по умолчанию - 'utf-8'.
errors по умолчанию - 'strict'.


### Методы

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

Создает новый строковый объект из заданного объекта. Если указаны параметры encoding или
errors, то объект должен предоставлять буфер данных, который будет декодирован с использованием указанной кодировки и обработчика ошибок.
В противном случае возвращается результат object.__str__() (если определен)
или repr(object).
encoding по умолчанию - 'utf-8'.
errors по умолчанию - 'strict'.


### Методы

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

Идентификатор конфигурационного ключа.

**Поля:**

`type`: <class 'str'>
`key`: <class 'str'>

### Методы

### `__init__(self, type: str, key: str) -> None`

Инициализация объекта self.  См. help(type(self)) для получения точного определения.


--

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

Пара ключ-значение конфигурации.

**Поля:**

`type`: <class 'str'>
`key`: <class 'str'>
`value`: <class 'str'>

### Методы

### `__init__(self, type: str, key: str, value: str) -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

Метаданные для документа в библиотеке.

**Атрибуты:**

`parent_id: Parent document ID for child documents (empty for top`: level docs)

**Поля:**

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

### Методы

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

Метаданные для активной задачи обработки документа.

**Поля:**

`id`: <class 'str'>
`document_id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`flow`: <class 'str'>
`user`: <class 'str'>
`collection`: <class 'str'>
`tags`: typing.List[str]

### Методы

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

Метаданные для набора данных.

Коллекции обеспечивают логическую группировку и изоляцию для документов и
данных графа знаний.

**Атрибуты:**

`name: Human`: читаемое имя коллекции

**Поля:**

`user`: <class 'str'>
`collection`: <class 'str'>
`name`: <class 'str'>
`description`: <class 'str'>
`tags`: typing.List[str]

### Методы

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

Базовый класс для потоковой передачи фрагментов ответа.

Используется для операций потоковой передачи на основе WebSocket, когда ответы доставляются
постепенно по мере их генерации.

**Поля:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>

### Методы

### `__init__(self, content: str, end_of_message: bool = False) -> None`

Инициализация объекта self.  См. help(type(self)) для получения точного определения.


--

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

Обоснование/процесс мышления агента.

Представляет собой внутренние этапы рассуждений или планирования агента во время выполнения.
Эти фрагменты показывают, как агент мыслит о проблеме.

**Поля:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Методы

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

Инициализация self.  См. help(type(self)) для получения точного определения.


--

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

Фрагмент наблюдения за выполнением инструмента агента.

Представляет собой результат или наблюдение, полученное в результате выполнения инструмента или действия.
Эти фрагменты показывают, что агент узнал, используя инструменты.

**Поля:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Методы

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

Инициализация self.  См. help(type(self)) для получения точной сигнатуры.


--

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

Заключительный фрагмент ответа агента.

Представляет собой окончательный ответ агента пользователю на его запрос после завершения
процесса рассуждений и использования инструментов.

**Атрибуты:**

`chunk_type: Always "final`: answer"

**Поля:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_dialog`: <class 'bool'>

### Методы

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

Инициализация self.  См. help(type(self)) для получения точной сигнатуры.


--

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

Поток данных RAG (Retrieval-Augmented Generation).

Используется для потоковой передачи ответов от графовых систем RAG, систем RAG на основе документов, для завершения текста,
и других генеративных сервисов.

**Поля:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_stream`: <class 'bool'>
`error`: typing.Dict[str, str] | None

### Методы

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

Инициализация объекта self.  См. help(type(self)) для получения точного определения.


--

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

Событие, связанное с происхождением, для обеспечения понятности.

Генерируется во время запросов GraphRAG, когда включен режим объяснения.
Каждое событие представляет узел происхождения, созданный во время обработки запроса.

**Поля:**

`explain_id`: <class 'str'>
`explain_graph`: <class 'str'>
`event_type`: <class 'str'>

### Методы

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

Инициализация self.  См. help(type(self)) для получения точной сигнатуры.


--

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

Возникает при возникновении ошибок протокола WebSocket.


--

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

Базовый класс для всех ошибок сервиса TrustGraph.


--

## `AgentError`

```python
from trustgraph.api import AgentError
```

Ошибка сервиса агента


--

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

Ошибка сервиса конфигурации


--

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

Ошибка извлечения документов RAG.


--

## `FlowError`

```python
from trustgraph.api import FlowError
```

Ошибка управления потоком


--

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

Ошибка API Gateway


--

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

Ошибка извлечения данных из графа RAG.


--

## `LLMError`

```python
from trustgraph.api import LLMError
```

Ошибка сервиса LLM


--

## `LoadError`

```python
from trustgraph.api import LoadError
```

Ошибка загрузки данных


--

## `LookupError`

```python
from trustgraph.api import LookupError
```

Ошибка поиска/просмотра.


--

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

Ошибка сервиса обработки запросов на естественном языке.


--

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

Ошибка сервиса запросов данных.


--

## `RequestError`

```python
from trustgraph.api import RequestError
```

Ошибка обработки запроса


--

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

Ошибка сервиса структурированных запросов.


--

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

Неожиданная/неизвестная ошибка


--

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

Базовый класс для всех ошибок сервиса TrustGraph.


--
