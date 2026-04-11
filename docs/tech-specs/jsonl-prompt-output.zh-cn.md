# JSONL 提示输出技术规范

## 概述

<<<<<<< HEAD
本规范描述了在 TrustGraph 中，用于提示响应的 JSONL（JSON Lines）输出格式的实现。JSONL 允许在大型语言模型（LLM）的响应中，以一种能够抵抗截断的方式提取结构化数据，从而解决了当 LLM 响应达到输出令牌限制时，JSON 数组输出可能被损坏的关键问题。
=======
本规范描述了在 TrustGraph 中，用于提示响应的 JSONL（JSON Lines）输出格式的实现。JSONL 允许在大型语言模型 (LLM) 响应中提取结构化数据，即使在响应达到输出令牌限制时，也能保持数据的完整性。
JSONL 能够实现对结构化数据的截断鲁棒性提取，解决了当 LLM 响应达到输出令牌限制时，JSON 数组输出可能被破坏的关键问题。
>>>>>>> 82edf2d (New md files from RunPod)




<<<<<<< HEAD

=======
>>>>>>> 82edf2d (New md files from RunPod)
本实现支持以下用例：

1. **抗截断提取**: 即使当
   LLM 输出在响应过程中被截断时，也能提取有效的中间结果。
2. **大规模提取**: 能够处理大量项的提取，而不会因 token 限制导致完全失败的风险。
   3. **混合类型提取**: 支持在单个提示中提取多种实体类型（定义、关系、实体、属性）。
4. **支持流式输出**: 允许对提取结果进行未来的流式/增量处理。
   
## 目标
   

## 目标

**向后兼容性**: 仍然可以使用 `response-type: "text"` 和
  `response-type: "json"` 的现有提示，无需修改即可继续工作。
<<<<<<< HEAD
**截断恢复能力**: 即使是部分 LLM 输出，也能产生部分有效的结果，
  而不是完全失败。
**模式验证**: 支持对单个对象进行 JSON 模式验证。
**区分联合类型**: 支持使用 `type` 字段作为区分器的混合类型输出。
  **最小的 API 变更**: 通过新的
=======
**截断鲁棒性**: 即使是部分 LLM 输出，也能产生部分有效的结果，
  而不是完全失败。
**模式验证**: 支持对单个对象进行 JSON 模式验证。
**区分联合**: 支持使用 `type` 字段作为区分器的混合类型输出。
  **最小的 API 更改**: 通过新的
>>>>>>> 82edf2d (New md files from RunPod)
响应类型和模式键来扩展现有的提示配置。
  

## 背景

### 当前架构

提示服务支持两种响应类型：

1. `response-type: "text"` - 原始文本响应，按原样返回。
2. `response-type: "json"` - 从响应中解析的 JSON 数据，并根据
   可选的 `schema` 进行验证。

当前在 `trustgraph-flow/trustgraph/template/prompt_manager.py` 中的实现：

```python
class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema
```

### 当前限制

当提取提示要求输出为 JSON 数组 (`[{...}, {...}, ...]`) 时：

**截断损坏：** 如果 LLM 在数组中间达到输出令牌限制，则整个响应变为无效的 JSON，无法解析。
  **全或无解析：** 必须接收完整的输出才能进行解析。
**没有部分结果：** 截断的响应会产生零可用数据。
**不适用于大型提取：** 提取的项目越多，失败的风险越高。


此规范通过引入 JSONL 格式来解决这些限制，其中每个提取的项目都是一个完整的 JSON 对象，位于其自己的行上。



## 技术设计

### 响应类型扩展

添加一个新的响应类型 `"jsonl"`，与现有的 `"text"` 和 `"json"` 类型并列。

#### 配置更改

**新的响应类型值：**

```
"response-type": "jsonl"
```

**模式解释：**

现有的 `"schema"` 键同时用于 `"json"` 和 `"jsonl"` 响应类型。
解释取决于响应类型：

`"json"`：模式描述整个响应（通常是数组或对象）。
`"jsonl"`：模式描述每个单独的行/对象。

