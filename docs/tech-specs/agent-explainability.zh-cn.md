---
layout: default
title: "Agent Explainability: Provenance Recording"
parent: "Chinese (Beta)"
---

# Agent Explainability: Provenance Recording

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

为使代理会话可追溯和可调试，并将代理循环中的溯源记录添加到 React 代理中，从而使用与 GraphRAG 相同的可解释性基础设施。

**设计决策：**
写入 `urn:graph:retrieval` (通用可解释性图)
目前采用线性依赖链 (分析 N → wasDerivedFrom → 分析 N-1)
工具是不可见的黑盒 (仅记录输入/输出)
DAG 支持计划在未来迭代中实现

## 实体类型

GraphRAG 和 Agent 都使用 PROV-O 作为基础本体，并具有 TrustGraph 特定的子类型：

### GraphRAG 类型
| 实体 | PROV-O 类型 | TG 类型 | 描述 |
|--------|-------------|----------|-------------|
| 问题 | `prov:Activity` | `tg:Question`, `tg:GraphRagQuestion` | 用户的查询 |
| 探索 | `prov:Entity` | `tg:Exploration` | 从知识图谱检索的边 |
| 重点 | `prov:Entity` | `tg:Focus` | 带有推理的选定边 |
| 合成 | `prov:Entity` | `tg:Synthesis` | 最终答案 |

### Agent 类型
| 实体 | PROV-O 类型 | TG 类型 | 描述 |
|--------|-------------|----------|-------------|
| 问题 | `prov:Activity` | `tg:Question`, `tg:AgentQuestion` | 用户的查询 |
| 分析 | `prov:Entity` | `tg:Analysis` | 每个思考/行动/观察周期 |
| 结论 | `prov:Entity` | `tg:Conclusion` | 最终答案 |

### Document RAG 类型
| 实体 | PROV-O 类型 | TG 类型 | 描述 |
|--------|-------------|----------|-------------|
| 问题 | `prov:Activity` | `tg:Question`, `tg:DocRagQuestion` | 用户的查询 |
| 探索 | `prov:Entity` | `tg:Exploration` | 从文档存储中检索的块 |
| 合成 | `prov:Entity` | `tg:Synthesis` | 最终答案 |

**注意：** Document RAG 使用 GraphRAG 类型的子集 (没有“重点”步骤，因为没有边选择/推理阶段)。

### 问题子类型

所有“问题”实体都共享 `tg:Question` 作为基本类型，但具有特定的子类型以标识检索机制：

| 子类型 | URI 模式 | 机制 |
|---------|-------------|-----------|
| `tg:GraphRagQuestion` | `urn:trustgraph:question:{uuid}` | 知识图谱 RAG |
| `tg:DocRagQuestion` | `urn:trustgraph:docrag:{uuid}` | 文档/块 RAG |
| `tg:AgentQuestion` | `urn:trustgraph:agent:{uuid}` | ReAct 代理 |

这允许通过 `tg:Question` 查询所有问题，同时通过子类型过滤特定机制。

## 溯源模型

```
Question (urn:trustgraph:agent:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasDerivedFrom
    │
Analysis1 (urn:trustgraph:agent:{uuid}/i1)
    │
    │  tg:thought = "I need to query the knowledge base..."
    │  tg:action = "knowledge-query"
    │  tg:arguments = {"question": "..."}
    │  tg:observation = "Result from tool..."
    │  rdf:type = prov:Entity, tg:Analysis
    │
    ↓ prov:wasDerivedFrom
    │
Analysis2 (urn:trustgraph:agent:{uuid}/i2)
    │  ...
    ↓ prov:wasDerivedFrom
    │
Conclusion (urn:trustgraph:agent:{uuid}/final)
    │
    │  tg:answer = "The final response..."
    │  rdf:type = prov:Entity, tg:Conclusion
```

### 文档检索增强生成（RAG）溯源模型

```
Question (urn:trustgraph:docrag:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasGeneratedBy
    │
Exploration (urn:trustgraph:docrag:{uuid}/exploration)
    │
    │  tg:chunkCount = 5
    │  tg:selectedChunk = "chunk-id-1"
    │  tg:selectedChunk = "chunk-id-2"
    │  ...
    │  rdf:type = prov:Entity, tg:Exploration
    │
    ↓ prov:wasDerivedFrom
    │
Synthesis (urn:trustgraph:docrag:{uuid}/synthesis)
    │
    │  tg:content = "The synthesized answer..."
    │  rdf:type = prov:Entity, tg:Synthesis
```

## 需要修改的内容

### 1. 模式更改

**文件:** `trustgraph-base/trustgraph/schema/services/agent.py`

向 `AgentRequest` 添加 `session_id` 和 `collection` 字段：
```python
@dataclass
class AgentRequest:
    question: str = ""
    state: str = ""
    group: list[str] | None = None
    history: list[AgentStep] = field(default_factory=list)
    user: str = ""
    collection: str = "default"  # NEW: Collection for provenance traces
    streaming: bool = False
    session_id: str = ""         # NEW: For provenance tracking across iterations
```

**文件:** `trustgraph-base/trustgraph/messaging/translators/agent.py`

更新翻译器，使其能够处理 `session_id` 和 `collection`，并在 `to_pulsar()` 和 `from_pulsar()` 中均能正确处理。

