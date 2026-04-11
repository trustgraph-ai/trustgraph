# RAG 实时支持技术规范

## 概述

本规范描述了为 GraphRAG 和 DocumentRAG 服务添加实时支持的方法，从而实现知识图谱和文档检索查询的实时分块响应。 这扩展了现有的实时架构，该架构已针对 LLM 文本补全、提示和代理服务实施。

## 目标

- **一致的实时体验**: 在所有 TrustGraph 服务中提供相同的时间体验
- **最小的 API 更改**: 通过单个 `streaming` 标志添加实时支持，遵循已建立的模式
- **保持现有兼容性**: 保持现有非实时行为作为默认
- **重用现有基础设施**: 利用 PromptClient 现有的实时功能
- **网关支持**: 通过 websocket 网关为客户端应用程序启用实时

## 背景

当前已实现的实时服务：
- **LLM 文本补全服务**: 第一阶段 - 从 LLM 提供商获取
- **提示服务**: 第二阶段 - 通过提示模板进行流式传输
- **代理服务**: 第三阶段 - 使用 ReAct 响应和分块的思考/观察/答案进行流式传输

RAG 服务的当前限制：
- GraphRAG 和 DocumentRAG 仅支持块响应
- 用户必须等待 LLM 响应完成才能看到任何输出
- 针对知识图谱或文档查询的较长响应给用户体验带来不便
- 与其他 TrustGraph 服务相比，体验不一致

本规范通过为 GraphRAG 和 DocumentRAG 添加实时支持来解决这些问题。 通过实现分块响应，TrustGraph 可以：
- 在所有查询类型中提供一致的实时体验
- 减少 RAG 查询的感知延迟
- 允许长时间运行查询的更好进度反馈
- 客户端应用程序支持实时显示

## 技术设计

### 架构

RAG 实时实现利用了现有的基础设施：

1. **PromptClient 实时** (已实现)
   - `kg_prompt()` 和 `document_prompt()` 已经接受 `streaming` 和 `chunk_callback` 参数
   - 这些调用 `prompt()` 内部，并启用实时功能
   - PromptClient 不需要任何更改

   模块： `trustgraph-base/trustgraph/base/prompt_client.py`

2. **GraphRAG 服务** (需要传递实时参数)
   - 将 `streaming` 参数添加到 `query()` 方法
   - 将实时标志和回调函数传递给 `prompt_client.kg_prompt()`
   - GraphRagRequest 模式需要包含 `streaming` 字段

   模块：
   - `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
   - `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (处理器)
   - `trustgraph-base/trustgraph/schema/graph_rag.py` (Request 模式)
   - `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (网关)

3. **DocumentRAG 服务** (需要传递实时参数)
   - 将 `streaming` 参数添加到 `query()` 方法
   - 将实时标志和回调函数传递给 `prompt_client.document_prompt()`
   - DocumentRagRequest 模式需要包含 `streaming` 字段

   模块：
   - `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
   - `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (处理器)
   - `trustgraph-base/trustgraph/schema/document_rag.py` (Request 模式)
   - `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (网关)

### 数据流

**非实时 (当前)**：
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=False)
                                   ↓
                                Prompt Service → LLM
                                   ↓
                                完整响应
                                   ↓
Client ← Gateway ← RAG Service ←  Response
```

**实时 (提案)**：
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                                   ↓
                                Prompt Service → LLM (streaming)
                                   ↓
                                块 → 回调 → RAG 响应 (块)
                                   ↓                       ↓
Client ← Gateway ← ────────────────────────────────── 响应流
```

### API

**GraphRAG 更改**:

1. **GraphRag.query()** - 添加实时参数
```python
async def query(
    self, query, user, collection,
    verbose=False, streaming=False, chunk_callback=None  # NEW
):
    # ... 现有实体/三元组检索 ...

    if streaming and chunk_callback:
        resp = await self.prompt_client.kg_prompt(
            query, kg,
            streaming=True,
            chunk_callback=chunk_callback
        )
    else:
        resp = await self.prompt_client.kg_prompt(query, kg)

    return resp
```

2. **GraphRagRequest 模式** - 添加实时字段
```python
class GraphRagRequest(Record):
    query = String()
    user = String()
    collection = String()
    streaming = Boolean()  # NEW
```

3. **GraphRagResponse 模式** - 添加实时字段 (遵循 Agent 模式)
```python
class GraphRagResponse(Record):
    response = String()    # Legacy: complete response
    chunk = String()       # NEW: streaming chunk
    end_of_stream = Boolean()  # NEW: indicates last chunk
```

4. **Processor** - 传递实时
```python
async def handle(self, msg):
    # ... 现有代码 ...

    async def send_chunk(chunk):
        await self.respond(GraphRagResponse(
            chunk=chunk,
            end_of_stream=False,
            response=None
        ))

    if request.streaming:
        full_response = await self.rag.query(
            query=request.query,
            user=request.user,
            collection=request.collection,
            streaming=True,
            chunk_callback=send_chunk
        )
        # 发送最终消息
        await self.respond(GraphRagResponse(
            chunk=None,
            end_of_stream=True,
            response=full_response
        ))
    else:
        # 现有非实时路径
        response = await self.rag.query(...)
        await self.respond(GraphRagResponse(response=response))
```

**DocumentRAG 更改**:

与 GraphRAG 相同模式：
1. 将 `streaming` 和 `chunk_callback` 参数添加到 `DocumentRag.query()`
2. 将 `streaming` 字段添加到 `DocumentRagRequest`
3. 将 `streaming` 字段添加到 `DocumentRagResponse`

### 时间线

估计实现时间：4-6 小时
- 第一阶段 (2 小时)： GraphRAG 实时支持
- 第二阶段 (2 小时)： DocumentRAG 实时支持
- 第三阶段 (1-2 小时)： 网关更新和 CLI 标志
- 测试： 已包含在每个阶段

## 开放问题

- 是否应该为 NLP 查询服务添加实时支持？
- 我们是否只想要实时输出中间步骤 (例如 "检索实体..."、"查询图...")，还是也想要实时输出？
- GraphRAG/DocumentRAG 响应是否应该包含块元数据 (例如块编号、预期总数)？

## 参考

- 现有实现： `docs/tech-specs/streaming-llm-responses.md`
- Agent 实时： `trustgraph-flow/trustgraph/agent/react/agent_manager.py`
- PromptClient 实时： `trustgraph-base/trustgraph/base/prompt_client.py`