```json
{
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": { "type": "string" },
      "definition": { "type": "string" }
    },
    "required": ["entity", "definition"]
  }
}
```

<<<<<<< HEAD
这避免了对提示配置工具和编辑器的修改。
=======
这避免了对提示配置工具和编辑器的更改。
>>>>>>> 82edf2d (New md files from RunPod)

### JSONL 格式规范

#### 简单提取

对于提取单一类型对象（定义、关系、
主题、行）的提示，输出为每行一个 JSON 对象，没有包装：

**提示输出格式：**
```
{"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"}
{"entity": "chlorophyll", "definition": "Green pigment in plants"}
{"entity": "mitochondria", "definition": "Powerhouse of the cell"}
```

**与之前的 JSON 数组格式对比：**
```json
[
  {"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"},
  {"entity": "chlorophyll", "definition": "Green pigment in plants"},
  {"entity": "mitochondria", "definition": "Powerhouse of the cell"}
]
```

<<<<<<< HEAD
如果大型语言模型在第2行之后截断，JSON数组格式会产生无效的JSON，
而JSONL会产生两个有效的对象。
=======
如果大型语言模型在第2行之后截断，JSON数组格式将产生无效的JSON，
而JSONL格式将产生两个有效的对象。
>>>>>>> 82edf2d (New md files from RunPod)

#### 混合类型提取（区分联合）

对于需要提取多种类型对象（例如，定义和
关系，或者实体、关系和属性）的提示，请使用一个 `"type"`
字段作为区分器：

**提示输出格式：**
```
{"type": "definition", "entity": "DNA", "definition": "Molecule carrying genetic instructions"}
{"type": "relationship", "subject": "DNA", "predicate": "located_in", "object": "cell nucleus", "object-entity": true}
{"type": "definition", "entity": "RNA", "definition": "Molecule that carries genetic information"}
{"type": "relationship", "subject": "RNA", "predicate": "transcribed_from", "object": "DNA", "object-entity": true}
```

<<<<<<< HEAD
**区分联合的模式使用 `oneOf`:**
=======
**区分联合的模式使用 `oneOf`：**
>>>>>>> 82edf2d (New md files from RunPod)
```json
{
  "response-type": "jsonl",
  "schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "type": { "const": "definition" },
          "entity": { "type": "string" },
          "definition": { "type": "string" }
        },
        "required": ["type", "entity", "definition"]
      },
      {
        "type": "object",
        "properties": {
          "type": { "const": "relationship" },
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "object-entity": { "type": "boolean" }
        },
        "required": ["type", "subject", "predicate", "object", "object-entity"]
      }
    ]
  }
}
```

<<<<<<< HEAD
#### 本体抽取

对于基于本体的抽取，涉及实体、关系和属性：
=======
#### 本体提取

对于基于本体的实体、关系和属性提取：
>>>>>>> 82edf2d (New md files from RunPod)

**提示输出格式：**
```
{"type": "entity", "entity": "Cornish pasty", "entity_type": "fo/Recipe"}
{"type": "entity", "entity": "beef", "entity_type": "fo/Food"}
{"type": "relationship", "subject": "Cornish pasty", "subject_type": "fo/Recipe", "relation": "fo/has_ingredient", "object": "beef", "object_type": "fo/Food"}
{"type": "attribute", "entity": "Cornish pasty", "entity_type": "fo/Recipe", "attribute": "fo/serves", "value": "4 people"}
```

### 实现细节

#### 提示类

现有的`Prompt`类不需要进行任何更改。 `schema`字段将被重用。
用于 JSONL 格式，其解释由 `response_type` 决定：

```python
class Prompt:
    def __init__(self, template, response_type="text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema  # Interpretation depends on response_type
```

#### PromptManager.load_config

无需修改 - 现有的配置加载已经处理了
`schema` 键。

#### JSONL 解析

添加一种新的解析方法，用于解析 JSONL 格式的响应：

