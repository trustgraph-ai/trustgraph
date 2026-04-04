## JSONL 提示输出技术规范

## 概述

本规范描述了在 TrustGraph 中实现 JSONL (JSON Lines) 输出格式的提示响应。JSONL 允许以容错的方式从 LLM 响应中提取结构化数据，从而解决了 JSON 数组输出在 LLM 响应达到输出令牌限制时发生损坏的问题。

此实现支持以下用例：

1. **容错提取**: 即使 LLM 输出被截断，仍可提取有效的部分结果
2. **大规模提取**: 能够在不因令牌限制而完全失败的情况下，处理大量项的提取
3. **混合类型提取**: 支持在单个提示中提取多种实体类型（定义、关系、实体、属性）
4. **流兼容输出**: 启用提取结果的未来流式/增量处理

## 目标

- **向后兼容性**: 使用 `response-type: "text"` 和 `response-type: "json"` 的现有提示无需修改即可继续工作
- **容错提取**: 部分 LLM 输出产生部分有效的结果，而不是完全失败
- **模式验证**: 支持对单个对象进行 JSON 模式验证
- **区分联合**: 使用 `type` 字段作为区分器，支持混合类型输出
- **最小的 API 更改**: 通过添加新的响应类型和模式键来扩展现有提示配置

## 背景

### 当前架构

提示服务支持两种响应类型：

1. `response-type: "text"` - 原始文本响应作为是返回
2. `response-type: "json"` - 从响应中解析，并根据可选的 `schema` 进行验证

### 影响的提示

以下提示应迁移到 JSONL 格式：

| 提示 ID | 描述 | 类型字段 |
|---|---|---|
| `extract-definitions` | 提取所有实体及其定义 | 无 (单个类型) |
| `extract-relationships` | 提取关系 | 无 (单个类型) |
| `extract-topics` | 提取主题/定义 | 无 (单个类型) |
| `extract-rows` | 提取结构化行 | 无 (单个类型) |
| `agent-kg-extract` | 组合定义 + 关系提取 | 是: `"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | 提取本体 | 是: `"entity"`, `"relationship"`, `"attribute"` |

### API 更改

#### 客户端视角

JSONL 解析对提示服务调用者透明。解析发生在提示服务内部，响应通过标准 `PromptResponse.object` 字段作为序列化的 JSON 数组返回。

当客户端调用提示服务（通过 `PromptClient.prompt()` 或类似方法）时：

- `response-type: "json"` (带数组模式) → 客户端接收 Python `list`
- `response-type: "jsonl"` → 客户端接收 Python `list`

从客户端的视角来看，两者都返回相同的数据结构。 区别在于 LLM 响应如何在服务器端进行解析：

- JSON 数组格式：执行一个 `json.loads()` 调用；如果被截断则完全失败
- JSONL 格式：逐行解析；如果被截断则产生部分结果

这意味着预期的以 JSON 格式返回提取结果的代码，无需在迁移到 JSONL 格式的提示时进行更改。

#### 服务器返回值

对于 `response-type: "jsonl"`，`PromptManager.invoke()` 方法返回一个 `list[dict]`，其中包含成功解析和验证的对象。 此列表随后通过 `PromptResponse.object` 字段作为 JSON 序列化。

#### 错误处理

- 无结果: 返回空列表 `[]`，带有警告日志
- 部分解析失败: 返回成功解析对象的列表，带有失败的警告日志
- 完全解析失败: 返回空列表 `[]`，带有警告日志

与 `response-type: "json"` 相比，这种行为是故意的，旨在提供容错性。

### 性能考虑

- 内存：逐行解析比加载完整的 JSON 数组使用更少的峰值内存
- 延迟：解析的性能与 JSON 数组解析相似
- 验证：按对象运行模式验证，这会增加开销，但允许在验证失败时产生部分结果

## 测试策略

### 单元测试

- JSONL 格式的有效输入解析
- 空行的 JSONL 解析
- Markdown 代码块的 JSONL 解析
- 最后的行被截断的 JSONL 解析
- 无效 JSON 行的 JSONL 解析
- 带有 `oneOf` 的区分联合的模式验证
- 现有 `"text"` 和 `"json"` 提示的向后兼容性

### 集成测试

- 使用 JSONL 提示的端到端提取
- 模拟截断响应（人为限制响应）
- 使用类型区分器的混合类型提取
- 使用所有三种类型的本体提取

### 提取质量测试

- 比较 JSONL 和 JSON 数组格式的提取结果
- 验证容错性: JSONL 在被截断时产生部分结果，而 JSON 失败
- 验证混合类型提取的类型字段

### 迁移计划

### 阶段 1：实现

1. 在 `PromptManager` 中实现 `parse_jsonl()` 方法
2. 扩展 `invoke()` 以处理 `response-type: "jsonl"`
3. 添加单元测试

### 阶段 2：提示迁移

1. 迁移 `extract-definitions` 提示和配置
2. 迁移 `extract-relationships` 提示和配置
3. 迁移 `extract-topics` 提示和配置
4. 迁移 `extract-rows` 提示和配置
5. 迁移 `agent-kg-extract` 提示和配置
6. 迁移 `extract-with-ontologies` 提示和配置

### 阶段 3：下游更新

1. 更新消费提取结果的代码以处理列表返回类型
2. 更新对按 `type` 字段对混合类型提取进行分类的代码
3. 更新断言提取结果格式的测试

## 安全考虑

- 输入验证：使用标准 `json.loads()` 进行 JSON 解析，这可以防止注入攻击
- 模式验证：使用 `jsonschema.validate()` 进行模式强制
- 无新攻击面：逐行解析比 JSON 数组解析更安全，因为它不会导致问题

## 性能考虑

- 内存：逐行解析使用更少的峰值内存，而不是加载完整的 JSON 数组
- 延迟：解析性能与 JSON 数组解析相似
- 验证：按对象运行模式验证，这会增加开销，但允许在验证失败时产生部分结果

## 迁移计划

### 阶段 1：实现

1. 在 `PromptManager` 中实现 `parse_jsonl()` 方法
2. 扩展 `invoke()` 以处理 `response-type: "jsonl"`
3. 添加单元测试

### 阶段 2：提示迁移

1. 迁移 `extract-definitions` 提示和配置
2. 迁移 `extract-relationships` 提示和配置
3. 迁移 `extract-topics` 提示和配置
4. 迁移 `extract-rows` 提示和配置
5. 迁移 `agent-kg-extract` 提示和配置
6. 迁移 `extract-with-ontologies` 提示和配置

### 阶段 3：下游更新

1. 更新消费提取结果的代码以处理列表返回类型
2. 更新对按 `type` 字段对混合类型提取进行分类的代码
3. 更新断言提取结果格式的测试

## 开放问题

目前没有。

## 参考

- 当前实现：`trustgraph-flow/trustgraph/template/prompt_manager.py`
- JSON Lines 规范：https://jsonlines.org/
- JSON Schema `oneOf`：https://json-schema.org/understanding-json-schema/reference/combining.html#oneof
- 相关规范：流式 LLM 响应 (`docs/tech-specs/streaming-llm-responses.md`)