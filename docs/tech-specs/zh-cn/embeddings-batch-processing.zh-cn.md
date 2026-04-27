---
layout: default
title: "嵌入式批量处理技术规范"
parent: "Chinese (Beta)"
---

# 嵌入式批量处理技术规范

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

本规范描述了对嵌入式服务的优化，以支持在单个请求中批量处理多个文本。当前的实现方式一次处理一个文本，而没有利用嵌入式模型在处理批量数据时所能提供的显著性能优势。

1. **单文本处理效率低下**: 当前实现将单个文本包装在列表中，没有充分利用 FastEmbed 的批量处理能力。
2. **每个文本的请求开销**: 每个文本都需要单独的 Pulsar 消息往返。
3. **模型推理效率低下**: 嵌入式模型具有固定的批量处理开销；小批量会浪费 GPU/CPU 资源。
4. **调用方中的串行处理**: 关键服务循环遍历项目，并一次调用一个嵌入式模型。

## 目标

**支持批量 API**: 允许在单个请求中处理多个文本。
**向后兼容性**: 保持对单文本请求的支持。
**显著的吞吐量提升**: 针对批量操作，目标是实现 5-10 倍的吞吐量提升。
**每个文本的降低延迟**: 在嵌入多个文本时，降低平均延迟。
**内存效率**: 在不产生过多内存消耗的情况下处理批量数据。
**提供商无关性**: 支持 FastEmbed、Ollama 以及其他提供商的批量处理。
**调用方迁移**: 更新所有嵌入式模型调用方，以便在有利的情况下使用批量 API。

## 背景

### 当前实现 - 嵌入式服务

位于 `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` 中的嵌入式实现存在显著的性能低效问题：

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**问题：**

1. **批处理大小为 1：** FastEmbed 的 `embed()` 方法针对批量处理进行了优化，但我们总是使用 `[text]` - 批处理大小为 1。

2. **每个请求的开销：** 每次嵌入请求都涉及：
   Pulsar 消息序列化/反序列化
   网络往返延迟
   模型推理启动开销
   Python 异步调度开销

3. **模式限制：** `EmbeddingsRequest` 模式仅支持单个文本：
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### 当前调用者 - 序列化处理

#### 1. API 网关

**文件:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

网关通过 HTTP/WebSocket 接收单文本嵌入请求，并将它们转发到嵌入服务。目前没有批量端点。

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**影响：** 外部客户端（Web应用程序、脚本）必须发出N次HTTP请求才能嵌入N段文本。

#### 2. 文档嵌入服务

**文件：** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

逐个处理文档块：

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**影响：** 每个文档块都需要单独的嵌入调用。一个包含 100 个块的文档 = 100 个嵌入请求。

#### 3. 图嵌入服务

**文件：** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

循环遍历实体，并逐个嵌入每个实体：

```python
async def on_message(self, msg, consumer, flow):
    for entity in v.entities:
        # Serial embedding - one entity at a time
        vectors = await flow("embeddings-request").embed(
            text=entity.context
        )
        entities.append(EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors,
            chunk_id=entity.chunk_id,
        ))
```

**影响：** 一个包含 50 个实体的消息意味着 50 个序列化的嵌入请求。这在知识图谱构建过程中是一个主要的瓶颈。

#### 4. 行嵌入服务

**文件：** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

循环遍历唯一的文本，并逐个嵌入每个文本：

```python
async def on_message(self, msg, consumer, flow):
    for text, (index_name, index_value) in texts_to_embed.items():
        # Serial embedding - one text at a time
        vectors = await flow("embeddings-request").embed(text=text)

        embeddings_list.append(RowIndexEmbedding(
            index_name=index_name,
            index_value=index_value,
            text=text,
            vectors=vectors
        ))
```

**影响：** 处理包含 100 个唯一索引值的表格 = 100 个序列化嵌入请求。

#### 5. EmbeddingsClient (基础客户端)

**文件：** `trustgraph-base/trustgraph/base/embeddings_client.py`

所有流程处理器使用的客户端仅支持单文本嵌入：

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**影响：** 所有使用此客户端的调用者都仅限于执行单文本操作。

#### 6. 命令行工具

**文件：** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

命令行工具接受单个文本参数：

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**影响：** 用户无法通过命令行进行批量嵌入。处理一个文本文件需要 N 次调用。

#### 7. Python SDK

Python SDK 提供了两个客户端类，用于与 TrustGraph 服务进行交互。这两个客户端类仅支持单文本嵌入。

**文件：** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**文件：** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**影响：** 使用 SDK 的 Python 开发者必须循环遍历文本，并进行 N 次单独的 API 调用。 SDK 用户没有批量嵌入支持。

### 性能影响

对于典型的文档导入（1000 个文本块）：
**当前：** 1000 个单独的请求，1000 次模型推理调用
**批量（batch_size=32）：** 32 个请求，32 次模型推理调用（减少 96.8%）

