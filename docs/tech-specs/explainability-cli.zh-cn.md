# 可解释 CLI 技术规范

## 状态

草稿

## 概述

本规范描述了用于在 TrustGraph 中调试和探索可解释数据的 CLI 工具。这些工具使用户能够跟踪答案的生成方式，并从边向源文档追溯查询的来源链。

三个 CLI 工具：

1. **`tg-show-document-hierarchy`** - 显示文档 → 页面 → 块 → 边层级结构
2. **`tg-list-explain-traces`** - 列出所有 GraphRAG 会话，包含问题
3. **`tg-show-explain-trace`** - 显示会话的完整可解释性跟踪

## 目标

- **调试**: 允许开发者检查文档处理结果
- **可追溯性**: 追踪任何提取的事实，追溯到其原始文档
- **透明性**: 明确显示 GraphRAG 如何得出答案
- **易用性**: 简单的 CLI 界面，带有合理的默认设置

## 背景

TrustGraph 拥有两个来源系统：

1. **摄取时来源**: (见 `extraction-time-provenance.md`) - 记录文档 → 页面 → 块 → 边的关系，发生在摄取时。存储在名为 `urn:graph:source` 的图表中，使用 `prov:wasDerivedFrom` 属性。

2. **查询时可解释性**: (见 `query-time-explainability.md`) - 记录问题 → 探索 → 重点 → 总结链，发生在 GraphRAG 查询时。存储在名为 `urn:graph:retrieval` 的图表中。

当前限制：
- 没有简单的方法来可视化文档层级结构，在处理后
- 必须手动查询三元组来查看可解释性数据
- 没有 GraphRAG 会话的综合视图

## 技术设计

### 工具 1: `tg-show-document-hierarchy`

**目的**: 针对特定文档 ID，遍历并显示所有派生的实体。

**用法**:
```bash
tg-show-document-hierarchy "urn:trustgraph:doc:abc123"
tg-show-document-hierarchy --show-content --max-content 500 "urn:trustgraph:doc:abc123"
```

**参数**:
| 参数 | 描述 |
|---|---|
| `document_id` | 文档 URI (位置参数) |
| `-u/--api-url` | API URL |
| `-t/--token` | 身份验证令牌 |
| `-U/--user` | 用户 ID (默认: `trustgraph`) |
| `-C/--collection` | 集合 (默认: `default`) |
| `--show-content` | 包含内容 (blob/文档内容) |
| `--max-content` | 每个 blob 的最大字符数 (默认: 200) |
| `--format` | 输出格式: `tree` (默认), `json` |

**实现**:
1. 查询三元组: `?child prov:wasDerivedFrom <document_id>` 在 `urn:graph:source` 图表中
2. 递归查询每个结果的子节点
3. 构建树结构: 文档 → 页面 → 块
4. 如果 `--show-content`，则从 librarian API 获取内容
5. 以缩进树或 JSON 格式显示

**输出示例**:
```
Document: urn:trustgraph:doc:abc123
  Title: "Sample PDF"
  Type: application/pdf

  └── Page 1: urn:trustgraph:doc:abc123/p1
      ├── Chunk 0: urn:trustgraph:doc:abc123/p1/c0
          Content: "The quick brown fox..." [truncated]
      └── Chunk 1: urn:trustgraph:doc:abc123/p1/c1
          Content: "Machine learning is..." [truncated]
```

### 工具 2: `tg-list-explain-traces`

**目的**: 列出 GraphRAG 会话（问题）在集合中的所有实例。

**用法**:
```bash
tg-list-explain-traces
tg-list-explain-traces --limit 20 --format json
```

**参数**:
| 参数 | 描述 |
|---|---|
| `-u/--api-url` | API URL |
| `-t/--token` | 身份验证令牌 |
| `-U/--user` | 用户 ID |
| `-C/--collection` | 集合 |
| `--limit` | 最大结果数 (默认: 50) |
| `--format` | 输出格式: `table` (默认), `json` |

**实现**:
1. 查询: `?session tg:query ?text` 在 `urn:graph:retrieval` 图表中
2. 查询时间戳: `?session prov:startedAtTime ?time`
3. 以表格形式显示

**输出示例**:
```
Session ID                                    | Question                        | Time
----------------------------------------------|--------------------------------|---------------------
urn:trustgraph:question:abc123                | What was the War on Terror?    | 2024-01-15 10:30:00
urn:trustgraph:question:def456                | Who founded OpenAI?            | 2024-01-15 09:15:00
```

### 工具 3: `tg-show-explain-trace`

**目的**: 显示 GraphRAG 会话的完整可解释性跟踪。

**用法**:
```bash
tg-show-explain-trace "urn:trustgraph:question:abc123"
tg-show-explain-trace --max-answer 1000 --show-provenance "urn:trustgraph:question:abc123"
```

**参数**:
| 参数 | 描述 |
|---|---|
| `question_id` | 问题 URI (位置参数) |
| `-u/--api-url` | API URL |
| `-t/--token` | 身份验证令牌 |
| `-U/--user` | 用户 ID |
| `-C/--collection` | 集合 |
| `--max-answer` | 答案的最大字符数 (默认: 500) |
| `--show-provenance` | 显示来源文档的边 |
| `--format` | 输出格式: `text` (默认), `json` |

**实现**:
1. 从 `tg:query` 谓词中获取问题文本
2. 查找探索: `?exp prov:wasGeneratedBy <question_id>`
3. 查找重点: `?focus prov:wasDerivedFrom <exploration_id>`
4. 获取选定的边: `<focus_id> tg:selectedEdge ?edge`
5. 对于每个边，获取 `tg:edge` (三元组) 和 `tg:reasoning`
6. 查找总结: `?synth prov:wasDerivedFrom <focus_id>`
7. 通过 librarian API 获取答案
8. 如果 `--show-provenance`，则跟踪指向来源文档的边

**输出示例**:
```
=== GraphRAG Session: urn:trustgraph:question:abc123 ===

Question: What was the War on Terror?
Time: 2024-01-15 10:30:00

--- Exploration ---
Retrieved 50 edges from knowledge graph

--- Focus (Edge Selection) ---
Selected 12 edges:

  1. (War on Terror, definition, "A military campaign...")
     Reasoning: Directly defines the subject of the query
     Source: chunk → page 2 → "Beyond the Vigilant State"

  2. (Guantanamo Bay, part_of, War on Terror)
     Reasoning: Shows key component of the campaign

--- Synthesis ---
Answer:
  The War on Terror was a military campaign initiated...
  [truncated at 500 chars]
```

## 创建的文件

| 文件 | 目的 |
|---|---|
| `trustgraph-cli/trustgraph/cli/show_document_hierarchy.py` | 工具 1 |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | 工具 2 |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | 工具 3 |

## 引用

- 咨询时间可解释性: `docs/tech-specs/query-time-explainability.md`
- 摄取时来源: `docs/tech-specs/extraction-time-provenance.md`
- 现有 CLI 示例: `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py`