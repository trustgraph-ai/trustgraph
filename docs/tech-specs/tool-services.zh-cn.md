---
layout: default
title: "工具服务：动态可插拔的代理工具"
parent: "Chinese (Beta)"
---

# 工具服务：动态可插拔的代理工具

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 状态

已实现

## 概述

本规范定义了一种称为“工具服务”的动态可插拔代理工具的机制。 与现有的内置工具类型（`KnowledgeQueryImpl`，`McpToolImpl`等）不同，工具服务允许通过以下方式引入新的工具：

1. 部署一个新的基于Pulsar的服务
2. 添加一个配置描述符，该描述符告诉代理如何调用它

这实现了可扩展性，而无需修改核心代理响应框架。

## 术语

| 术语 | 定义 |
|------|------------|
| **内置工具** | 具有硬编码实现的现有工具类型，位于`tools.py` |
| **工具服务** | 可以作为代理工具调用的Pulsar服务，由服务描述符定义 |
| **工具** | 引用工具服务的已配置实例，暴露给代理/LLM |

这是一个两层模型，类似于MCP工具：
MCP：MCP服务器定义工具接口 → 工具配置引用它
工具服务：工具服务定义Pulsar接口 → 工具配置引用它

## 背景：现有工具

### 内置工具实现

当前，工具在`trustgraph-flow/trustgraph/agent/react/tools.py`中定义，并具有类型化的实现：

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

每种工具类型：
具有一个硬编码的 Pulsar 服务，它会调用该服务（例如：`graph-rag-request`）
知道要调用的客户端上的确切方法（例如：`client.rag()`）
在实现中定义了类型化的参数

### 工具注册 (service.py:105-214)

工具从配置文件中加载，其中有一个 `type` 字段，它映射到实现：

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## 架构

### 两层模型

#### 第一层：工具服务描述器

一个工具服务定义了 Pulsar 服务接口。它声明：
用于请求/响应的 Pulsar 队列
它需要的来自使用它的工具的配置参数

```json
{
  "id": "custom-rag",
  "request-queue": "non-persistent://tg/request/custom-rag",
  "response-queue": "non-persistent://tg/response/custom-rag",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

一种不需要任何配置参数的工具服务：

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### 第二层：工具描述

一个工具引用一个工具服务，并提供：
配置参数值（满足服务的要求）
代理的工具元数据（名称、描述）
LLM 的参数定义

```json
{
  "type": "tool-service",
  "name": "query-customers",
  "description": "Query the customer knowledge base",
  "service": "custom-rag",
  "collection": "customers",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about customers"
    }
  ]
}
```

多个工具可以使用不同的配置来引用相同的服务：

```json
{
  "type": "tool-service",
  "name": "query-products",
  "description": "Query the product knowledge base",
  "service": "custom-rag",
  "collection": "products",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about products"
    }
  ]
}
```

### 请求格式

当一个工具被调用时，发送给工具服务的请求包括：
`user`: 来自代理的请求（多租户）
`config`: 来自工具描述的 JSON 编码的配置值
`arguments`: 来自 LLM 的 JSON 编码的参数

```json
{
  "user": "alice",
  "config": "{\"collection\": \"customers\"}",
  "arguments": "{\"question\": \"What are the top customer complaints?\"}"
}
```

工具服务接收这些数据，并将其解析为字典，在 `invoke` 方法中进行处理。

### 通用工具服务实现

一个 `ToolServiceImpl` 类根据配置调用工具服务：

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.config_values = config_values  # e.g., {"collection": "customers"}
        # ...

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, self.config_values, arguments)
        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
```

## 设计决策

### 双层配置模型

工具服务遵循类似于 MCP 工具的双层模型：

1. **工具服务 (Tool Service)**：定义 Pulsar 服务接口（主题、所需的配置参数）。
2. **工具 (Tool)**：引用工具服务，提供配置值，定义 LLM 参数。

这种分离方式允许：
一个工具服务可以被多个具有不同配置的工具使用。
清晰区分服务接口和工具配置。
重用服务定义。

### 请求映射：带外壳的透传

发送到工具服务的请求是一个结构化的外壳，包含：
`user`：从代理请求中传播，用于多租户。
配置值：来自工具描述符（例如，`collection`）。
`arguments`：LLM 提供的参数，作为字典传递。

代理管理器将 LLM 的响应解析为 `act.arguments`（作为字典，`agent_manager.py:117-154`）。此字典包含在请求外壳中。

### 模式处理：无类型

请求和响应使用无类型的字典。代理级别不进行任何模式验证 - 工具服务负责验证其输入。这提供了定义新服务的最大灵活性。

### 客户端接口：直接 Pulsar 主题

工具服务使用直接的 Pulsar 主题，无需配置流。工具服务描述符指定完整的队列名称：

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

这允许服务在任何命名空间中被托管。

### 错误处理：标准错误约定

工具服务响应遵循现有的模式约定，包含一个 `error` 字段：

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

响应结构:
成功: `error` 为 `None`，响应包含结果
错误: `error` 被填充为 `type` 和 `message`

这符合现有服务模式（例如：`PromptResponse`，`QueryResponse`，`AgentResponse`）。

### 请求/响应关联

请求和响应使用 `id` 在 Pulsar 消息属性中进行关联：

请求包含 `id` 在属性中：`properties={"id": id}`
响应包含相同的 `id`：`properties={"id": id}`

这遵循代码库中使用的现有模式（例如：`agent_service.py`，`llm_service.py`）。

### 流式支持

工具服务可以返回流式响应：

具有相同 `id` 在属性中的多个响应消息
每个响应包含 `end_of_stream: bool` 字段
最终响应具有 `end_of_stream: True`