```python
def parse_jsonl(self, text):
    """
    Parse JSONL response, returning list of valid objects.

    Invalid lines (malformed JSON, empty lines) are skipped with warnings.
    This provides truncation resilience - partial output yields partial results.
    """
    results = []

    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown code fence markers if present
        if line.startswith('```'):
            continue

        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError as e:
            # Log warning but continue - this provides truncation resilience
            logger.warning(f"JSONL parse error on line {line_num}: {e}")

    return results
```

#### PromptManager.invoke 变更

扩展 invoke 方法以处理新的响应类型：

```python
async def invoke(self, id, input, llm):
    logger.debug("Invoking prompt template...")

    terms = self.terms | self.prompts[id].terms | input
    resp_type = self.prompts[id].response_type

    prompt = {
        "system": self.system_template.render(terms),
        "prompt": self.render(id, input)
    }

    resp = await llm(**prompt)

    if resp_type == "text":
        return resp

    if resp_type == "json":
        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

    if resp_type == "jsonl":
        objects = self.parse_jsonl(resp)

        if not objects:
            logger.warning("JSONL parse returned no valid objects")
            return []

        # Validate each object against schema if provided
        if self.prompts[id].schema:
            validated = []
            for i, obj in enumerate(objects):
                try:
                    validate(instance=obj, schema=self.prompts[id].schema)
                    validated.append(obj)
                except Exception as e:
                    logger.warning(f"Object {i} failed schema validation: {e}")
            return validated

        return objects

    raise RuntimeError(f"Response type {resp_type} not known")
```

### 受影响的提示语

以下提示语应迁移到 JSONL 格式：

| 提示语 ID | 描述 | 类型字段 |
|-----------|-------------|------------|
| `extract-definitions` | 实体/定义提取 | 否（单个类型）|
| `extract-relationships` | 关系提取 | 否（单个类型）|
| `extract-topics` | 主题/定义提取 | 否（单个类型）|
| `extract-rows` | 结构化行提取 | 否（单个类型）|
| `agent-kg-extract` | 组合定义 + 关系提取 | 是：`"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | 基于本体的提取 | 是：`"entity"`, `"relationship"`, `"attribute"` |

### API 变更

#### 客户端视角

JSONL 解析对提示服务 API 的调用者是透明的。解析过程
在提示服务的服务器端进行，响应通过标准的
`PromptResponse.object` 字段以序列化的 JSON 数组形式返回。

当客户端调用提示服务（通过 `PromptClient.prompt()` 或类似方式时）：

<<<<<<< HEAD
**`response-type: "json"`**（带有数组模式）→ 客户端接收 Python `list`
**`response-type: "jsonl"`** → 客户端接收 Python `list`

从客户端的角度来看，两者都返回相同的的数据结构。
=======
**`response-type: "json"`** (带有数组模式) → 客户端接收 Python `list`
**`response-type: "jsonl"`** → 客户端接收 Python `list`

从客户端的角度来看，两者都返回相同的数据结构。
>>>>>>> 82edf2d (New md files from RunPod)
区别完全在于服务器端如何解析 LLM 的输出：

JSON 数组格式：单个 `json.loads()` 调用；如果被截断，则完全失败。
JSONL 格式：逐行解析；如果被截断，则产生部分结果。

这意味着，现有的客户端代码期望从提取提示中获得列表，
在将提示从 JSON 迁移到 JSONL 格式时，不需要进行任何更改。

#### 服务器返回值

对于 `response-type: "jsonl"`，`PromptManager.invoke()` 方法返回一个
`list[dict]`，其中包含所有成功解析和验证的对象。 此
列表随后被序列化为 JSON，用于 `PromptResponse.object` 字段。

#### 错误处理

空结果：返回一个空列表 `[]`，并带有警告日志。
部分解析失败：返回成功解析的对象列表，
  并为解析失败的情况记录警告日志。
完全解析失败：返回一个空列表 `[]`，并带有警告日志。

这与 `response-type: "json"` 不同，后者会在解析失败时引发 `RuntimeError`。
对于 JSONL 的宽松处理是故意的，目的是为了提供截断恢复能力。


### 配置示例

完整的提示配置示例：

