---
layout: default
title: "查询时可解释性"
parent: "Chinese (Beta)"
---

# 查询时可解释性

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 状态

已实现

## 概述

本规范描述了 GraphRAG 如何记录和在查询执行期间传递可解释性数据。目标是实现完全的可追溯性：从最终答案，再到选择的边，最后到源文档。

查询时可解释性捕获了 GraphRAG 管道在推理过程中的行为。它与提取时的来源信息相关联，该信息记录了知识图谱事实的来源。

## 术语

| 术语 | 定义 |
|---|---|
| **可解释性** | 结果的推导方式 |
| **会话** | 单个 GraphRAG 查询执行 |
| **边选择** | 使用 LLM 进行相关边的选择，并提供推理 |
| **来源链** | 从边 → 块 → 页面 → 文档 |

## 架构

### 可解释性流程

```
GraphRAG 查询
    │
    ├─► 会话活动
    │       └─► 查询文本，时间戳
    │
    ├─► 检索实体
    │       └─► 从子图检索的所有边
    │
    ├─► 选择实体
    │       └─► 使用 LLM 推理选择的边
    │           └─► 每条边都与提取来源关联
    │
    └─► 答案实体
            └─► 指向合成响应 (在库员中)
```

### 两阶段 GraphRAG 管道

1. **边选择**：LLM 从子图中选择相关的边，并提供每个边的推理
2. **合成**：LLM 从选择的边生成答案

这种分离实现了可解释性：我们知道哪些边贡献了结果。

### 存储

- 可解释性三元组存储在可配置的集合中 (默认：`explainability`)
- 使用 PROV-O 语义网进行来源关系
- 使用 RDF-star 重新表达进行边引用
- 答案内容存储在库员服务中 (不在内联位置 - 过于庞大)

### 实时流

可解释性事件在查询执行时流式传输到客户端：

1. 创建会话 → 发出事件
2. 检索边 → 发出事件
3. 使用推理选择边 → 发出事件
4. 答案合成 → 发出事件

客户端接收 `explain_id` 和 `explain_collection` 以获取完整详细信息。

## URI 结构

所有 URI 使用 `urn:trustgraph:` 命名空间和 UUID：

| 实体 | URI 模式 |
|---|---|
| 会话 | `urn:trustgraph:session:{uuid}` |
| 检索 | `urn:trustgraph:prov:retrieval:{uuid}` |
| 选择 | `urn:trustgraph:prov:selection:{uuid}` |
| 答案 | `urn:trustgraph:prov:answer:{uuid}` |
| 边选择 | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## RDF 模型 (PROV-O)

### 会话活动

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "GraphRAG 查询会话" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "What was the War on Terror?" .
```

### 检索实体

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "检索的边" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### 选择实体

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "选择的边" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "This edge establishes the key relationship..." .
```

### 答案实体

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "GraphRAG 答案" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

`tg:document` 引用库员服务中存储的答案。

## 名称空间常量

定义在 `trustgraph-base/trustgraph/provenance/namespaces.py`：

| 常量 | URI |
|---|---|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## GraphRagResponse 模式

```python
@dataclass
class GraphRagResponse:
    error: None | None = None
    response: str = ""
    end_of_stream: bool = False
    explain_id: str | None = None
    explain_collection: str | None = None
    message_type: str = ""  # "chunk" 或 "explain"
    end_of_session: bool = False
```

### 消息类型

| message_type | 目的 |
|---|---|
| `chunk` | 响应文本 (流式或最终) |
| `explain` | 可解释性事件，包含 IRI 引用 |

### 会话生命周期

1. 多个 `explain` 消息 (会话、检索、选择、答案)
2. 多个 `chunk` 消息 (流式响应)
3. 最终的 `chunk`，`end_of_session=True`

## 边选择格式

LLM 返回 JSONL 格式的边：

```jsonl
{"id": "edge-hash-1", "reasoning": "This edge shows the key relationship..."}
{"id": "edge-hash-2", "reasoning": "Provides supporting evidence..."}
```

`id` 是使用 `edge_id()` 计算的 `(labeled_s, labeled_p, labeled_o)` 的哈希值。

## URI 保留

### 问题

GraphRAG 向 LLM 显示了人类可读的标签，但为了可追溯性，需要原始 URI。

### 解决方案

`get_labelgraph()` 返回：
- `labeled_edges`: 包含 `(label_s, label_p, label_o)` 的列表，供 LLM 使用
- `uri_map`: 将 `edge_id(labels)` 映射到 `(uri_s, uri_p, uri_o)` 的字典

在存储可解释性数据时，使用 `uri_map` 中的 URI。

## 来源追踪

### 从边到源

可以追踪选择的边：

1. 查询包含的子图：`?subgraph tg:contains <<s p o>>`
2. 遵循 `prov:wasDerivedFrom` 链，找到根文档
3. 每个步骤中的链：块 → 页面 → 文档

### 支持 Cassandra 引用

Cassandra 查询服务支持引用：

```python
# 在 get_term_value() 中：
elif term.type == TRIPLE:
    return serialize_triple(term.triple)
```

这允许查询：
```
?subgraph tg:contains <<http://example.org/s http://example.org/p "value">>
```

## CLI 使用

```bash
tg-invoke-graph-rag --explainable -q "What was the War on Terror?"
```

## 参考

- PROV-O (W3C Provenance Ontology): https://www.w3.org/TR/prov-o/
- RDF-star: https://w3c.github.io/rdf-star/
- 提取时的来源信息: `docs/tech-specs/extraction-time-provenance.md`