对于图嵌入（包含 50 个实体的消息）：
**当前：** 50 次序列等待调用，约 5-10 秒
**批量：** 1-2 次批量调用，约 0.5-1 秒（提升 5-10 倍）

FastEmbed 和类似库在批量大小达到硬件限制时，可以实现接近线性的吞吐量扩展（通常每个批次 32-128 个文本）。

## 技术设计

### 架构

嵌入批量处理优化需要修改以下组件：

#### 1. **模式增强**
   扩展 `EmbeddingsRequest` 以支持多个文本
   扩展 `EmbeddingsResponse` 以返回多个向量集合
   保持与单文本请求的向后兼容性

   模块：`trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **基础服务增强**
   更新 `EmbeddingsService` 以处理批量请求
   添加批量大小配置
   实现支持批量请求的处理逻辑

   模块：`trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **提供者处理器更新**
   更新 FastEmbed 处理器，将整个批次传递给 `embed()`
   更新 Ollama 处理器，以处理批次（如果支持）
   为不支持批处理的提供商添加回退的序列化处理

   模块：
   `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **客户端增强**
   向 `EmbeddingsClient` 添加批量嵌入方法
   支持单次和批量 API
   为大型输入添加自动批量处理

   模块：`trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **调用方更新 - 流处理器**
   更新 `graph_embeddings` 以批量实体上下文
   更新 `row_embeddings` 以批量索引文本
   如果消息批量处理可行，则更新 `document_embeddings`

   模块：
   `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **API 网关增强**
   添加批量嵌入端点
   支持请求体中的文本数组

   模块：`trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **CLI 工具增强**
   添加对多个文本或文件输入的支持
   添加批量大小参数

   模块：`trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **Python SDK 增强**
   向 `FlowInstance` 添加 `embeddings_batch()` 方法
   向 `SocketFlowInstance` 添加 `embeddings_batch()` 方法
   为 SDK 用户支持单次和批量 API

   模块：
   `trustgraph-base/trustgraph/api/flow.py`
   `trustgraph-base/trustgraph/api/socket_client.py`

### 数据模型

#### EmbeddingsRequest

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

用法：
单个文本：`EmbeddingsRequest(texts=["hello world"])`
批量：`EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### EmbeddingsResponse

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

响应结构：
`vectors[i]` 包含用于 `texts[i]` 的向量集合。
每个向量集合都是 `list[list[float]]` (模型可能为每个文本返回多个向量)。
示例：3 个文本 → `vectors` 有 3 个条目，每个条目包含该文本的嵌入向量。

### API 接口

#### EmbeddingsClient

```python
class EmbeddingsClient(RequestResponse):
    async def embed(
        self,
        texts: list[str],
        timeout: float = 300,
    ) -> list[list[list[float]]]:
        """
        Embed one or more texts in a single request.

        Args:
            texts: List of texts to embed
            timeout: Timeout for the operation

        Returns:
            List of vector sets, one per input text
        """
        resp = await self.request(
            EmbeddingsRequest(texts=texts),
            timeout=timeout
        )
        if resp.error:
            raise RuntimeError(resp.error.message)
        return resp.vectors
```

#### API 网关嵌入式模型端点

更新后的端点支持单个或批量嵌入式模型：

```
POST /api/v1/embeddings
Content-Type: application/json

{
    "texts": ["text1", "text2", "text3"],
    "flow_id": "default"
}

Response:
{
    "vectors": [
        [[0.1, 0.2, ...]],
        [[0.3, 0.4, ...]],
        [[0.5, 0.6, ...]]
    ]
}
```

### 实现细节

#### 第一阶段：模式更改

**EmbeddingsRequest:**
```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

**EmbeddingsResponse:**
```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

**更新了 EmbeddingsService.on_request：**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### 第二阶段：FastEmbed 处理器更新

**当前（效率低下）：**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**更新：**
```python
async def on_embeddings(self, texts: list[str], model=None):
    """Embed texts - processes all texts in single model call"""
    if not texts:
        return []

    use_model = model or self.default_model
    self._load_model(use_model)

    # FastEmbed handles the full batch efficiently
    all_vecs = list(self.embeddings.embed(texts))

    # Return list of vector sets, one per input text
    return [[v.tolist()] for v in all_vecs]
```

#### 第三阶段：图嵌入服务更新

**当前 (序列号):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**更新 (批量):**
```python
async def on_message(self, msg, consumer, flow):
    # Collect all contexts
    contexts = [entity.context for entity in v.entities]

    # Single batch embedding call
    all_vectors = await flow("embeddings-request").embed(texts=contexts)

    # Pair results with entities
    entities = [
        EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors[0],  # First vector from the set
            chunk_id=entity.chunk_id,
        )
        for entity, vectors in zip(v.entities, all_vectors)
    ]
```

#### 第四阶段：行嵌入服务更新

