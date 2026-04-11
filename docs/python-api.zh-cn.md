---
layout: default
title: "TrustGraph Python API 参考"
parent: "Chinese (Beta)"
---

# TrustGraph Python API 参考

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 安装

```bash
pip install trustgraph
```

## 快速开始

所有类和类型都从 `trustgraph.api` 包中导入：

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

## 目录

### 核心

[Api](#api)

### Flow 客户端

[Flow](#flow)
[FlowInstance](#flowinstance)
[AsyncFlow](#asyncflow)
[AsyncFlowInstance](#asyncflowinstance)

### WebSocket 客户端

[SocketClient](#socketclient)
[SocketFlowInstance](#socketflowinstance)
[AsyncSocketClient](#asyncsocketclient)
[AsyncSocketFlowInstance](#asyncsocketflowinstance)

### 批量操作

[BulkClient](#bulkclient)
[AsyncBulkClient](#asyncbulkclient)

### 指标

[Metrics](#metrics)
[AsyncMetrics](#asyncmetrics)

### 数据类型

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

### 异常

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

主要的 TrustGraph API 客户端，用于同步和异步操作。

此类提供对所有 TrustGraph 服务的访问，包括流程管理、
知识图谱操作、文档处理、RAG 查询等等。它支持
基于 REST 和基于 WebSocket 的通信模式。

客户端可以作为上下文管理器使用，以进行自动资源清理：
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### 方法

### `__aenter__(self)`

进入异步上下文管理器。

### `__aexit__(self, *args)`

退出异步上下文管理器并关闭连接。

### `__enter__(self)`

进入同步上下文管理器。

### `__exit__(self, *args)`

退出同步上下文管理器并关闭连接。

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

初始化 TrustGraph API 客户端。

**参数：**

`url`: TrustGraph API 的基本 URL (默认值: "http://localhost:8088/"")
`timeout`: 请求超时时间，单位为秒 (默认值: 60)
`token`: 可选的用于身份验证的 bearer token

**示例：**

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

关闭所有异步客户端连接。

此方法关闭异步 WebSocket、批量操作和流连接。
当退出异步上下文管理器时，它会自动调用。

**示例：**

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

获取一个异步批量操作客户端。

提供通过 WebSocket 进行异步/等待风格的批量导入/导出操作，以便高效处理大型数据集。

**返回值:** AsyncBulkClient: 异步批量操作客户端


**示例:**

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

获取一个基于异步 REST 的流程客户端。

提供对流程操作的 async/await 风格访问。这对于异步 Python 应用程序和框架（FastAPI、aiohttp 等）是首选。


**返回值:** AsyncFlow: 异步流程客户端

**示例:**

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

获取一个异步指标客户端。

提供对 Prometheus 指标的 async/await 风格访问。

**返回值:** AsyncMetrics: 异步指标客户端

**示例:**

```python
async_metrics = api.async_metrics()
prometheus_text = await async_metrics.get()
print(prometheus_text)
```

### `async_socket(self)`

获取一个异步 WebSocket 客户端，用于流式操作。

提供异步/等待 (async/await) 风格的 WebSocket 访问，并支持流式传输。
这是在 Python 中进行异步流式传输的首选方法。

**返回值:** AsyncSocketClient: 异步 WebSocket 客户端

**示例:**

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

获取用于导入/导出的同步批量操作客户端。

批量操作允许通过 WebSocket 连接高效地传输大型数据集，包括三元组、嵌入、实体上下文和对象。

**返回值:** BulkClient: 同步批量操作客户端


**示例:**

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

关闭所有同步客户端连接。

此方法关闭 WebSocket 和批量操作连接。
它在退出上下文管理器时会自动调用。

**示例：**

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

获取一个 Collection 客户端，用于管理数据集合。

集合将文档和知识图谱数据组织成
逻辑分组，用于隔离和访问控制。

**返回值:** Collection: 集合管理客户端

**示例:**

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

获取一个 Config 客户端，用于管理配置设置。

**返回值:** Config: 配置管理客户端

**示例:**

```python
config = api.config()

# Get configuration values
values = config.get([ConfigKey(type="llm", key="model")])

# Set configuration
config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
```

### `flow(self)`

获取一个 Flow 客户端，用于管理和与流程进行交互。

Flows 是 TrustGraph 中的主要执行单元，提供对
诸如代理、RAG 查询、嵌入和文档处理等服务的访问。

**返回值:** Flow: Flow 管理客户端

**示例:**

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

获取一个 Knowledge 客户端，用于管理知识图谱核心。

**返回值:** Knowledge: 知识图谱管理客户端

**示例:**

```python
knowledge = api.knowledge()

# List available KG cores
cores = knowledge.list_kg_cores(user="trustgraph")

# Load a KG core
knowledge.load_kg_core(id="core-123", user="trustgraph")
```

### `library(self)`

获取一个用于文档管理的库客户端。

该库提供文档存储、元数据管理以及
处理工作流程协调功能。

**返回值:** Library: 文档库管理客户端

**示例:**

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

获取一个同步指标客户端，用于监控。

从 TrustGraph 服务获取 Prometheus 格式的指标，用于监控和可观察性。

**返回值:** 指标：同步指标客户端


**示例:**

```python
metrics = api.metrics()
prometheus_text = metrics.get()
print(prometheus_text)
```

### `request(self, path, request)`

构造一个低级别的 REST API 请求。

此方法主要用于内部使用，但可以在需要时用于直接
API 访问。

**参数：**

`path`: API 端点路径（相对于基本 URL）
`request`: 请求负载，以字典形式表示

**返回值：** dict: 响应对象

**抛出异常：**

`ProtocolException`: 如果响应状态码不是 200 或响应不是 JSON 格式
`ApplicationException`: 如果响应包含错误

**示例：**

```python
response = api.request("flow", {
    "operation": "list-flows"
})
```

### `socket(self)`

获取一个同步的 WebSocket 客户端，用于流式操作。

WebSocket 连接提供流式支持，用于实时响应
来自代理、RAG 查询和文本补全。此方法返回一个
对 WebSocket 协议的同步包装器。

**返回值:** SocketClient: 同步 WebSocket 客户端

**示例:**

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

用于蓝图和流程实例操作的流程管理客户端。

此类提供用于管理流程蓝图（模板）和
流程实例（正在运行的流程）的方法。蓝图定义了流程的结构和
参数，而实例代表可以
执行服务的活动流程。

### 方法

### `__init__(self, api)`

初始化流程客户端。

**参数：**

`api`: 用于发出请求的父级 API 实例。

### `delete_blueprint(self, blueprint_name)`

删除一个流程蓝图。

**参数：**

`blueprint_name`: 要删除的蓝图的名称。

**示例：**

```python
api.flow().delete_blueprint("old-blueprint")
```

### `get(self, id)`

获取正在运行的流程实例的定义。

**参数：**

`id`: 流程实例 ID

**返回值：** dict: 流程实例定义

**示例：**

```python
flow_def = api.flow().get("default")
print(flow_def)
```

### `get_blueprint(self, blueprint_name)`

通过名称获取流程蓝图定义。

**参数：**

`blueprint_name`: 要检索的蓝图的名称

**返回值：** dict: 蓝图定义，以字典形式返回

**示例：**

```python
blueprint = api.flow().get_blueprint("default")
print(blueprint)  # Blueprint configuration
```

### `id(self, id='default')`

获取一个 FlowInstance，用于在特定流程上执行操作。

**参数：**

`id`: 流程标识符 (默认值: "default")

**返回值：** FlowInstance: 用于服务操作的流程实例

**示例：**

```python
flow = api.flow().id("my-flow")
response = flow.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `list(self)`

列出所有活动流程实例。

**返回值:** list[str]: 流程实例 ID 列表

**示例:**

```python
flows = api.flow().list()
print(flows)  # ['default', 'flow-1', 'flow-2', ...]
```

### `list_blueprints(self)`

列出所有可用的流程蓝图。

**返回值:** list[str]: 蓝图名称列表

**示例:**

```python
blueprints = api.flow().list_blueprints()
print(blueprints)  # ['default', 'custom-flow', ...]
```

### `put_blueprint(self, blueprint_name, definition)`

创建或更新流程蓝图。

**参数：**

`blueprint_name`: 蓝图的名称
`definition`: 蓝图定义字典

**示例：**

```python
definition = {
    "services": ["text-completion", "graph-rag"],
    "parameters": {"model": "gpt-4"}
}
api.flow().put_blueprint("my-blueprint", definition)
```

### `request(self, path=None, request=None)`

发送一个流程范围内的 API 请求。

**参数：**

`path`: 可选的流程端点路径后缀
`request`: 请求负载字典

**返回值：** dict: 响应对象

**异常：**

`RuntimeError`: 如果未指定请求参数

### `start(self, blueprint_name, id, description, parameters=None)`

从蓝图启动一个新的流程实例。

**参数：**

`blueprint_name`: 要实例化的蓝图名称
`id`: 流程实例的唯一标识符
`description`: 人类可读的描述
`parameters`: 可选的参数字典

**示例：**

```python
api.flow().start(
    blueprint_name="default",
    id="my-flow",
    description="My custom flow",
    parameters={"model": "gpt-4"}
)
```

### `stop(self, id)`

停止正在运行的流程实例。

**参数：**

`id`: 要停止的流程实例 ID

**示例：**

```python
api.flow().stop("my-flow")
```


--

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

用于在特定流程上执行服务的流程实例客户端。

此类提供对所有 TrustGraph 服务的访问，包括：
文本补全和嵌入
具有状态管理的代理操作
图表和文档 RAG 查询
知识图谱操作（三元组、对象）
文档加载和处理
自然语言到 GraphQL 查询的转换
结构化数据分析和模式检测
MCP 工具执行
提示模板

通过运行的流程实例访问服务，该实例由 ID 标识。

### 方法

### `__init__(self, api, id)`

初始化 FlowInstance。

**参数：**

`api`: 父级 Flow 客户端
`id`: 流程实例标识符

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

执行具有推理和工具使用功能的代理操作。

代理可以执行多步骤推理、使用工具，并在交互过程中维护对话
状态。 这是一个同步的非流版本。

**参数：**

`question`: 用户问题或指令
`user`: 用户标识符（默认为："trustgraph"）
`state`: 可选的状态字典，用于具有状态的对话
`group`: 可选的组标识符，用于多用户上下文
`history`: 可选的对话历史记录，以消息字典列表的形式

**返回值：** str: 代理的最终答案

**示例：**

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

检测结构化数据样本的数据类型。

**参数：**

`sample`: 要分析的数据样本（字符串内容）

**返回值：** 包含 detected_type、confidence 以及可选元数据的字典。

### `diagnose_data(self, sample, schema_name=None, options=None)`

执行综合数据诊断：检测类型并生成描述符。

**参数：**

`sample`: 要分析的数据样本（字符串内容）
`schema_name`: 可选的目标模式名称，用于生成描述符。
`options`: 可选参数（例如，CSV 的分隔符）。

**返回值：** 包含 detected_type、confidence、descriptor 和元数据的字典。

### `document_embeddings_query(self, text, user, collection, limit=10)`

使用语义相似度查询文档块。

查找内容在语义上与输入文本相似的文档块，使用向量嵌入。


**参数：**

`text`: 用于语义搜索的查询文本。
`user`: 用户/键空间标识符。
`collection`: 集合标识符。
`limit`: 最大结果数量（默认为 10）。

**返回值：** 字典：包含 chunk_id 和 score 的查询结果。

**示例：**

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

执行基于文档的检索增强生成 (RAG) 查询。

文档 RAG 使用向量嵌入来查找相关的文档片段，
然后使用 LLM，并将这些片段作为上下文来生成响应。

**参数：**

`query`: 自然语言查询
`user`: 用户/键空间标识符 (默认值: "trustgraph")
`collection`: 集合标识符 (默认值: "default")
`doc_limit`: 要检索的最大文档片段数 (默认值: 10)

**返回值：** str: 包含文档上下文的生成响应

**示例：**

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

为一个或多个文本生成向量嵌入。

将文本转换为适合语义
搜索和相似度比较的密集向量表示。

**参数：**

`texts`: 要嵌入的输入文本列表

**返回值：** list[list[list[float]]]: 向量嵌入，每个输入文本对应一个集合

**示例：**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

生成用于将结构化数据映射到特定模式的描述符。

**参数：**

`sample`: 用于分析的数据样本（字符串内容）
`data_type`: 数据类型（csv, json, xml）
`schema_name`: 用于生成描述符的目标模式名称
`options`: 可选参数（例如，CSV的分隔符）

**返回值：** 包含描述符和元数据的字典

### `graph_embeddings_query(self, text, user, collection, limit=10)`

使用语义相似性查询知识图谱实体。

查找知识图谱中描述与输入文本在语义上
相似的实体，使用向量嵌入。

**参数：**

`text`: 用于语义搜索的查询文本
`user`: 用户/键空间标识符
`collection`: 集合标识符
`limit`: 最大结果数量（默认为 10）

**返回值：** 字典：包含相似实体的查询结果

**示例：**

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

执行基于图的检索增强生成 (RAG) 查询。

图 RAG 使用知识图谱结构来通过
遍历实体关系来查找相关上下文，然后使用 LLM 生成响应。

**参数：**

`query`: 自然语言查询
`user`: 用户/键空间标识符 (默认为: "trustgraph")
`collection`: 集合标识符 (默认为: "default")
`entity_limit`: 检索到的最大实体数量 (默认为: 50)
`triple_limit`: 每个实体的最大三元组数量 (默认为: 30)
`max_subgraph_size`: 子图中最大总三元组数量 (默认为: 150)
`max_path_length`: 最大遍历深度 (默认为: 2)

**返回值：** str: 包含图上下文的生成响应

**示例：**

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

加载一个二进制文档以进行处理。

上传一个文档（PDF、DOCX、图像等），以便从流程的文档管道中提取和
处理。

**参数：**

`document`: 文档内容，以字节形式表示
`id`: 可选的文档标识符（如果为 None，则自动生成）
`metadata`: 可选的元数据（三元组列表或具有 emit 方法的对象）
`user`: 用户/键空间标识符（可选）
`collection`: 集合标识符（可选）

**返回值：** dict: 处理响应

**引发：**

`RuntimeError`: 如果提供了元数据，但没有提供 id

**示例：**

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

加载用于处理的文本内容。

上传文本内容，以便通过流程的
文本管道进行提取和处理。

**参数：**

`text`: 文本内容，以字节形式
`id`: 可选的文档标识符（如果为 None，则自动生成）
`metadata`: 可选的元数据（三元组列表或具有 emit 方法的对象）
`charset`: 字符编码（默认值："utf-8"）
`user`: 用户/键空间标识符（可选）
`collection`: 集合标识符（可选）

**返回值：** dict: 处理响应

**异常：**

`RuntimeError`: 如果提供了元数据，但没有提供 id

**示例：**

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

执行一个模型上下文协议 (MCP) 工具。

MCP 工具提供可扩展的功能，用于代理和工作流程，
允许与外部系统和服务集成。

**参数：**

`name`: 工具名称/标识符
`parameters`: 工具参数字典 (默认: {})

**返回值：** str 或 dict: 工具执行结果

**异常：**

`ProtocolException`: 如果响应格式无效

**示例：**

```python
flow = api.flow().id("default")

# Execute a tool
result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `nlp_query(self, question, max_results=100)`

将自然语言问题转换为 GraphQL 查询。

**参数：**

`question`: 自然语言问题
`max_results`: 返回的最大结果数量（默认为：100）

**返回值：** 包含 graphql_query、variables、detected_schemas 和 confidence 的字典。

### `prompt(self, id, variables)`

执行带有变量替换的提示模板。

提示模板允许使用可重用的提示模式，并带有动态变量。
这种方法对于一致的提示工程非常有用。

**参数：**

`id`: 提示模板标识符
`variables`: 变量名称到值的映射字典

**返回值：** str 或 dict: 渲染后的提示结果（文本或结构化对象）

**引发：**

`ProtocolException`: 如果响应格式无效

**示例：**

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

在此流程实例中发起服务请求。

**参数：**

`path`: 服务路径（例如，"service/text-completion"）
`request`: 请求负载字典

**返回值：** dict: 服务响应

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

使用语义相似性在索引字段上查询行数据。

查找索引字段值在语义上与输入文本相似的行，使用向量嵌入。这实现了对结构化数据的模糊/语义匹配。

**参数：**



`text`: 用于语义搜索的查询文本。
`schema_name`: 要搜索的模式名称。
`user`: 用户/键空间标识符（默认为："trustgraph"）。
`collection`: 集合标识符（默认为："default"）。
`index_name`: 可选的索引名称，用于将搜索限制到特定的索引。
`limit`: 最大结果数量（默认为：10）。

**返回值:** dict: 查询结果，包含 index_name、index_value、text 和 score。

**示例:**

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

对知识图谱中的结构化行执行 GraphQL 查询。

使用 GraphQL 语法查询结构化数据，允许进行复杂的查询，
包括过滤、聚合和关系遍历。

**参数：**

`query`: GraphQL 查询字符串
`user`: 用户/键空间标识符（默认为："trustgraph"）
`collection`: 集合标识符（默认为："default"）
`variables`: 可选的查询变量字典
`operation_name`: 多操作文档的可选操作名称

**返回值：** dict: 包含 'data'、'errors' 和/或 'extensions' 字段的 GraphQL 响应

**引发：**

`ProtocolException`: 如果发生系统级错误

**示例：**

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

使用提示分析，为数据样本选择匹配的模式。

**参数：**

`sample`: 要分析的数据样本（字符串内容）
`options`: 可选参数

**返回值：** 包含 schema_matches 数组和元数据的字典。

### `structured_query(self, question, user='trustgraph', collection='default')`

对结构化数据执行自然语言问题。
结合 NLP 查询转换和 GraphQL 执行。

**参数：**

`question`: 自然语言问题
`user`: Cassandra keyspace 标识符（默认为："trustgraph"）
`collection`: 数据集合标识符（默认为："default"）

**返回值：** 包含数据和可选错误的字典。

### `text_completion(self, system, prompt)`

使用流程的 LLM 执行文本补全。

**参数：**

`system`: 定义助手行为的系统提示。
`prompt`: 用户提示/问题

**返回值：** str: 生成的响应文本

**示例：**

```python
flow = api.flow().id("default")
response = flow.text_completion(
    system="You are a helpful assistant",
    prompt="What is quantum computing?"
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

使用模式匹配查询知识图谱三元组。

搜索与给定的主语、谓语和/或
对象模式匹配的 RDF 三元组。 未指定的参数用作通配符。

**参数：**

`s`: 主语 URI (可选，使用 None 表示通配符)
`p`: 谓语 URI (可选，使用 None 表示通配符)
`o`: 对象 URI 或字面量 (可选，使用 None 表示通配符)
`user`: 用户/键空间标识符 (可选)
`collection`: 集合标识符 (可选)
`limit`: 要返回的最大结果数 (默认：10000)

**返回值：** list[Triple]: 匹配的三元组对象的列表

**引发：**

`RuntimeError`: 如果 s 或 p 不是 Uri，或者 o 不是 Uri/Literal

**示例：**

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

使用 REST API 的异步流程管理客户端。

提供基于 async/await 的流程管理操作，包括列出、
启动、停止流程，以及管理流程类定义。 此外，还提供对流程范围内的服务（如代理、RAG 和查询）的访问，这些服务通过非流式
REST 接口提供。


注意：对于流式支持，请使用 AsyncSocketClient。

### 方法

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

初始化异步流程客户端。

**参数：**

`url`：TrustGraph API 的基本 URL
`timeout`：请求超时时间（以秒为单位）
`token`：可选的用于身份验证的 bearer token

### `aclose(self) -> None`

关闭异步客户端并清理资源。

注意：清理由 aiohttp 会话上下文管理器自动处理。
此方法是为了与其他异步客户端保持一致而提供的。

### `delete_class(self, class_name: str)`

删除一个流程类定义。

从系统中移除一个流程类蓝图。 不会影响
正在运行的流程实例。

**参数：**

`class_name`：要删除的流程类名称

**示例：**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

获取流程定义。

获取完整的流程配置，包括其类名、
描述和参数。

**参数：**

`id`: 流程标识符

**返回值：** dict: 流程定义对象

**示例：**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

获取流程类定义。

获取流程类的蓝图定义，包括其配置模式和服务绑定。


**参数：**

`class_name`: 流程类名称

**返回值：** dict: 流程类定义对象

**示例：**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

获取一个异步流程实例客户端。

返回一个客户端，用于与特定流程的服务进行交互（代理、RAG、查询、嵌入等）。


**参数：**

`flow_id`: 流程标识符

**返回值：** AsyncFlowInstance: 用于特定流程操作的客户端

**示例：**

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

列出所有流程标识符。

获取系统中当前部署的所有流程的ID。

**返回值:** list[str]: 流程标识符列表

**示例:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

列出所有流程类名称。

获取系统中所有可用流程类（蓝图）的名称。

**返回值:** list[str]: 流程类名称列表

**示例:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

创建或更新一个流程类定义。

存储一个流程类蓝图，该蓝图可用于实例化流程。

**参数：**

`class_name`: 流程类名称
`definition`: 流程类定义对象

**示例：**

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

异步向网关API发送HTTP POST请求。

用于向TrustGraph API发送经过身份验证的请求的内部方法。

**参数：**

`path`: API端点路径（相对于基本URL）
`request_data`: 请求负载字典

**返回值：** dict: 来自API的响应对象

**引发：**

`ProtocolException`：如果 HTTP 状态码不是 200 或响应不是有效的 JSON
`ApplicationException`：如果 API 返回错误响应

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

启动一个新的流程实例。

从指定的流程类定义创建并启动一个流程。


**参数：**

`class_name`：用于创建实例的流程类名称
`id`：新流程实例的标识符
`description`：流程的易于理解的描述
`parameters`：流程的可选配置参数

**示例：**

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

停止正在运行的流程。

停止并移除一个流程实例，释放其资源。

**参数：**

`id`: 要停止的流程标识符

**示例：**

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

异步流程实例客户端。

提供对流程范围内的服务的异步/等待访问，包括代理、
RAG 查询、嵌入和图查询。所有操作返回完整的
响应（非流式传输）。

注意：对于流式传输支持，请使用 AsyncSocketFlowInstance。

### 方法

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

初始化异步流程实例。

**参数：**

`flow`: 父级 AsyncFlow 客户端
`flow_id`: 流程标识符

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

执行代理操作（非流式传输）。

运行代理以回答问题，可以选择使用对话状态和
历史记录。在代理完成处理后，返回完整的响应。


注意：此方法不支持流式传输。对于代理的实时想法和
观察结果，请使用 AsyncSocketFlowInstance.agent()。

**参数：**

`question`: 用户问题或指令
`user`: 用户标识符
`state`: 可选的状态字典，用于对话上下文
`group`: 可选的组标识符，用于会话管理
`history`: 可选的对话历史记录列表
`**kwargs`: 额外的特定于服务的参数

**返回值：** dict: 完整的代理响应，包括答案和元数据

**示例：**

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

执行基于文档的 RAG 查询（非流式）。

使用文档嵌入进行检索增强生成。
通过语义搜索检索相关的文档片段，然后根据检索到的文档生成
一个完整的响应。返回完整的响应。

注意：此方法不支持流式传输。对于流式 RAG 响应，
请使用 AsyncSocketFlowInstance.document_rag()。

**参数：**

`query`: 用户查询文本
`user`: 用户标识符
`collection`: 包含文档的集合标识符
`doc_limit`: 要检索的最大文档片段数量（默认为 10）
`**kwargs`: 额外的特定于服务的参数

**返回值：** str: 基于文档数据的完整生成的响应

**示例：**

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

为输入文本生成嵌入向量。

将文本转换为数值向量表示，使用流程配置的嵌入模型。适用于语义搜索和相似度
比较。


**参数：**

`texts`: 要嵌入的输入文本列表
`**kwargs`: 额外的特定于服务的参数

**返回值：** dict: 包含嵌入向量的响应

**示例：**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

用于语义实体搜索的图嵌入查询。

对图实体嵌入执行语义搜索，以查找与输入文本最相关的实体。返回按相似度排序的实体。


**参数：**

`text`: 用于语义搜索的查询文本
`user`: 用户标识符
`collection`: 包含图嵌入的集合标识符
`limit`: 要返回的最大结果数（默认为：10）
`**kwargs`: 额外的特定于服务的参数

**返回值：** dict: 包含按相似度排序的实体匹配结果，以及相似度分数。

**示例：**

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

执行基于图的 RAG 查询（非流式）。

使用知识图谱数据执行检索增强生成。
识别相关的实体及其关系，然后生成一个
基于图结构的回应。返回完整的响应。

注意：此方法不支持流式传输。对于流式 RAG 响应，
请使用 AsyncSocketFlowInstance.graph_rag()。

**参数：**

`query`: 用户查询文本
`user`: 用户标识符
`collection`: 包含知识图谱的集合标识符
`max_subgraph_size`: 每个子图中最大三元组数（默认：1000）
`max_subgraph_count`: 要检索的最大子图数量（默认：5）
`max_entity_distance`: 实体扩展的最大图距离（默认：3）
`**kwargs`: 额外的特定于服务的参数

**返回值：** str: 基于图数据生成的完整响应

**示例：**

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

向作用域为流程的服务发送请求。

用于在当前流程实例中调用服务的内部方法。

**参数：**

`service`: 服务名称（例如，"agent", "graph-rag", "triples"）
`request_data`: 服务请求负载

**返回值：** dict: 服务响应对象

**抛出异常：**

`ProtocolException`: 如果请求失败或响应无效
`ApplicationException`: 如果服务返回错误

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

查询用于结构化数据语义搜索的行嵌入。

在行索引嵌入上执行语义搜索，以查找其索引字段值与输入文本最相似的行。 允许
对结构化数据进行模糊/语义匹配。


**参数：**

`text`: 用于语义搜索的查询文本。
`schema_name`: 要搜索的模式名称。
`user`: 用户标识符（默认值："trustgraph"）。
`collection`: 集合标识符（默认值："default"）。
`index_name`: 可选的索引名称，用于将搜索限制到特定的索引。
`limit`: 要返回的最大结果数量（默认值：10）。
`**kwargs`: 额外的特定于服务的参数。

**返回值:** dict: 包含匹配项的响应，包含 index_name、index_value、text 和 score。

**示例:**

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

在存储的行上执行 GraphQL 查询。

使用 GraphQL 语法查询结构化数据行。支持使用变量和命名操作的复杂查询。


**参数：**

`query`: GraphQL 查询字符串
`user`: 用户标识符
`collection`: 包含行的集合标识符
`variables`: 可选的 GraphQL 查询变量
`operation_name`: 用于多操作查询的可选操作名称
`**kwargs`: 额外的特定于服务的参数

**返回值：** dict: 包含数据和/或错误的 GraphQL 响应

**示例：**

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

生成文本补全（非流式）。

根据系统提示和用户提示，从大型语言模型生成文本回复。
返回完整的回复文本。

注意：此方法不支持流式传输。对于流式文本生成，
请使用 AsyncSocketFlowInstance.text_completion()。

**参数：**

`system`: 定义大型语言模型行为的系统提示。
`prompt`: 用户提示或问题。
`**kwargs`: 额外的特定于服务的参数。

**返回值：** str: 完整的生成文本回复。

**示例：**

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

使用模式匹配查询 RDF 三元组。

搜索与指定的 subject（主体）、predicate（谓词）和/或
object（对象）模式匹配的三元组。 模式使用 None 作为通配符来匹配任何值。

**参数：**

`s`: Subject（主体）模式（None 表示通配符）
`p`: Predicate（谓词）模式（None 表示通配符）
`o`: Object（对象）模式（None 表示通配符）
`user`: 用户标识符（None 表示所有用户）
`collection`: Collection（集合）标识符（None 表示所有集合）
`limit`: 返回的三元组的最大数量（默认：100）
`**kwargs`: 额外的特定于服务的参数

**返回值：** dict: 包含匹配的三元组的响应

**示例：**

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

同步 WebSocket 客户端，用于流式操作。

提供了对基于 WebSocket 的 TrustGraph 服务的同步接口，
通过使用同步生成器包装异步 WebSocket 库，以提高易用性。
支持从代理接收流式响应、RAG 查询和文本补全。

注意：这是一个围绕异步 WebSocket 操作的同步包装器。对于
真正的异步支持，请使用 AsyncSocketClient。

### 方法

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

初始化同步 WebSocket 客户端。

**参数：**

`url`：TrustGraph API 的基本 URL（HTTP/HTTPS 将转换为 WS/WSS）
`timeout`：WebSocket 超时时间（以秒为单位）
`token`：可选的用于身份验证的 bearer token

### `close(self) -> None`

关闭 WebSocket 连接。

注意：在异步代码中，清理由上下文管理器自动处理。

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

获取用于 WebSocket 流式操作的 flow 实例。

**参数：**

`flow_id`：Flow 标识符

**返回值：** SocketFlowInstance：具有流式方法的 Flow 实例

**示例：**

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

同步 WebSocket 流程实例，用于流式操作。

它提供与 REST FlowInstance 相同的接口，但具有基于 WebSocket 的
流式支持，用于实时响应。 所有方法都支持一个可选的
`streaming` 参数，以启用增量结果交付。

### 方法

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

初始化 socket 流程实例。

**参数：**

`client`: 父 SocketClient
`flow_id`: 流程标识符

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

执行一个支持流式传输的代理操作。

代理可以执行涉及工具使用的多步骤推理。 即使当
streaming=False 时，此方法也会始终
返回流式传输的分块（想法、观察结果、答案），以显示代理的推理过程。

**参数：**

`question`: 用户问题或指令
`user`: 用户标识符
`state`: 可选的状态字典，用于具有状态的对话
`group`: 可选的组标识符，用于多用户环境
`history`: 可选的对话历史记录，以消息字典列表的形式
`streaming`: 启用流式传输模式（默认：False）
`**kwargs`: 传递给代理服务的其他参数

**返回值：** Iterator[StreamingChunk]: 代理的想法、观察结果和答案的流

**示例：**

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

执行具有可解释性支持的代理操作。

同时流式传输内容块（AgentThought、AgentObservation、AgentAnswer）
和溯源事件（ProvenanceEvent）。溯源事件包含 URI，
可以使用 ExplainabilityClient 获取有关代理推理过程的详细信息。


代理跟踪信息包括：
Session：初始问题和会话元数据
Iterations：每个思考/行动/观察周期
Conclusion：最终答案

**参数：**

`question`：用户问题或指令
`user`：用户标识符
`collection`：用于存储溯源信息的集合标识符
`state`：可选的状态字典，用于有状态的对话
`group`：可选的组标识符，用于多用户上下文
`history`：可选的对话历史记录，以消息字典列表的形式
`**kwargs`：传递给代理服务的其他参数
`Yields`：
`Union[StreamingChunk, ProvenanceEvent]`：代理块和溯源事件

**示例：**

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

使用语义相似度查询文档块。

**参数：**

`text`: 用于语义搜索的查询文本
`user`: 用户/键空间标识符
`collection`: 集合标识符
`limit`: 最大结果数量（默认为：10）
`**kwargs`: 传递给服务的其他参数

**返回值：** dict: 包含匹配文档块的 chunk_ids 的查询结果

**示例：**

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

执行基于文档的 RAG 查询，并可选择启用流式传输。

使用向量嵌入来查找相关的文档片段，然后使用 LLM 生成
响应。流式模式逐步提供结果。

**参数：**

`query`: 自然语言查询
`user`: 用户/键空间标识符
`collection`: 集合标识符
`doc_limit`: 要检索的最大文档片段数（默认为：10）
`streaming`: 启用流式模式（默认为：False）
`**kwargs`: 传递给服务的其他参数

**返回值：** Union[str, Iterator[str]]: 完整的响应或文本片段的流

**示例：**

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

执行支持可解释性的基于文档的 RAG 查询。

同时流式传输内容块（RAGChunk）和溯源事件（ProvenanceEvent）。
溯源事件包含 URI，可以使用 ExplainabilityClient 获取详细信息，了解响应的生成方式。


文档 RAG 跟踪信息包括：
问题：用户的查询
探索：从文档存储中检索到的块（chunk_count）
综合：生成的答案

**参数：**

`query`：自然语言查询
`user`：用户/键空间标识符
`collection`：集合标识符
`doc_limit`：要检索的最大文档块数（默认：10）
`**kwargs`：传递给服务的其他参数
`Yields`：
`Union[RAGChunk, ProvenanceEvent]`：内容块和溯源事件

**示例：**

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

为一个或多个文本生成向量嵌入。

**参数：**

`texts`: 要进行嵌入的输入文本列表。
`**kwargs`: 传递给服务的其他参数。

**返回值：** dict: 包含向量的响应（每个输入文本对应一个向量集合）。

**示例：**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

使用语义相似度查询知识图谱实体。

**参数：**

`text`: 用于语义搜索的查询文本
`user`: 用户/命名空间标识符
`collection`: 集合标识符
`limit`: 最大结果数量（默认为：10）
`**kwargs`: 传递给服务的附加参数

**返回值：** dict: 包含相似实体的查询结果

**示例：**

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

执行基于图的关系检索增强生成（RAG）查询，并可选择启用流式传输。

使用知识图谱结构来查找相关上下文，然后使用大型语言模型（LLM）生成
响应。流式模式逐步提供结果。

**参数：**

`query`：自然语言查询
`user`：用户/键空间标识符
`collection`：集合标识符
`max_subgraph_size`：子图中最大三元组数量（默认为：1000）
`max_subgraph_count`：最大子图数量（默认为：5）
`max_entity_distance`：最大遍历深度（默认为：3）
`streaming`：启用流式模式（默认为：False）
`**kwargs`：传递给服务的其他参数

**返回值：** Union[str, Iterator[str]]：完整的响应或文本块的流

**示例：**

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

执行具有可解释性支持的基于图的 RAG 查询。

同时流式传输内容块（RAGChunk）和溯源事件（ProvenanceEvent）。
溯源事件包含 URI，可以使用 ExplainabilityClient 获取详细信息，了解响应的生成方式。


**参数：**

`query`: 自然语言查询
`user`: 用户/键空间标识符
`collection`: 集合标识符
`max_subgraph_size`: 子图中最大三元组数量（默认：1000）
`max_subgraph_count`: 最大子图数量（默认：5）
`max_entity_distance`: 最大遍历深度（默认：3）
`**kwargs`: 传递给服务的其他参数
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: 内容块和溯源事件

**示例：**

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

执行模型上下文协议 (MCP) 工具。

**参数：**

`name`: 工具名称/标识符
`parameters`: 工具参数字典
`**kwargs`: 传递给服务的附加参数

**返回值：** dict: 工具执行结果

**示例：**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

执行一个带有可选流式的提示模板。

**参数：**

`id`: 提示模板标识符
`variables`: 变量名到值的映射字典
`streaming`: 启用流式模式 (默认: False)
`**kwargs`: 传递给服务的附加参数

**返回值：** Union[str, Iterator[str]]: 完整的响应或文本块的流

**示例：**

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

使用语义相似性在索引字段上查询行数据。

查找其索引字段值在语义上与
输入文本相似的行，使用向量嵌入。这实现了对结构化数据的模糊/语义匹配。


**参数：**

`text`: 用于语义搜索的查询文本
`schema_name`: 要搜索的模式名称
`user`: 用户/键空间标识符（默认为："trustgraph"）
`collection`: 集合标识符（默认为："default"）
`index_name`: 可选的索引名称，用于将搜索限制到特定索引
`limit`: 最大结果数量（默认为：10）
`**kwargs`: 传递给服务的其他参数

**返回值：** dict: 查询结果，包含匹配项，其中包含 index_name、index_value、text 和 score

**示例：**

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

执行针对结构化行的 GraphQL 查询。

**参数：**

`query`: GraphQL 查询字符串
`user`: 用户/键空间标识符
`collection`: 集合标识符
`variables`: 可选的查询变量字典
`operation_name`: 用于多操作文档的可选操作名称
`**kwargs`: 传递给服务的附加参数

**返回值：** dict: 包含数据、错误和/或扩展的 GraphQL 响应

**示例：**

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

执行带有可选流的文本补全。

**参数：**

`system`: 定义助手行为的系统提示。
`prompt`: 用户提示/问题。
`streaming`: 启用流模式（默认：False）。
`**kwargs`: 传递给服务的附加参数。

**返回值：** Union[str, Iterator[str]]: 完整的响应或文本块的流。

**示例：**

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

使用模式匹配查询知识图谱三元组。

**参数：**

`s`: 主体过滤器 - URI 字符串、Term 字典，或 None 表示通配符
`p`: 谓语过滤器 - URI 字符串、Term 字典，或 None 表示通配符
`o`: 对象过滤器 - URI/字面量字符串、Term 字典，或 None 表示通配符
`g`: 命名图过滤器 - URI 字符串或 None 表示所有图
`user`: 用户/键空间标识符（可选）
`collection`: 集合标识符（可选）
`limit`: 返回的最大结果数（默认：100）
`**kwargs`: 传递给服务的其他参数

**返回值：** List[Dict]: 匹配的三元组列表，以原始格式返回

**示例：**

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

使用流式批处理查询知识图谱三元组。

随着三元组的到达，它会产生一批批的三元组，从而减少获得第一个结果所需的时间，并降低大型结果集的内存开销。


**参数：**

`s`: 主体过滤器 - URI 字符串、Term 字典，或 None 表示通配符
`p`: 谓语过滤器 - URI 字符串、Term 字典，或 None 表示通配符
`o`: 对象过滤器 - URI/字面量字符串、Term 字典，或 None 表示通配符
`g`: 命名图过滤器 - URI 字符串或 None 表示所有图
`user`: 用户/键空间标识符（可选）
`collection`: 集合标识符（可选）
`limit`: 要返回的最大结果数（默认：100）
`batch_size`: 每批三元组数（默认：20）
`**kwargs`: 传递给服务的其他参数
`Yields`:
`List[Dict]`: 以线格式的三元组批次

**示例：**

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

异步 WebSocket 客户端

### 方法

### `__init__(self, url: str, timeout: int, token: str | None)`

初始化 self。请参考 help(type(self)) 以获取准确的签名。

### `aclose(self)`

关闭 WebSocket 连接

### `flow(self, flow_id: str)`

获取用于 WebSocket 操作的异步流程实例


--

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

异步 WebSocket 流实例

### 方法

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

初始化 self。请参阅 help(type(self)) 以获取准确的签名。

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

带有可选流的 Agent

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

带有可选流的文档 RAG

### `embeddings(self, texts: list, **kwargs)`

生成文本嵌入

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

用于语义搜索的图嵌入查询

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

带有可选流的图 RAG

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

执行 MCP 工具

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

带有可选流的提示执行

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

用于结构化数据的语义搜索的行嵌入查询

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

对结构化行的 GraphQL 查询

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

带有可选流的文本补全

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

三元模式查询


--

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

从值构建线性的 Term 字典。

自动检测规则（当 term_type 为 None 时）：
  已经是一个带有 't' 键的字典 -> 保持原样（已经是 Term）
  以 http://, https://, urn: 开头 -> IRI
  包含在 <> 中（例如，<http://...>）-> IRI（去除尖角括号）
  其他任何内容 -> 文本

**参数：**

`value`: Term 值（字符串、字典或 None）
`term_type`: 'iri'、'literal' 或 None 中的一个，用于自动检测
`datatype`: 文本对象的类型（例如，xsd:integer）
`language`: 文本对象的语言标签（例如，en）

**返回值：** dict: 线性的 Term 字典，如果值是 None 则返回 None


--

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

用于导入/导出的同步批量操作客户端。

通过 WebSocket 提供高效的大数据集批量数据传输。
使用同步生成器包装异步 WebSocket 操作，以提高易用性。

注意：要获得真正的异步支持，请使用 AsyncBulkClient。

### 方法

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

初始化同步批量客户端。

**参数：**

`url`：TrustGraph API 的基本 URL（HTTP/HTTPS 将转换为 WS/WSS）
`timeout`：WebSocket 超时时间（以秒为单位）
`token`：可选的用于身份验证的 bearer token

### `close(self) -> None`

关闭连接

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

从流程中批量导出文档嵌入。

通过 WebSocket 流式传输高效下载所有文档块嵌入。

**参数：**

`flow`：流程标识符
`**kwargs`：附加参数（为未来使用保留）

**返回值：** Iterator[Dict[str, Any]]: 嵌入字典的流

**示例：**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

从流程中批量导出实体上下文。

通过 WebSocket 流式传输高效下载所有实体上下文信息。

**参数：**

`flow`: 流程标识符
`**kwargs`: 附加参数（预留给未来使用）

**返回值：** Iterator[Dict[str, Any]]: 上下文字典的流

**示例：**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

从流程中批量导出图嵌入。

能够高效地通过 WebSocket 流式传输下载所有图实体嵌入。

**参数：**

`flow`: 流程标识符
`**kwargs`: 附加参数（预留给未来使用）

**返回值：** Iterator[Dict[str, Any]]: 嵌入字典的流

**示例：**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

从流程中批量导出 RDF 三元组。

能够高效地通过 WebSocket 流式传输下载所有三元组。

**参数：**

`flow`: 流程标识符
`**kwargs`: 附加参数（预留给未来使用）

**返回值：** Iterator[Triple]: 三元组对象的流

**示例：**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

将文档嵌入批量导入到流程中。

通过 WebSocket 流式传输高效地上传文档分块嵌入，
用于文档检索增强生成 (RAG) 查询。

**参数：**

`flow`: 流程标识符
`embeddings`: 产生嵌入字典的迭代器
`**kwargs`: 附加参数（预留给未来使用）

**示例：**

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

将实体上下文批量导入到流程中。

通过 WebSocket 流式传输高效地上传实体上下文信息。
实体上下文为图实体提供额外的文本上下文，
以提高 RAG 的性能。

**参数：**

`flow`: 流程标识符
`contexts`: 产生上下文字典的迭代器
`metadata`: 包含 id、元数据、用户、集合的元数据字典
`batch_size`: 每个批次的上下文数量（默认为 100）
`**kwargs`: 附加参数（为未来使用保留）

**示例：**

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

批量将图嵌入向量导入到流程中。

通过 WebSocket 流式传输高效地上传图实体嵌入向量。

**参数：**

`flow`: 流程标识符
`embeddings`: 产生嵌入字典的迭代器
`**kwargs`: 附加参数（预留给未来使用）

**示例：**

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

批量将结构化行导入到流程中。

通过 WebSocket 流式传输高效地上传结构化数据行，
用于 GraphQL 查询。

**参数：**

`flow`: 流程标识符
`rows`: 产生行字典的迭代器
`**kwargs`: 附加参数（为未来使用保留）

**示例：**

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

批量将 RDF 三元组导入到流程中。

通过 WebSocket 流式传输高效地上传大量三元组。

**参数：**

`flow`: 流程标识符
`triples`: 产生 Triple 对象的迭代器
`metadata`: 包含 id、元数据、用户、集合的元数据字典
`batch_size`: 每个批次的元组数量（默认为 100）
`**kwargs`: 其他参数（保留用于未来使用）

**示例：**

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

异步批量操作客户端

### 方法

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。

### `aclose(self) -> None`

关闭连接

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

通过 WebSocket 批量导出文档嵌入

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

通过 WebSocket 批量导出实体上下文

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

通过 WebSocket 批量导出图嵌入

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

通过 WebSocket 批量导出三元组

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

通过 WebSocket 批量导入文档嵌入

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

通过 WebSocket 批量导入实体上下文

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

通过 WebSocket 批量导入图嵌入

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

通过 WebSocket 批量导入行

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

通过 WebSocket 批量导入三元组


--

## `Metrics`

```python
from trustgraph.api import Metrics
```

同步指标客户端

### 方法

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。

### `get(self) -> str`

获取 Prometheus 指标，以文本形式


--

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

异步指标客户端

### 方法

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。

### `aclose(self) -> None`

关闭连接

### `get(self) -> str`

获取 Prometheus 指标（以文本形式）


--

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

客户端，用于获取可解释性实体，并处理最终一致性。

使用静默检测：获取、等待、再次获取、比较。
如果结果相同，则数据稳定。

### 方法

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

初始化可解释性客户端。

**参数:**

`flow_instance`: 用于查询三元组的 SocketFlowInstance。
`retry_delay`: 重试之间的延迟（以秒为单位）（默认值：0.2）。
`max_retries`: 最大重试次数（默认值：10）。

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

检测会话是 GraphRAG 还是 Agent 类型。

**参数:**

`session_uri`: 会话/问题的 URI。
`graph`: 命名图。
`user`: 用户/键空间标识符。
`collection`: 集合标识符。

**返回值:** "graphrag" 或 "agent"。

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

从会话 URI 开始，获取完整的 Agent 跟踪。

遵循溯源链：问题 -> 分析(s) -> 结论。

**参数:**

`session_uri`: Agent 会话/问题的 URI。
`graph`: 命名图（默认值：urn:graph:retrieval）。
`user`: 用户/键空间标识符。
`collection`: 集合标识符。
`api`: 用于图书管理员访问的 TrustGraph Api 实例（可选）。
`max_content`: 结论的最大内容长度。

**返回值:** 包含问题、迭代（分析列表）和结论实体的字典。

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

从问题 URI 开始，获取完整的 DocumentRAG 跟踪。

遵循溯源链：
    问题 -> 关联 -> 探索 -> 综合。

**参数:**

`question_uri`: 问题实体 URI。
`graph`: 命名图（默认值：urn:graph:retrieval）。
`user`: 用户/键空间标识符。
`collection`: 集合标识符。
`api`: 用于图书管理员访问的 TrustGraph Api 实例（可选）。
`max_content`: 综合的最大内容长度。

**返回值:** 包含问题、关联、探索和综合实体的字典。

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

通过文档 URI 从图书管理员处获取内容。

**参数:**

`document_uri`: 图书管理员中的文档 URI。
`api`: 用于图书管理员访问的 TrustGraph Api 实例。
`user`: 用于图书管理员的用户标识符。
`max_content`: 要返回的最大内容长度。

**返回值:** 文档内容作为字符串。

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

获取边缘选择实体（由 Focus 使用）。

**参数:**

`uri`: 边缘选择 URI。
`graph`: 要查询的命名图。
`user`: 用户/键空间标识符。
`collection`: 集合标识符。

**返回值:** EdgeSelection 或如果未找到则返回 None。

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

通过 URI 获取可解释性实体，并采用最终一致性处理。

使用静默检测：
1. 获取 URI 对应的三元组
2. 如果结果为零，则重试
3. 如果结果不为零，则等待并再次获取
4. 如果结果相同，则数据稳定 - 解析并返回
5. 如果结果不同，则数据仍在写入 - 重试

**参数：**

`uri`: 要获取的实体 URI
`graph`: 查询的命名图 (例如，"urn:graph:retrieval")
`user`: 用户/密钥空间标识符
`collection`: 集合标识符

**返回值：** ExplainEntity 子类，如果未找到则返回 None

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

获取 Focus 实体及其所有边选择。

**参数：**

`uri`: Focus 实体 URI
`graph`: 查询的命名图
`user`: 用户/密钥空间标识符
`collection`: 集合标识符

**返回值：** 包含填充的 edge_selections 的 Focus 对象，如果未找到则返回 None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

从问题 URI 开始，获取完整的 GraphRAG 跟踪。

遵循溯源链：问题 -> 关联 -> 探索 -> Focus -> 综合

**参数：**

`question_uri`: 问题实体 URI
`graph`: 命名图 (默认: urn:graph:retrieval)
`user`: 用户/密钥空间标识符
`collection`: 集合标识符
`api`: 用于 librarian 访问的 TrustGraph Api 实例 (可选)
`max_content`: 综合的最大内容长度

**返回值：** 包含 question、grounding、exploration、focus、synthesis 实体的字典

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

列出集合中的所有可解释性会话 (问题)。

**参数：**

`graph`: 命名图 (默认: urn:graph:retrieval)
`user`: 用户/密钥空间标识符
`collection`: 集合标识符
`limit`: 要返回的会话的最大数量

**返回值：** 按时间戳排序的 Question 实体列表 (最新在前)

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

解决边三元组的所有组件的标签。

**参数：**

`edge`: 包含 "s"、"p"、"o" 键的字典
`user`: 用户/密钥空间标识符
`collection`: 集合标识符

**返回值：** (s_label, p_label, o_label) 元组

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

使用缓存，为 URI 解析 rdfs:label。

**参数：**

`uri`: 要获取标签的 URI
`user`: 用户/密钥空间标识符
`collection`: 集合标识符

**返回值：** 如果找到，则返回标签，否则返回 URI 本身


--

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

可解释性实体的基类。

**字段：**

`uri`: <class 'str'>
`entity_type`: <class 'str'>

### 方法

### `__init__(self, uri: str, entity_type: str = '') -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

## `Question`

```python
from trustgraph.api import Question
```

问题实体 - 用户启动会话的查询。

**字段：**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`query`: <class 'str'>
`timestamp`: <class 'str'>
`question_type`: <class 'str'>

### 方法

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

初始化 self。请参阅 help(type(self)) 以获取准确的签名。


--

## `Exploration`

```python
from trustgraph.api import Exploration
```

探索实体 - 从知识库中检索到的边/块。

**字段：**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`edge_count`: <class 'int'>
`chunk_count`: <class 'int'>
`entities`: typing.List[str]

### 方法

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

## `Focus`

```python
from trustgraph.api import Focus
```

关注实体 - 使用 LLM 推理选择的边（仅限 GraphRAG）。

**字段：**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`selected_edge_uris`: typing.List[str]
`edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### 方法

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

初始化 self。请参阅 help(type(self)) 以获取准确的签名。


--

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

综合实体 - 最终答案。

**字段：**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### 方法

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

## `Analysis`

```python
from trustgraph.api import Analysis
```

分析实体 - 一个思考/行动/观察循环（仅限Agent）。

**字段：**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`action`: <class 'str'>
`arguments`: <class 'str'>
`thought`: <class 'str'>
`observation`: <class 'str'>

### 方法

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

结论实体 - 最终答案（仅限代理）。

**字段：**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### 方法

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

初始化 self。请参阅 help(type(self)) 以获取准确的签名。


--

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

从 GraphRAG Focus 步骤中选择的边，并附带推理。

**字段：**

`uri`: <class 'str'>
`edge`: typing.Dict[str, str] | None
`reasoning`: <class 'str'>

### 方法

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

将线格式的三元组转换为 (s, p, o) 元组。


--

### `extract_term_value(term: Dict[str, Any]) -> Any`

从线格式的 Term 字典中提取值。


--

## `Triple`

```python
from trustgraph.api import Triple
```

RDF三元组，表示知识图谱中的一条陈述。

**字段：**

`s`: <class 'str'>
`p`: <class 'str'>
`o`: <class 'str'>

### 方法

### `__init__(self, s: str, p: str, o: str) -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

## `Uri`

```python
from trustgraph.api import Uri
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

从给定的对象创建一个新的字符串对象。如果指定了 encoding 或
errors，则该对象必须公开一个数据缓冲区，该缓冲区将使用给定的编码和错误处理程序进行解码。
否则，返回 object.__str__() 的结果（如果已定义），或者 repr(object)。
encoding 默认为 'utf-8'。
errors 默认为 'strict'。

### 方法

### ⟦CODE_0⟧

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

从给定的对象创建一个新的字符串对象。如果指定了 encoding 或
errors，则该对象必须公开一个数据缓冲区，该缓冲区将使用给定的编码和错误处理程序进行解码。
否则，返回 object.__str__() 的结果（如果已定义），或者 repr(object)。
encoding 默认为 'utf-8'。
errors 默认为 'strict'。

### 方法

### ⟦CODE_0⟧

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

配置键标识符。

**字段：**

`type`: <class 'str'>
`key`: <class 'str'>

### 方法

### `__init__(self, type: str, key: str) -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

配置键值对。

**字段：**

`type`: <class 'str'>
`key`: <class 'str'>
`value`: <class 'str'>

### 方法

### `__init__(self, type: str, key: str, value: str) -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

文档库中一个文档的元数据。

**属性：**

`parent_id: Parent document ID for child documents (empty for top`: level docs)

**字段：**

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

### 方法

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

正在处理的文档的元数据。

**字段：**

`id`: <class 'str'>
`document_id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`flow`: <class 'str'>
`user`: <class 'str'>
`collection`: <class 'str'>
`tags`: typing.List[str]

### 方法

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

初始化 self。有关准确签名的信息，请参阅 help(type(self))。


--

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

数据的元数据。

集合提供逻辑分组和隔离，用于文档和
知识图谱数据。

**属性：**

`name: Human`: 可读的集合名称

**字段：**

`user`: <class 'str'>
`collection`: <class 'str'>
`name`: <class 'str'>
`description`: <class 'str'>
`tags`: typing.List[str]

### 方法

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

初始化 self。请参阅 help(type(self)) 以获取准确的签名。


--

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

流式响应分块的基础类。

用于基于 WebSocket 的流式操作，其中响应以增量方式传递，
并在生成时交付。

**字段：**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>

### 方法

### `__init__(self, content: str, end_of_message: bool = False) -> None`

初始化 self。请参阅 help(type(self)) 以获取准确的签名。


--

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

代理的推理/思考过程片段。

代表代理在执行期间的内部推理或规划步骤。
这些片段展示了代理如何思考问题。

**字段：**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### 方法

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

初始化 self。请参考 help(type(self)) 以获取准确的签名。


--

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

代理工具执行观察块。

表示执行工具或操作的结果或观察结果。
这些块显示了代理通过使用工具学到的内容。

**字段：**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### 方法

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

初始化 self。请参阅 help(type(self)) 以获取准确的签名。


--

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

Agent final answer chunk.

Represents the agent's final response to the user's query after completing
its reasoning and tool use.

**Attributes:**

`chunk_type: Always "final`: answer"

**Fields:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_dialog`: <class 'bool'>

### Methods

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

Initialize self.  See help(type(self)) for accurate signature.


--

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

RAG（检索增强生成）流式传输块。

用于从图 RAG、文档 RAG、文本补全以及其他生成服务中流式传输响应。


**字段：**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_stream`: <class 'bool'>
`error`: typing.Dict[str, str] | None

### 方法

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

初始化 self。有关准确的签名，请参阅 help(type(self))。


--

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

可解释性的溯源事件。

在启用可解释模式时，GraphRAG 查询期间会发出。
每个事件代表在查询处理过程中创建的溯源节点。

**字段：**

`explain_id`: <class 'str'>
`explain_graph`: <class 'str'>
`event_type`: <class 'str'>

### 方法

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

初始化 self。请参阅 help(type(self)) 以获取准确的签名。


--

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

当 WebSocket 协议出现错误时触发。


--

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

TrustGraph 服务所有错误的基类。


--

## `AgentError`

```python
from trustgraph.api import AgentError
```

代理服务错误


--

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

配置服务错误


--

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

文档检索错误


--

## `FlowError`

```python
from trustgraph.api import FlowError
```

流程管理错误


--

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

API 网关错误


--

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

图表 RAG 检索错误


--

## `LLMError`

```python
from trustgraph.api import LLMError
```

LLM 服务错误


--

## `LoadError`

```python
from trustgraph.api import LoadError
```

数据加载错误


--

## `LookupError`

```python
from trustgraph.api import LookupError
```

查找/搜索错误


--

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

自然语言处理查询服务错误


--

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

行查询服务错误


--

## `RequestError`

```python
from trustgraph.api import RequestError
```

请求处理错误


--

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

结构化查询服务错误


--

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

意外/未知的错误


--

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

TrustGraph 服务所有错误的基类。


--