```json
{
  "prompt": "Extract all entities and their definitions from the following text. Output one JSON object per line.\n\nText:\n{{text}}\n\nOutput format per line:\n{\"entity\": \"<name>\", \"definition\": \"<definition>\"}",
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": {
        "type": "string",
        "description": "The entity name"
      },
      "definition": {
        "type": "string",
        "description": "A clear definition of the entity"
      }
    },
    "required": ["entity", "definition"]
  }
}
```

## 安全注意事项

**输入验证**: JSON 解析使用标准的 `json.loads()`，这可以防止注入攻击。
  **模式验证**: 使用 ⟦CODE_0⟧ 来强制执行模式。
**模式验证**: 使用 `jsonschema.validate()` 进行模式强制。
<<<<<<< HEAD
**没有新的攻击面：** JSONL 解析比 JSON 数组解析更安全，因为它采用逐行处理的方式。
=======
**无新的攻击面**: JSONL 解析比 JSON 数组解析更安全，因为采用逐行处理的方式。
>>>>>>> 82edf2d (New md files from RunPod)
  parsing due to line-by-line processing

## 性能考量

**内存**: 逐行解析比加载完整的 JSON 数组消耗更少的峰值内存。
  **延迟**: 解析性能与 JSON 数组解析相当。
**验证**: 模式验证按对象进行，这会增加开销，但
可以在验证失败时提供部分结果。
  
## 测试策略


### 单元测试

使用有效输入的 JSONL 解析
使用空行的 JSONL 解析
使用 Markdown 代码块的 JSONL 解析
使用截断的最终行的 JSONL 解析
包含穿插无效 JSON 行的 JSONL 解析
使用 `oneOf` 区分联合的模式验证
<<<<<<< HEAD
向后兼容性：现有的 `"text"` 和 `"json"` 提示词保持不变

### 集成测试

使用 JSONL 提示词的端到端提取
=======
向后兼容性：现有的 `"text"` 和 `"json"` 提示保持不变

### 集成测试

使用 JSONL 提示的端到端提取
>>>>>>> 82edf2d (New md files from RunPod)
使用模拟截断的提取（人为限制响应）
使用类型区分器的混合类型提取
使用所有三种类型的本体提取

### 提取质量测试

比较提取结果：JSONL 与 JSON 数组格式
验证截断恢复能力：JSONL 在 JSON 失败的情况下，可以产生部分结果

## 迁移计划

### 第一阶段：实施

1. 在 `parse_jsonl()` 中实现 `PromptManager` 方法
2. 扩展 `invoke()` 以处理 `response-type: "jsonl"`
3. 添加单元测试

<<<<<<< HEAD
### 第二阶段：提示词迁移

1. 更新 `extract-definitions` 提示词和配置
2. 更新 `extract-relationships` 提示词和配置
3. 更新 `extract-topics` 提示词和配置
4. 更新 `extract-rows` 提示词和配置
5. 更新 `agent-kg-extract` 提示词和配置
6. 更新 `extract-with-ontologies` 提示词和配置
=======
### 第二阶段：提示迁移

1. 更新 `extract-definitions` 提示和配置
2. 更新 `extract-relationships` 提示和配置
3. 更新 `extract-topics` 提示和配置
4. 更新 `extract-rows` 提示和配置
5. 更新 `agent-kg-extract` 提示和配置
6. 更新 `extract-with-ontologies` 提示和配置
>>>>>>> 82edf2d (New md files from RunPod)

### 第三阶段：下游更新

1. 更新任何使用提取结果的代码，使其能够处理列表返回类型。
2. 更新根据 `type` 字段对混合类型提取进行分类的代码。
<<<<<<< HEAD
3. 更新用于断言提取输出格式的测试。
=======
3. 更新断言提取输出格式的测试。
>>>>>>> 82edf2d (New md files from RunPod)

## 待解决问题

目前没有。

## 参考文献

当前实现：`trustgraph-flow/trustgraph/template/prompt_manager.py`
JSON Lines 规范：https://jsonlines.org/
JSON Schema `oneOf`：https://json-schema.org/understanding-json-schema/reference/combining.html#oneof
相关规范：Streaming LLM Responses (`docs/tech-specs/streaming-llm-responses.md`)
