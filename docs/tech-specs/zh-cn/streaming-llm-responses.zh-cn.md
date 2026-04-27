---
layout: default
title: "流式LLM响应技术规范"
parent: "Chinese (Beta)"
---

# 流式LLM响应技术规范

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

本规范描述了在TrustGraph中实现LLM响应的流式支持。流式传输允许实时交付由LLM生成的token，而不是等待完整的响应生成。
流式传输允许实时交付由LLM生成的token，而不是等待完整的响应生成。
流式传输允许实时交付由LLM生成的token，而不是等待完整的响应生成。
流式传输允许实时交付由LLM生成的token，而不是等待完整的响应生成。

此实现支持以下用例：

1. **实时用户界面**: 将生成的令牌流式传输到用户界面，
   从而提供即时的视觉反馈。
2. **减少首次令牌时间**: 用户立即看到输出，
   而不是等待完整生成。
3. **处理长响应**: 处理可能导致超时或超出内存限制的非常长的输出。
   4. **交互式应用程序**: 启用响应迅速的聊天和代理界面。


## 目标

**向后兼容性：** 现有的非流式客户端继续工作
  无需修改。
**一致的 API 设计：** 流式和非流式使用相同的模式，差异最小。
  
**提供商的灵活性：** 在可用时支持流式传输，在不可用时提供优雅的
  回退方案。
**分阶段推出：** 逐步实施以降低风险。
**端到端支持：** 从 LLM 提供商到客户端
  应用程序，通过 Pulsar、Gateway API 和 Python API 提供支持。

## 背景

### 当前架构

当前 LLM 文本补全流程如下：

1. 客户端发送 `TextCompletionRequest`，包含 `system` 和 `prompt` 字段。
2. LLM 服务处理请求并等待完整生成。
3. 返回单个 `TextCompletionResponse`，包含完整的 `response` 字符串。