### 2. 向 Agent Service 添加可解释性生产者

**文件:** `trustgraph-flow/trustgraph/agent/react/service.py`

注册一个“可解释性”生产者（与 GraphRAG 相同模式）：
```python
from ... base import ProducerSpec
from ... schema import Triples

# In __init__:
self.register_specification(
    ProducerSpec(
        name = "explainability",
        schema = Triples,
    )
)
```

### 3. 溯源三元组生成

**文件:** `trustgraph-base/trustgraph/provenance/agent.py`

创建辅助函数（类似于 GraphRAG 的 `question_triples`、`exploration_triples` 等）：
```python
def agent_session_triples(session_uri, query, timestamp):
    """Generate triples for agent Question."""
    return [
        Triple(s=session_uri, p=RDF_TYPE, o=PROV_ACTIVITY),
        Triple(s=session_uri, p=RDF_TYPE, o=TG_QUESTION),
        Triple(s=session_uri, p=TG_QUERY, o=query),
        Triple(s=session_uri, p=PROV_STARTED_AT_TIME, o=timestamp),
    ]

def agent_iteration_triples(iteration_uri, parent_uri, thought, action, arguments, observation):
    """Generate triples for one Analysis step."""
    return [
        Triple(s=iteration_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=iteration_uri, p=RDF_TYPE, o=TG_ANALYSIS),
        Triple(s=iteration_uri, p=TG_THOUGHT, o=thought),
        Triple(s=iteration_uri, p=TG_ACTION, o=action),
        Triple(s=iteration_uri, p=TG_ARGUMENTS, o=json.dumps(arguments)),
        Triple(s=iteration_uri, p=TG_OBSERVATION, o=observation),
        Triple(s=iteration_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]

def agent_final_triples(final_uri, parent_uri, answer):
    """Generate triples for Conclusion."""
    return [
        Triple(s=final_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=final_uri, p=RDF_TYPE, o=TG_CONCLUSION),
        Triple(s=final_uri, p=TG_ANSWER, o=answer),
        Triple(s=final_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]
```

### 4. 类型定义

**文件:** `trustgraph-base/trustgraph/provenance/namespaces.py`

添加可解释性实体类型和代理谓词：
```python
# Explainability entity types (used by both GraphRAG and Agent)
TG_QUESTION = TG + "Question"
TG_EXPLORATION = TG + "Exploration"
TG_FOCUS = TG + "Focus"
TG_SYNTHESIS = TG + "Synthesis"
TG_ANALYSIS = TG + "Analysis"
TG_CONCLUSION = TG + "Conclusion"

# Agent predicates
TG_THOUGHT = TG + "thought"
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation"
TG_ANSWER = TG + "answer"
```

## 文件修改

| 文件 | 更改 |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | 向 AgentRequest 添加 session_id 和 collection |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | 更新翻译器以适应新字段 |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | 添加实体类型、agent谓词和 Document RAG 谓词 |
| `trustgraph-base/trustgraph/provenance/triples.py` | 向 GraphRAG 三元组构建器添加 TG 类型，添加 Document RAG 三元组构建器 |
| `trustgraph-base/trustgraph/provenance/uris.py` | 添加 Document RAG URI 生成器 |
| `trustgraph-base/trustgraph/provenance/__init__.py` | 导出新类型、谓词和 Document RAG 函数 |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | 向 DocumentRagResponse 添加 explain_id 和 explain_graph |
| `trustgraph-base/trustgraph/messaging/translators/retrieval.py` | 更新 DocumentRagResponseTranslator 以适应可解释性字段 |
| `trustgraph-flow/trustgraph/agent/react/service.py` | 添加可解释性生产者 + 记录逻辑 |
| `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` | 添加可解释性回调并发出溯源三元组 |
| `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` | 添加可解释性生产者并连接回调 |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | 处理 agent 跟踪类型 |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | 在 GraphRAG 旁边列出 agent 会话 |

## 创建的文件

| 文件 | 目的 |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | Agent 相关的三元组生成器 |

## CLI 更新

**检测：** 无论是 GraphRAG 还是 Agent 问题，都具有 `tg:Question` 类型。通过以下方式区分：
1. URI 模式：`urn:trustgraph:agent:` vs `urn:trustgraph:question:`
2. 派生实体：`tg:Analysis` (agent) vs `tg:Exploration` (GraphRAG)

**`list_explain_traces.py`:**
显示类型列（Agent vs GraphRAG）

**`show_explain_trace.py`:**
自动检测跟踪类型
Agent 渲染显示：问题 → 分析步骤(s) → 结论

## 向后兼容性

`session_id` 默认为 `""` - 旧请求有效，但将不具有溯源信息
`collection` 默认为 `"default"` - 合理的备选方案
CLI 能够优雅地处理两种跟踪类型

## 验证

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# List traces (should show agent sessions with Type column)
tg-list-explain-traces -U trustgraph -C default

# Show agent trace
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## 未来工作（不在本次 PR 中）

DAG 依赖关系（当分析 N 使用来自多个先前分析的结果时）
特定于工具的溯源链接（KnowledgeQuery → 它的 GraphRAG 跟踪）
流式溯源输出（在过程中输出，而不是在最后批量输出）
