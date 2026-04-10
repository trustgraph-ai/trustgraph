# 提取来源：子图模型

## 问题

提取时 provenance 目前为每个提取的三元组生成完整的重构：一个唯一的 ⟦CODE_0⟧、⟦CODE_1⟧，以及与每个知识事实相关的 PROV-O 元数据。处理一个块
提取时 provenance 目前为每个提取的三元组生成完整的重构：一个唯一的 `stmt_uri`、`activity_uri`，以及与每个知识事实相关的 PROV-O 元数据。处理一个块
提取时 provenance 目前为每个提取的三元组生成完整的重构：一个唯一的 ⟦CODE_0⟧、⟦CODE_1⟧，以及与每个知识事实相关的 PROV-O 元数据。处理一个块
这会产生 20 个关系，并在其基础上产生约 220 个溯源三元组，而知识三元组约为 20 个，这导致了大约 10:1 的开销。


这既成本高昂（存储、索引、传输），又在语义上
不准确。每个片段都由单个 LLM 调用处理，该调用在一个事务中生成
所有其三元组。当前的每个三元组模型
通过制造 20 个独立提取
事件的假象来掩盖这一点。

此外，四个提取处理器中的两个（kg-extract-ontology、
kg-extract-agent）完全没有来源信息，这在审计
跟踪中留下了空白。

## 解决方案

将每个三元组的显式化替换为**子图模型**：每个数据块提取一个溯源记录，该记录在从该数据块生成的所有三元组中共享。



### 术语变更

| 旧术语 | 新术语 |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
| `tg:reifies` (1:1, 相同) | `tg:contains` (1:多, 包含) |

### 目标结构

所有溯源三元组都放入名为 `urn:graph:source` 的命名图中。

```
# Subgraph contains each extracted triple (RDF-star quoted triples)
<subgraph> tg:contains <<s1 p1 o1>> .
<subgraph> tg:contains <<s2 p2 o2>> .
<subgraph> tg:contains <<s3 p3 o3>> .

# Derivation from source chunk
<subgraph> prov:wasDerivedFrom <chunk_uri> .
<subgraph> prov:wasGeneratedBy <activity> .

# Activity: one per chunk extraction
<activity> rdf:type          prov:Activity .
<activity> rdfs:label        "{component_name} extraction" .
<activity> prov:used         <chunk_uri> .
<activity> prov:wasAssociatedWith <agent> .
<activity> prov:startedAtTime "2026-03-13T10:00:00Z" .
<activity> tg:componentVersion "0.25.0" .
<activity> tg:llmModel       "gpt-4" .          # if available
<activity> tg:ontology        <ontology_uri> .   # if available

# Agent: stable per component
<agent> rdf:type   prov:Agent .
<agent> rdfs:label "{component_name}" .
```

### 比较数据量

对于一个产生 N 个提取三元组的模块：

| | 旧方式（每个三元组） | 新方式（子图） |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| 活动三元组 | ~9 x N | ~9 |
| 代理三元组 | 2 x N | 2 |
| 语句/子图元数据 | 2 x N | 2 |
| **总的溯源三元组** | **~13N** | **N + 13** |
| **示例（N=20）** | **~260** | **33** |

## 范围

### 需要更新的处理器（现有溯源，每个三元组）

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

目前，它在每个定义的循环内部调用 `statement_uri()` + `triple_provenance_triples()`。


更改：
将 `subgraph_uri()` 和 `activity_uri()` 的创建移到循环之前。
在循环内部收集 `tg:contains` 三元组。
循环结束后，一次性输出共享的活动/主体/推导块。

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

模式与定义相同。 更改也相同。

### 需要添加的处理器，用于添加来源信息（目前缺失）

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

目前会生成不带来源信息的三元组。添加子图来源信息。
使用相同的模式：每个块一个子图，对于每个提取的三元组使用 `tg:contains`。


**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

目前会生成不带来源信息的三元组。添加子图来源信息。
使用相同的模式。

### 共享来源库的更改

**`trustgraph-base/trustgraph/provenance/triples.py`**

将 `triple_provenance_triples()` 替换为 `subgraph_provenance_triples()`
新函数接受一个提取的三元组列表，而不是单个三元组。
为每个三元组生成一个 `tg:contains`，共享活动/代理块。
移除旧的 `triple_provenance_triples()`

**`trustgraph-base/trustgraph/provenance/uris.py`**

将 `statement_uri()` 替换为 `subgraph_uri()`

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

将 `TG_REIFIES` 替换为 `TG_CONTAINS`

### 不在范围之内

**kg-extract-topics**: 较旧的处理器，目前未在标准流程中使用。
  **kg-extract-rows**: 生成的是行，而不是三元组，具有不同的数据来源模型。
**查询时的数据来源** (⟦CODE_0⟧): 独立的关注点。
  模型
**查询时的数据来源信息** (`urn:graph:retrieval`)：独立的关注点，
  已经使用了不同的模式（提问/探索/聚焦/综合）。
**文档/页面/块的来源**（PDF解码器，分块器）：已经使用了。
  `derived_entity_triples()`，这对于每个实体而言，而不是每个三元组而言，因此没有
  重复的问题。

## 实现说明

### 处理器循环重构

之前（每个三元组，在关系中）：
```python
for rel in rels:
    # ... build relationship_triple ...
    stmt_uri = statement_uri()
    prov_triples = triple_provenance_triples(
        stmt_uri=stmt_uri,
        extracted_triple=relationship_triple,
        ...
    )
    triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

在 (子图) 之后：
```python
sg_uri = subgraph_uri()

for rel in rels:
    # ... build relationship_triple ...
    extracted_triples.append(relationship_triple)

prov_triples = subgraph_provenance_triples(
    subgraph_uri=sg_uri,
    extracted_triples=extracted_triples,
    chunk_uri=chunk_uri,
    component_name=default_ident,
    component_version=COMPONENT_VERSION,
    llm_model=llm_model,
    ontology_uri=ontology_uri,
)
triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

### 新的辅助签名

```python
def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata
    """
```

### 破坏性变更

这是一个对溯源模型的重大更改。
溯源功能尚未发布，因此无需迁移。旧的 `tg:reifies` / `tg:reifies` 代码可以直接删除。
`statement_uri` 代码可以直接删除。