当前模式 (`trustgraph-base/trustgraph/schema/services/llm.py`)：

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
```

### 当前限制

**延迟：** 用户必须等待完整生成后才能看到任何输出。
**超时风险：** 较长的生成过程可能超出客户端超时阈值。
**糟糕的用户体验：** 在生成过程中没有反馈，会让人产生缓慢的感觉。
**资源使用：** 完整的响应必须缓存在内存中。

本规范通过启用增量响应来解决这些限制，同时保持完全的向后兼容性。


## 技术设计

### 第一阶段：基础设施

第一阶段通过修改模式、API 和 CLI 工具，为流式传输奠定基础。


#### 模式更改

##### LLM 模式 (`trustgraph-base/trustgraph/schema/services/llm.py`)

**请求更改：**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

`streaming`：当 `true` 时，请求流式响应传输。
默认：`false`（保留现有行为）。

**响应变更：**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

`end_of_stream`：当 `true` 时，表示这是最终（或唯一的）响应。
对于非流式请求：单个响应，包含 `end_of_stream=true`。
对于流式请求：多个响应，全部包含 `end_of_stream=false`。
  除了最后一个响应。

##### 提示模式 (`trustgraph-base/trustgraph/schema/services/prompt.py`)

提示服务包装了文本补全功能，因此它遵循相同的模式：

**请求更改：**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**响应变更：**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### 网关 API 变更

网关 API 必须向 HTTP/WebSocket 客户端暴露流式传输功能。

**REST API 更新：**

`POST /api/v1/text-completion`: 接受请求体中的 `streaming` 参数
响应行为取决于流式传输标志：
  `streaming=false`: 单个 JSON 响应（当前行为）
  `streaming=true`: 服务器发送事件 (SSE) 流或 WebSocket 消息

**响应格式（流式传输）：**

每个流式传输的数据块都遵循相同的模式结构：
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

最终部分：
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### Python API 变更

Python 客户端 API 必须同时支持流式和非流式模式，
同时保持向后兼容性。

**LlmClient 更新** (`trustgraph-base/trustgraph/clients/llm_client.py`):

```python
class LlmClient(BaseClient):
    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        # Existing behavior when streaming=False

    async def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request.
        Yields response chunks as they arrive.
        """
        # New async generator method
```

**PromptClient 更新** (`trustgraph-base/trustgraph/base/prompt_client.py`):

类似于使用 `streaming` 参数和异步生成器的变体。

#### CLI 工具更改

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

默认启用流式传输，以获得更好的交互式用户体验。
`--no-streaming` 标志禁用流式传输。
当启用流式传输时：将生成的 token 输出到标准输出，并在它们到达时立即输出。
当禁用流式传输时：等待完整的响应，然后输出。

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

与 `tg-invoke-llm` 相同的模式。

#### LLM 服务基础类更改

**LlmService** (`trustgraph-base/trustgraph/base/llm_service.py`):

```python
class LlmService(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        request = msg.value()
        streaming = getattr(request, 'streaming', False)

        if streaming and self.supports_streaming():
            async for chunk in self.generate_content_stream(...):
                await self.send_response(chunk, end_of_stream=False)
            await self.send_response(final_chunk, end_of_stream=True)
        else:
            response = await self.generate_content(...)
            await self.send_response(response, end_of_stream=True)

    def supports_streaming(self):
        """Override in subclass to indicate streaming support."""
        return False

    async def generate_content_stream(self, system, prompt, model, temperature):
        """Override in subclass to implement streaming."""
        raise NotImplementedError()
```

--

### 第二阶段：VertexAI 概念验证

第二阶段在单个提供商（VertexAI）中实现流式传输，以验证
基础设施并实现端到端测试。

#### VertexAI 实施

**模块：** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**变更：**

1. 覆盖 `supports_streaming()` 以返回 `True`
2. 实现 `generate_content_stream()` 异步生成器
3. 处理 Gemini 和 Claude 模型（通过 VertexAI Anthropic API）

**Gemini 流式传输：**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    model_instance = self.get_model(model, temperature)
    response = model_instance.generate_content(
        [system, prompt],
        stream=True  # Enable streaming
    )
    for chunk in response:
        yield LlmChunk(
            text=chunk.text,
            in_token=None,  # Available only in final chunk
            out_token=None,
        )
    # Final chunk includes token counts from response.usage_metadata
```

**Claude (通过 VertexAI Anthropic) 流式传输：**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### 测试

流式响应组装的单元测试
与 VertexAI (Gemini 和 Claude) 的集成测试
端到端测试：CLI -> 网关 -> Pulsar -> VertexAI -> 回调
向后兼容性测试：非流式请求仍然有效

--

### 第三阶段：所有 LLM 提供商

第三阶段将流式支持扩展到系统中的所有 LLM 提供商。

#### 提供商实施状态

每个提供商必须：
1. **完全流式支持**: 实施 `generate_content_stream()`
2. **兼容模式**: 正确处理 `end_of_stream` 标志
   (返回单个响应，包含 `end_of_stream=true`)

| 提供商 | 包 | 流式支持 |
|----------|---------|-------------------|
| OpenAI | trustgraph-flow | 完全 (原生流式 API) |
| Claude/Anthropic | trustgraph-flow | 完全 (原生流式 API) |
| Ollama | trustgraph-flow | 完全 (原生流式 API) |
| Cohere | trustgraph-flow | 完全 (原生流式 API) |
| Mistral | trustgraph-flow | 完全 (原生流式 API) |
| Azure OpenAI | trustgraph-flow | 完全 (原生流式 API) |
| Google AI Studio | trustgraph-flow | 完全 (原生流式 API) |
| VertexAI | trustgraph-vertexai | 完全 (第二阶段) |
| Bedrock | trustgraph-bedrock | 完全 (原生流式 API) |
| LM Studio | trustgraph-flow | 完全 (与 OpenAI 兼容) |
| LlamaFile | trustgraph-flow | 完全 (与 OpenAI 兼容) |
| vLLM | trustgraph-flow | 完全 (与 OpenAI 兼容) |
| TGI | trustgraph-flow | 待定 |
| Azure | trustgraph-flow | 待定 |

#### 实施模式

对于与 OpenAI 兼容的提供商 (OpenAI, LM Studio, LlamaFile, vLLM)：

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    response = await self.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield LlmChunk(text=chunk.choices[0].delta.content)
```

--

### 第四阶段：代理 API

第四阶段将流式传输扩展到代理 API。 这更加复杂，因为
代理 API 本身就是多消息的（思考 → 行动 → 观察
→ 重复 → 最终答案）。

#### 当前代理模式

```python
class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()
```

#### 建议的代理模式变更

**请求变更：**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**响应变化：**

代理在推理过程中会产生多种类型的输出：
想法（推理）
动作（工具调用）
观察结果（工具结果）
答案（最终回复）
错误

由于 `chunk_type` 标识了正在发送的内容类型，因此可以合并单独的
`answer`、`error`、`thought` 和 `observation` 字段，
从而将其合并到一个 `content` 字段中：

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**字段语义：**

`chunk_type`: 指示 `content` 字段中包含的内容类型。
  `"thought"`: 代理的推理/思考。
  `"action"`: 正在调用的工具/动作。
  `"observation"`: 来自工具执行的结果。
  `"answer"`: 对用户问题的最终答案。
  `"error"`: 错误消息。

`content`: 实际的流式内容，根据 `chunk_type` 进行解释。

`end_of_message`: 当 `true` 时，当前块类型已完成。
  示例：当前思考的所有 token 都已发送。
  允许客户端知道何时进入下一个阶段。

`end_of_dialog`: 当 `true` 时，整个代理交互已完成。
  这是一个流中的最终消息。

#### 代理流式行为

当 `streaming=true` 时：

1. **思考流式传输：**
   具有 `chunk_type="thought"`、`end_of_message=false` 的多个块。
   最终的思考块具有 `end_of_message=true`。
2. **动作通知：**
   具有 `chunk_type="action"`、`end_of_message=true` 的单个块。
3. **观察：**
   具有 `chunk_type="observation"` 的块（块），最终块具有 `end_of_message=true`。
4. **重复** 1-3 步骤，直到代理完成推理。
5. **最终答案：**
   `chunk_type="answer"` 包含最终的响应，位于 `content` 中。
   最后一个块具有 `end_of_message=true`、`end_of_dialog=true`。

**示例流序列：**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

当 `streaming=false`:
当前行为保持不变
提供完整的答案的单个响应
`end_of_message=true`, `end_of_dialog=true`

#### 网关和 Python API

网关：用于代理流的新 SSE/WebSocket 端点
Python API：新的 `agent_stream()` 异步生成器方法

--

## 安全注意事项

**没有新的攻击面**：流式传输使用相同的身份验证/授权机制
**速率限制**：如果需要，请应用每个令牌或每个分块的速率限制
**连接处理**：在客户端断开连接时，正确终止流
**超时管理**：流式传输请求需要适当的超时处理

## 性能注意事项

**内存**：流式传输减少了峰值内存使用量（没有完整的响应缓冲）
**延迟**：首次令牌的时间显著减少
**连接开销**：SSE/WebSocket 连接具有保活开销
**Pulsar 吞吐量**：多个小消息与单个大消息之间的权衡
  tradeoff

## 测试策略

### 单元测试
使用新字段的模式序列化/反序列化
向后兼容性（缺少字段使用默认值）
分块组装逻辑

### 集成测试
每个 LLM 提供商的流式传输实现
网关 API 流式传输端点
Python 客户端流式传输方法

### 端到端测试
CLI 工具的流式传输输出
完整流程：客户端 → 网关 → Pulsar → LLM → 返回
混合流式传输/非流式传输工作负载

### 向后兼容性测试
现有客户端无需修改即可工作
非流式传输请求的行为与之前相同

## 迁移计划

### 第一阶段：基础设施
部署模式更改（向后兼容）
部署网关 API 更新
部署 Python API 更新
发布 CLI 工具更新

### 第二阶段：VertexAI
部署 VertexAI 流式实现。
使用测试工作负载进行验证。

### 第三阶段：所有提供商
逐步推广提供商更新。
监控问题。

### 第四阶段：Agent API
部署 Agent 模式变更。
部署 Agent 流式实现。
更新文档。

## 时间线

| 阶段 | 描述 | 依赖项 |
|-------|-------------|--------------|
| 第一阶段 | 基础设施 | 无 |
| 第二阶段 | VertexAI 概念验证 | 第一阶段 |
| 第三阶段 | 所有提供商 | 第二阶段 |
| 第四阶段 | Agent API | 第三阶段 |

## 设计决策

在规范过程中，解决了以下问题：

1. **流式传输中的 Token 计数**: Token 计数是增量值，而不是累计总数。
   消费者可以根据需要对其进行求和。这与大多数提供商报告的使用方式一致，并简化了实现。
   

2. **流中的错误处理：** 如果发生错误，则会填充 `error` 字段，并且不需要填充其他字段。 错误始终是最终的
   通信 - 在发生错误后，不允许也不期望发送任何后续消息。
   通信 - 在此之后，不允许也不需要发送任何后续消息。
   一个错误。对于 LLM/Prompt 流，`end_of_stream=true`。对于 Agent 流，
   `chunk_type="error"` 与 `end_of_dialog=true`。

3. **部分响应恢复：** 消息协议（Pulsar）具有容错性，
   因此不需要消息级别的重试。如果客户端丢失了流的信息
   或断开连接，则必须从头开始重试整个请求。

4. **快速响应流式传输**: 流式传输仅支持文本 (`text`)
   响应，不支持结构化 (`object`) 响应。 提示服务在开始时就知道输出将是 JSON 还是文本，这取决于提示
   模板。 如果对 JSON 输出提示执行流式传输请求，则
   会出现问题。
   服务应该要么：
   返回完整的 JSON 数据，以单个响应的形式，包含 `end_of_stream=true`，或者
   拒绝流式传输请求，并返回错误。

## 开放问题

目前没有。

## 参考文献

当前 LLM 模式：`trustgraph-base/trustgraph/schema/services/llm.py`
当前提示词模式：`trustgraph-base/trustgraph/schema/services/prompt.py`
当前代理模式：`trustgraph-base/trustgraph/schema/services/agent.py`
LLM 服务基础地址：`trustgraph-base/trustgraph/base/llm_service.py`
VertexAI 提供商：`trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
网关 API：`trustgraph-base/trustgraph/api/`
CLI 工具：`trustgraph-cli/trustgraph/cli/`
