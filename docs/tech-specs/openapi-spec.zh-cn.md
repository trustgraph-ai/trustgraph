---
layout: default
title: "OpenAPI 规范 - 技术规范"
parent: "Chinese (Beta)"
---

# OpenAPI 规范 - 技术规范

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 目标

创建一个全面的、模块化的 OpenAPI 3.1 规范，用于 TrustGraph REST API 网关，该规范应：
记录所有 REST 接口
使用外部 `$ref` 以实现模块化和可维护性
直接映射到消息转换器代码
提供准确的请求/响应模式

## 权威来源

API 由以下内容定义：
**消息转换器**: `trustgraph-base/trustgraph/messaging/translators/*.py`
**分派器管理器**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
**端点管理器**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## 目录结构

```
openapi/
├── openapi.yaml                          # Main entry point
├── paths/
│   ├── config.yaml                       # Global services
│   ├── flow.yaml
│   ├── librarian.yaml
│   ├── knowledge.yaml
│   ├── collection-management.yaml
│   ├── flow-services/                    # Flow-hosted services
│   │   ├── agent.yaml
│   │   ├── document-rag.yaml
│   │   ├── graph-rag.yaml
│   │   ├── text-completion.yaml
│   │   ├── prompt.yaml
│   │   ├── embeddings.yaml
│   │   ├── mcp-tool.yaml
│   │   ├── triples.yaml
│   │   ├── objects.yaml
│   │   ├── nlp-query.yaml
│   │   ├── structured-query.yaml
│   │   ├── structured-diag.yaml
│   │   ├── graph-embeddings.yaml
│   │   ├── document-embeddings.yaml
│   │   ├── text-load.yaml
│   │   └── document-load.yaml
│   ├── import-export/
│   │   ├── core-import.yaml
│   │   ├── core-export.yaml
│   │   └── flow-import-export.yaml      # WebSocket import/export
│   ├── websocket.yaml
│   └── metrics.yaml
├── components/
│   ├── schemas/
│   │   ├── config/
│   │   ├── flow/
│   │   ├── librarian/
│   │   ├── knowledge/
│   │   ├── collection/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/
│   ├── responses/
│   └── examples/
└── security/
    └── bearerAuth.yaml
```

## 服务映射

### 全局服务 (`/api/v1/{kind}`)
`config` - 配置管理
`flow` - 流生存周期
`librarian` - 文档库
`knowledge` - 知识核心
`collection-management` - 集合元数据

### 托管于流的服务 (`/api/v1/flow/{flow}/service/{kind}`)

**请求/响应:**
`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**发布/订阅:**
`text-load`, `document-load`

### 导入/导出
`/api/v1/import-core` (POST)
`/api/v1/export-core` (GET)
`/api/v1/flow/{flow}/import/{kind}` (WebSocket)
`/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### 其他
`/api/v1/socket` (WebSocket 多路复用)
`/api/metrics` (Prometheus)

## 方案

### 第一阶段：设置
1. 创建目录结构
2. 创建主 `openapi.yaml` 文件，包含元数据、服务器、安全配置
3. 创建可重用组件（错误、通用参数、安全方案）

### 第二阶段：通用模式
创建在服务间共享的模式：
`RdfValue`, `Triple` - RDF/三元组结构
`ErrorObject` - 错误响应
`DocumentMetadata`, `ProcessingMetadata` - 元数据结构
通用参数：`FlowId`, `User`, `Collection`

### 第三阶段：全球服务
对于每个全球服务（配置、流程、库管理员、知识、集合管理）：
1. 在 `paths/` 中创建路径文件。
2. 在 `components/schemas/{service}/` 中创建请求模式。
3. 创建响应模式。
4. 添加示例。
5. 从主文件 `openapi.yaml` 中引用。

### 第四阶段：流程托管服务
对于每个流程托管服务：
1. 在 `paths/flow-services/` 中创建路径文件。
2. 在 `components/schemas/ai-services/` 中创建请求/响应模式。
3. 在适用情况下，添加流媒体标志文档。
4. 从主文件 `openapi.yaml` 中引用。

### 第五阶段：导入/导出 & WebSocket
1. 文档核心导入/导出端点。
2. 文档 WebSocket 协议模式。
3. 文档流程级别的导入/导出 WebSocket 端点。

### 第六阶段：验证
1. 使用 OpenAPI 验证工具进行验证。
2. 使用 Swagger UI 进行测试。
3. 验证所有翻译器是否已覆盖。

## 字段命名约定

所有 JSON 字段使用 **kebab-case**：
`flow-id`, `blueprint-name`, `doc-limit`, `entity-limit`, 等。

## 创建模式文件

对于 `trustgraph-base/trustgraph/messaging/translators/` 中的每个翻译器：

1. **读取翻译器 `to_pulsar()` 方法** - 定义请求模式。
2. **读取翻译器 `from_pulsar()` 方法** - 定义响应模式。
3. **提取字段名称和类型**。
4. **创建 OpenAPI 模式**，包含：
   字段名称（kebab-case）。
   类型（字符串、整数、布尔值、对象、数组）。
   必需字段。
   默认值。
   描述。

### 示例映射过程

```python
# From retrieval.py DocumentRagRequestTranslator
def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
    return DocumentRagQuery(
        query=data["query"],                              # required string
        user=data.get("user", "trustgraph"),             # optional string, default "trustgraph"
        collection=data.get("collection", "default"),     # optional string, default "default"
        doc_limit=int(data.get("doc-limit", 20)),        # optional integer, default 20
        streaming=data.get("streaming", False)            # optional boolean, default false
    )
```

对应于：

```yaml
# components/schemas/ai-services/DocumentRagRequest.yaml
type: object
required:
  - query
properties:
  query:
    type: string
    description: Search query
  user:
    type: string
    default: trustgraph
  collection:
    type: string
    default: default
  doc-limit:
    type: integer
    default: 20
    description: Maximum number of documents to retrieve
  streaming:
    type: boolean
    default: false
    description: Enable streaming responses
```

## 流式响应

支持流式传输的服务会返回带有 `end_of_stream` 标志的多个响应：
`agent`, `text-completion`, `prompt`
`document-rag`, `graph-rag`

在每个服务的响应模式中记录此模式。

## 错误响应

所有服务都可以返回：
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

其中，`ErrorObject` 指的是：
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## 参考文献

翻译人员：`trustgraph-base/trustgraph/messaging/translators/`
调度映射：`trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
终端路由：`trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
服务摘要：`API_SERVICES_SUMMARY.md`