这符合 `AgentResponse` 和其他流式服务中使用的模式。

### 响应处理：字符串返回

所有现有工具都遵循相同的模式：**接收参数作为字典，将观察结果作为字符串返回**。

| 工具 | 响应处理 |
|------|------------------|
| `KnowledgeQueryImpl` | 直接返回 `client.rag()` (字符串) |
| `TextCompletionImpl` | 直接返回 `client.question()` (字符串) |
| `McpToolImpl` | 返回字符串，或如果不是字符串则返回 `json.dumps(output)` |
| `StructuredQueryImpl` | 将结果格式化为字符串 |
| `PromptImpl` | 直接返回 `client.prompt()` (字符串) |

工具服务遵循相同的约定：
服务返回一个字符串响应（观察结果）
如果响应不是字符串，则通过 `json.dumps()` 进行转换
描述符中不需要提取配置

这使描述符保持简单，并将责任放在服务上，使其为代理返回适当的文本响应。

## 配置指南

要添加一个新的工具服务，需要两个配置项：

### 1. 工具服务配置

存储在 `tool-service` 配置键下。定义了 Pulsar 队列和可用的配置参数。

| 字段 | 必需 | 描述 |
|-------|----------|-------------|
| `id` | 是 | 工具服务的唯一标识符 |
| `request-queue` | 是 | 用于请求的完整 Pulsar 主题（例如：`non-persistent://tg/request/joke`） |
| `response-queue` | 是 | 用于响应的完整 Pulsar 主题（例如：`non-persistent://tg/response/joke`） |
| `config-params` | 否 | 服务接受的配置参数数组 |

每个配置参数可以指定：
`name`: 参数名称 (必需)
`required`: 是否需要工具提供该参数 (默认: 否)

示例:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [
    {"name": "style", "required": false}
  ]
}
```

### 2. 工具配置

存储在 `tool` 配置键下。定义了代理可以使用的工具。

| 字段 | 必需 | 描述 |
|-------|----------|-------------|
| `type` | 是 | 必须是 `"tool-service"` |
| `name` | 是 | 暴露给 LLM 的工具名称 |
| `description` | 是 | 描述工具的功能（显示给 LLM）|
| `service` | 是 | 调用工具服务的 ID |
| `arguments` | 否 | LLM 的参数定义数组 |
| *(配置参数)* | 变化 | 服务定义的任何配置参数 |

每个参数可以指定：
`name`：参数名称（必需）
`type`：数据类型，例如 `"string"`（必需）
`description`：显示给 LLM 的描述（必需）

示例：
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {
      "name": "topic",
      "type": "string",
      "description": "The topic for the joke (e.g., programming, animals, food)"
    }
  ]
}
```

### 加载配置

使用 `tg-put-config-item` 加载配置：

```bash
# Load tool-service config
tg-put-config-item tool-service/joke-service < joke-service.json

# Load tool config
tg-put-config-item tool/tell-joke < tell-joke.json
```

必须重启代理服务器才能加载新的配置。

## 实现细节

### 模式

`trustgraph-base/trustgraph/schema/services/tool_service.py` 中的请求和响应类型：

```python
@dataclass
class ToolServiceRequest:
    user: str = ""           # User context for multi-tenancy
    config: str = ""         # JSON-encoded config values from tool descriptor
    arguments: str = ""      # JSON-encoded arguments from LLM

@dataclass
class ToolServiceResponse:
    error: Error | None = None
    response: str = ""       # String response (the observation)
    end_of_stream: bool = False
```

### 服务器端：DynamicToolService

基类位于 `trustgraph-base/trustgraph/base/dynamic_tool_service.py`：

```python
class DynamicToolService(AsyncProcessor):
    """Base class for implementing tool services."""

    def __init__(self, **params):
        topic = params.get("topic", default_topic)
        # Constructs topics: non-persistent://tg/request/{topic}, non-persistent://tg/response/{topic}
        # Sets up Consumer and Producer

    async def invoke(self, user, config, arguments):
        """Override this method to implement the tool's logic."""
        raise NotImplementedError()
```

### 客户端：ToolServiceImpl

在 `trustgraph-flow/trustgraph/agent/react/tools.py` 中的实现：

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        # Uses the provided queue paths directly
        # Creates ToolServiceClient on first use

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, config_values, arguments)
        return response if isinstance(response, str) else json.dumps(response)
```

### 文件

| 文件 | 目的 |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | 请求/响应模式 |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | 调用服务的客户端 |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | 服务实现的基类 |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | `ToolServiceImpl` 类 |
| `trustgraph-flow/trustgraph/agent/react/service.py` | 配置加载 |

### 示例：笑话服务

一个用 `trustgraph-flow/trustgraph/tool_service/joke/` 编写的示例服务：

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

工具服务配置：
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

工具配置：
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {"name": "topic", "type": "string", "description": "The topic for the joke"}
  ]
}
```

### 向后兼容性

现有的内置工具类型继续以不变的方式工作。
`tool-service` 是一种新的工具类型，与现有类型（`knowledge-query`、`mcp-tool`等）并存。

## 未来考虑事项

### 自定义服务

未来的增强功能可能允许服务发布自己的描述：

服务在启动时发布到已知的 `tool-descriptors` 主题。
代理订阅并动态注册工具。
实现了真正的即插即用，无需配置更改。

这超出了初始实现的范围。

## 参考文献

当前工具实现：`trustgraph-flow/trustgraph/agent/react/tools.py`
工具注册：`trustgraph-flow/trustgraph/agent/react/service.py:105-214`
代理模式：`trustgraph-base/trustgraph/schema/services/agent.py`
