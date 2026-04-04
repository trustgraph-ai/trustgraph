# CLI 修改：v1.8 到 v2.1

## 摘要

CLI (`trustgraph-cli`) 包含大量新增功能，主要集中在以下三个方面：
**可解释性/来源追溯**, **嵌入式访问**, 和 **图查询**。
移除两个旧工具，一个重命名，并且多个现有工具获得了新的功能。

---

## 新的 CLI 工具

### 可解释性 & 来源追溯

| 命令 | 描述 |
|---------|-------------|
| `tg-list-explain-traces` | 列出集合中所有 Explain 实例（GraphRAG 和 Agent），显示实例 ID、类型、问题文本和时间戳。 |
| `tg-show-explain-trace` | 显示 Explain 实例的完整追溯信息。 对于 GraphRAG：问题、探索、聚焦、合成阶段。 对于 Agent：会话、迭代（思考/行动/观察）、最终答案。 自动检测追溯类型。 支持 `--show-provenance` 选项，用于追溯边缘到源文档。 |
| `tg-show-extraction-provenance` | 给出文档 ID，遍历来源链：文档 -> 页面 -> 块 -> 边缘，使用 `prov:wasDerivedFrom` 关系。 支持 `--show-content` 和 `--max-content` 选项。 |

### 嵌入式

| 命令 | 描述 |
|---------|-------------|
| `tg-invoke-embeddings` | 通过嵌入服务将文本转换为向量嵌入。 接受一个或多个文本输入，返回向量为浮点数的列表。 |
| `tg-invoke-graph-embeddings` | 使用向量嵌入根据文本相似性查询图实体。 返回匹配的实体以及相似度得分。 |
| `tg-invoke-document-embeddings` | 使用向量嵌入根据文本相似性查询文档块。 返回匹配的块 ID 以及相似度得分。 |
| `tg-invoke-row-embeddings` | 使用在索引字段上进行的文本相似性查询，查询结构化数据行。 返回与索引值和得分匹配的行。 需要 `--schema-name` 且支持 `--index-name`。 |

### 图查询

| 命令 | 描述 |
|---------|-------------|
| `tg-query-graph` | 基于模式的图存储查询。 与 `tg-show-graph` 不同（它会显示所有内容），这允许通过任何组合的子句、谓词、对象和图进行选择性查询。 自动检测值类型：IRI (`http://...`, `urn:...`, `<...>`)、带有引号的三重 (`<<s p o>>`) 和字面量。 |
| `tg-get-document-content` | 从库中通过文档 ID 获取文档内容。 可以输出到文件或 stdout，支持文本和二进制内容。 |

---

## 已移除的 CLI 工具

| 命令 | 备注 |
|---------|-------|
| `tg-load-pdf` | 已移除。 文档加载现在通过库/处理流程进行。 |
| `tg-load-text` | 已移除。 文档加载现在通过库/处理流程进行。 |

---

## 重命名后的 CLI 工具

| 旧名称 | 新名称 | 备注 |
|----------|----------|-------|
| `tg-invoke-objects-query` | `tg-invoke-rows-query` | 反映了从 "对象" 到 "行" 的术语重命名，用于结构化数据。 |

---

## 现有工具的重要变更

### `tg-invoke-graph-rag`

- **可解释性支持**: 现在支持 4 阶段的可解释性管道（问题、基础/探索、聚焦、合成），并显示内联来源事件。
- **流式传输**: 使用 WebSocket 流式传输实现实时输出。
- **来源追溯**: 可以通过重构和 `prov:wasDerivedFrom` 链，追溯选定的边缘回源文档。
- 从约 30 行增长到约 760 行，以适应完整的可解释性管道。

### `tg-invoke-document-rag`

- **可解释性支持**: 添加了 `question_explainable()` 模式，可以流式传输带有内联来源事件的文档 RAG 响应（问题、基础、探索、合成阶段）。

### `tg-invoke-agent`

- **可解释性支持**: 添加了 `question_explainable()` 模式，在执行代理时显示内联来源事件（问题、分析、结论、AgentThought、AgentObservation、AgentAnswer）。
- 详细模式显示了带有表情符号前缀的思考/观察流。

### `tg-show-graph`

- **流式传输模式**: 现在使用 `triples_query_stream()` 与可配置的批次大小，实现更快的首次结果时间和减少内存开销。
- **命名图支持**: 新的 `--graph` 过滤选项。 识别命名图：
  - 默认图 (空): 核心知识的事实
  - `urn:graph:source`: 提取来源
  - `urn:graph:retrieval`: 查询时追溯
- **显示图列**: 新的 `--show-graph` 标志，显示每个三元组的命名图。
- **可配置的限制**: 新的 `--limit` 和 `--batch-size` 选项。

### `tg-graph-to-turtle`

- **RDF-star 支持**: 现在可以处理带有引号的三元 (`RDF-star reification`)。
- **流式传输模式**: 使用流式传输实现更快的首次处理时间。
- **Wire 格式处理**: 已更新为使用新的 wire 格式 (`{"t": "i", "i": uri}` 用于 IRI，`{"t": "l", "v": value}` 用于字面量，`{"t": "r", "r": {...}}` 用于带有引号的三元)，代替旧的 `{"v": ..., "e": ...}` 格式。
- **命名图支持**: 新的 `--graph` 过滤选项。

### `tg-set-tool`

- **新的工具类型**: `row-embeddings-query` 用于在结构化数据索引上进行语义搜索。
- **新的选项**: `--schema-name`, `--index-name`, `--limit` 用于配置 `row-embeddings-query` 工具。

### `tg-show-tools`

- 显示新的 `row-embeddings-query` 工具类型及其 `schema-name`、`index-name` 和 `limit` 字段。

### `tg-load-knowledge`

- **进度报告**: 现在统计并报告每个文件的加载三元和实体上下文的数量，以及总数。
- **术语格式更新**: 实体上下文现在使用新的术语格式 (`{"t": "i", "i": uri}`) 代替旧的 Value 格式 (`{"v": entity, "e": True}`)。

---

## 破坏性变更

- **术语重命名**: `Value` 模式已重命名为 `Term`，该重命名影响了与图存储交互的 CLI 工具。 新格式使用 `{"t": "i", "i": uri}` 用于 IRI，`{"t": "l", "v": value}` 用于字面量，代替旧的 `{"v": ..., "e": ...}` 格式。
- **`tg-invoke-objects-query` 重命名**为 `tg-invoke-rows-query`。
- **`tg-load-pdf` 和 `tg-load-text` 已移除**。