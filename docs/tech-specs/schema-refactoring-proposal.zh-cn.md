# 方案：Schema 目录重构

## 当前问题

1. **扁平结构** - 所有 Schema 都位于同一目录下，难以理解它们之间的关系
2. **混杂的关注点** - 核心类型、领域对象和 API 契约都混合在一起
3. **不明确的命名** - 文件如 "object.py", "types.py", "topic.py" 并不能清晰地表明其用途
4. **缺乏明确的层级** - 无法轻松地看出哪些依赖于哪些

## 建议的结构

```
trustgraph-base/trustgraph/schema/
├── __init__.py
├── core/              # 核心基本类型，在所有地方使用
│   ├── __init__.py
│   ├── primitives.py  # Error, Value, Triple, Field, RowSchema
│   ├── metadata.py    # 元数据记录
│   └── topic.py       # Topic 工具
│
├── knowledge/         # 知识领域模型和提取
│   ├── __init__.py
│   ├── graph.py       # EntityContext, EntityEmbeddings, Triples
│   ├── document.py    # Document, TextDocument, Chunk
│   ├── knowledge.py   # 知识提取类型
│   ├── embeddings.py  # 所有与嵌入相关的类型（从多个文件中移动）
│   └── nlp.py         # Definition, Topic, Relationship, Fact 类型
│
└── services/          # 服务请求/响应契约
    ├── __init__.py
    ├── llm.py         # TextCompletion, Embeddings, Tool 请求/响应
    ├── retrieval.py   # GraphRAG, DocumentRAG 查询/响应
    ├── query.py       # GraphEmbeddingsRequest/Response, DocumentEmbeddingsRequest/Response
    ├── agent.py       # Agent 请求/响应
    ├── flow.py        # Flow 请求/响应
    ├── prompt.py      # Prompt 服务请求/响应
    ├── config.py      # 配置服务
    ├── library.py     # 库服务
    └── lookup.py      # 查找服务
```

## 关键变更

1. **分层组织** - 清晰地将核心类型、知识模型和服务契约分开
2. **更好的命名**：
   - `types.py` → `core/primitives.py` (更清晰的用途)
   - `object.py` → 根据实际内容将文件拆分
   - `documents.py` → `knowledge/document.py` (单数，一致)
   - `models.py` → `services/llm.py` (更清晰地表明模型类型)
   - `prompt.py` → 拆分：服务部分到 `services/prompt.py`，数据类型到 `knowledge/nlp.py`

3. **逻辑分组**：
   - 所有嵌入类型集中在 `knowledge/embeddings.py`
   - 所有与 LLM 相关的服务契约在 `services/llm.py`
   - 在 services 目录中明确区分请求/响应对
   - 知识提取类型与其它知识领域模型分组

4. **依赖关系清晰**：
   - 核心类型没有依赖
   - 知识模型仅依赖核心
   - 服务契约可以依赖核心和知识模型

## 迁移的好处

1. **更轻松的导航** - 开发者可以快速找到所需的内容
2. **更好的模块化** - 区分不同关注点更清晰
3. **更简单的导入** - 更有意义的导入路径
4. **更具未来性** - 轻松添加新的知识类型或服务，而无需增加混乱

## 示例导入变更

```python
# 之前
from trustgraph.schema import Error, Triple, GraphEmbeddings, TextCompletionRequest

# 之后
from trustgraph.schema.core import Error, Triple
from trustgraph.schema.knowledge import GraphEmbeddings
from trustgraph.schema.services import TextCompletionRequest
```

## 实施说明

1. 通过在根的 `__init__.py` 中保持导入，保持与以前的兼容性
2. 逐步移动文件，并在需要时更新导入
3. 考虑添加一个 `legacy.py`，用于在过渡期间导入所有内容
4. 更新文档以反映新的结构

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "检查当前 Schema 目录结构", "status": "completed", "priority": "high"}, {"id": "2", "content": "分析 Schema 文件及其用途", "status": "completed", "priority": "high"}, {"id": "3", "content": "提出改进的命名和结构", "status": "completed", "priority": "high"}]