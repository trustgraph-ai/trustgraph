# 工具服务：动态可插拔的代理工具

## 状态

已实现

## 概述

该规范定义了一种动态可插拔的代理工具机制，称为“工具服务”。 与现有的内置工具类型（如 `KnowledgeQueryImpl`、`McpToolImpl` 等），工具服务允许通过以下方式引入新的工具：

1.  部署一个新的基于 Pulsar 的服务
2.  添加一个配置描述符，告诉代理如何调用它

这使得无需修改核心 agent-react 框架即可实现扩展。

## 术语

| 术语 | 定义 |
|---|---|
| **内置工具** | 具有在 `tools.py` 中硬编码实现的现有工具类型 |
| **工具服务** | 一个基于 Pulsar 的服务，可以被其他工具调用 |
| **配置描述符** | 用于配置工具服务的 JSON 格式文件 |

## 实现细节

### 流程

1.  **服务启动:** 服务将自身注册到 agent，包含服务名称、队列路径等信息
2.  **工具配置:** 客户端通过加载配置描述符，动态注册服务
3.  **调用服务:**  客户端使用 `ToolServiceClient` 调用服务

### 架构

```
[客户端 (agent-react)] <-> [ToolServiceClient] <-> [服务 (dynamic_tool_service)] <-> [Pulsar 队列]
```

### 示例

```python
# 客户端 (agent-react)
async def call_service(service_name, args):
  # 从配置中获取 service_配置
  service_config = get_config(service_name)
  # 创建 ToolServiceClient
  client = ToolServiceClient(service_config)
  # 调用服务
  response = await client.call(args)
  return response
```

### 示例配置描述符

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

### 示例工具配置

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

### 示例服务实现

```python
import asyncio
import json
from trustgraph.base import dynamic_tool_service
from trustgraph.base.tool_service_client import ToolServiceClient
from trustgraph.schema.services.tool_service import ToolServiceRequest

class Processor(dynamic_tool_service.DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = await self.get_joke(topic, style)  # 假设这里调用一个 joke 库
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"

    async def get_joke(self, topic, style):
        # 这是一个占位符，实际需要调用 joke 库来获取笑话
        if topic == "programming" and style == "pun":
            return "Why did the programmer quit? Because he didn't get arrays!"
        else:
            return "I don't know any jokes right now."
```

### 例子：加载配置

```bash
# 加载工具服务配置
tg-put-config-item tool-service/joke-service < joke-service.json

# 加载工具配置
tg-put-config-item tool/tell-joke < tell-joke.json
```

### 重新启动 agent-react

`agent-react` 必须重新启动才能拾取新的配置。

## 未来考虑

### 自主宣布的服务

未来的增强可以允许服务发布自己的描述符：

-   服务将自身注册到 agent，包含服务名称、队列路径等信息
-   Agent 订阅并动态注册工具
-   这使得无需修改配置即可实现真正的可插拔性

此功能超出了初始实现范围。

## 参考

-   现有工具实现：`trustgraph-flow/trustgraph/agent/react/tools.py`
-   工具注册：`trustgraph-flow/trustgraph/agent/react/service.py:105-214`
-   agent 方案：`trustgraph-base/trustgraph/schema/services/agent.py`