**当前 (序列号):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**更新 (批量):**
```python
# Collect texts and metadata
texts = list(texts_to_embed.keys())
metadata = list(texts_to_embed.values())

# Single batch embedding call
all_vectors = await flow("embeddings-request").embed(texts=texts)

# Pair results
embeddings_list = [
    RowIndexEmbedding(
        index_name=meta[0],
        index_value=meta[1],
        text=text,
        vectors=vectors[0]  # First vector from the set
    )
    for text, meta, vectors in zip(texts, metadata, all_vectors)
]
```

#### 第五阶段：命令行工具增强

**更新后的命令行界面：**
```python
def main():
    parser = argparse.ArgumentParser(...)

    parser.add_argument(
        'text',
        nargs='*',  # Zero or more texts
        help='Text(s) to convert to embedding vectors',
    )

    parser.add_argument(
        '-f', '--file',
        help='File containing texts (one per line)',
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for processing (default: 32)',
    )
```

用法：
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### 第六阶段：Python SDK 增强

**FlowInstance (HTTP 客户端):**

```python
class FlowInstance:
    def embeddings(self, texts: list[str]) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        input = {"texts": texts}
        return self.request("service/embeddings", input)["vectors"]
```

**SocketFlowInstance (WebSocket 客户端):**

```python
class SocketFlowInstance:
    def embeddings(self, texts: list[str], **kwargs: Any) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts via WebSocket.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        request = {"texts": texts}
        response = self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
        return response["vectors"]
```

**SDK 使用示例：**

```python
# Single text
vectors = flow.embeddings(["hello world"])
print(f"Dimensions: {len(vectors[0][0])}")

# Batch embedding
texts = ["text one", "text two", "text three"]
all_vectors = flow.embeddings(texts)

# Process results
for text, vecs in zip(texts, all_vectors):
    print(f"{text}: {len(vecs[0])} dimensions")
```

## 安全注意事项

**请求大小限制**: 强制执行最大批处理大小，以防止资源耗尽。
**超时处理**: 针对批处理大小，适当调整超时时间。
**内存限制**: 监控大型批处理的内存使用情况。
**输入验证**: 在处理之前，验证批处理中的所有文本。

## 性能注意事项

### 预期改进

**吞吐量**:
单个文本: ~10-50 文本/秒 (取决于模型)
批处理 (大小 32): ~200-500 文本/秒 (提升 5-10 倍)

**每个文本的延迟**:
单个文本: 每个文本 50-200 毫秒
批处理 (大小 32): 每个文本 5-20 毫秒 (摊销值)

**特定服务的改进**:

| 服务 | 当前 | 批处理 | 改进 |
|---------|---------|---------|-------------|
| 图嵌入 (50 个实体) | 5-10 秒 | 0.5-1 秒 | 5-10 倍 |
| 行嵌入 (100 个文本) | 10-20 秒 | 1-2 秒 | 5-10 倍 |
| 文档导入 (1000 个块) | 100-200 秒 | 10-30 秒 | 5-10 倍 |

### 配置参数

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## 测试策略

### 单元测试
单个文本嵌入（向后兼容）
空批处理的处理
最大批处理大小的强制执行
部分批处理失败的错误处理

### 集成测试
通过 Pulsar 进行端到端批处理嵌入
图嵌入服务批处理
行嵌入服务批处理
API 网关批处理端点

### 性能测试
比较单批和批量吞吐量
在各种批处理大小下的内存使用情况
延迟分布分析

## 迁移计划

这是一个破坏性更改版本。所有阶段都一起实施。

### 第一阶段：Schema 更改
将 EmbeddingsRequest 中的 `text: str` 替换为 `texts: list[str]`
将 EmbeddingsResponse 中的 `vectors` 类型更改为 `list[list[list[float]]]`

### 第二阶段：处理器更新
更新 FastEmbed 和 Ollama 处理器中的 `on_embeddings` 签名
在单个模型调用中处理整个批次

### 第三阶段：客户端更新
更新 `EmbeddingsClient.embed()` 以接受 `texts: list[str]`

### 第四阶段：调用方更新
更新 graph_embeddings 以批处理实体上下文
更新 row_embeddings 以批处理索引文本
更新 document_embeddings 以使用新的 Schema
更新 CLI 工具

### 第五阶段：API 网关
更新用于新 Schema 的嵌入端点

### 第六阶段：Python SDK
更新 `FlowInstance.embeddings()` 签名
更新 `SocketFlowInstance.embeddings()` 签名

## 开放问题

**大型批处理的流式传输**: 我们是否应该支持对非常大的批处理（>100 个文本）进行流式传输结果？
**特定于提供商的限制**: 我们应该如何处理具有不同最大批处理大小的提供商？
**部分失败处理**: 如果批处理中的一个文本失败，我们应该使整个批处理失败，还是返回部分结果？
**文档嵌入批处理**: 我们应该跨多个 Chunk 消息进行批处理，还是保持每个消息的处理？

## 参考文献

[FastEmbed 文档](https://github.com/qdrant/fastembed)
[Ollama 嵌入 API](https://github.com/ollama/ollama)
[EmbeddingsService 实现](trustgraph-base/trustgraph/base/embeddings_service.py)
[GraphRAG 性能优化](graphrag-performance-optimization.md)
