# 基于实体的知识图谱在 Cassandra 上的存储

## 概述

本文档描述了一种在 Apache Cassandra 上存储 RDF 风格知识图谱的存储模型。该模型采用一种**以实体为中心**的方法，其中每个实体都知道它参与的所有四元组以及它所扮演的角色。这用两个表替换了传统的多表 SPO 组合方法。

## 背景和动机

### 传统方法

在 Cassandra 上，标准的 RDF 四元组存储需要多个反规范化的表来覆盖查询模式，通常需要 6 个或更多的表，这些表代表主语、谓词、宾语和数据集 (SPOD) 的不同组合。每个四元组都会写入到每个表中，从而导致显著的写入放大、运维开销和模式复杂性。

此外，标签解析（用于实体的人类可读名称）需要单独的往返查询，这在 AI 和 GraphRAG 用例中尤其昂贵，因为标签对于 LLM 上下文至关重要。

### 以实体为中心的洞察

每个四元组 `(D, S, P, O)` 涉及最多 4 个实体。通过为每个实体参与四元组的记录创建一个行，我们保证**任何至少包含一个已知元素的查询都会命中分区键**。这使用单个数据表覆盖所有 16 种查询模式。

主要优点：

**2 个表**，而不是 7 个以上
**每个四元组 4 次写入**，而不是 6 次以上
**免费的标签解析**——实体的标签与其关系共存，从而自然地预热应用程序缓存
**所有 16 种查询模式**都由单分区读取提供
**更简单的操作**——只有一个数据表需要调整、压缩和修复

## 模式

### 表 1：quads_by_entity

主要数据表。每个实体都有一个分区，其中包含它参与的所有四元组。该名称反映了查询模式（按实体查找）。

```sql
CREATE TABLE quads_by_entity (
    collection text,       -- Collection/tenant scope (always specified)
    entity     text,       -- The entity this row is about
    role       text,       -- 'S', 'P', 'O', 'G' — how this entity participates
    p          text,       -- Predicate of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    s          text,       -- Subject of the quad
    o          text,       -- Object of the quad
    d          text,       -- Dataset/graph of the quad
    dtype      text,       -- XSD datatype (when otype = 'L'), e.g. 'xsd:string'
    lang       text,       -- Language tag (when otype = 'L'), e.g. 'en', 'fr'
    PRIMARY KEY ((collection, entity), role, p, otype, s, o, d, dtype, lang)
);
```

**分区键 (Partition key)**: `(collection, entity)` — 作用域限定在集合中，每个实体对应一个分区。

**聚类列顺序的理由 (Clustering column order rationale)**:

1. **role** — 大部分查询都以“这个实体是哪个主语/客体”开始。
2. **p** — 下一个最常见的过滤条件，例如“给我所有 `knows` 关系”。
3. **otype** — 允许根据 URI 值与字面值关系进行过滤。
4. **s, o, d** — 剩余的列用于保证唯一性。
5. **dtype, lang** — 区分具有相同值但不同类型元数据的字面值（例如，`"thing"` 与 `"thing"@en` 与 `"thing"^^xsd:string`）。

### 表 2: quads_by_collection

支持集合级别的查询和删除。提供属于某个集合的所有四元组的清单。命名方式反映了查询模式（按集合查找）。

```sql
CREATE TABLE quads_by_collection (
    collection text,
    d          text,       -- Dataset/graph of the quad
    s          text,       -- Subject of the quad
    p          text,       -- Predicate of the quad
    o          text,       -- Object of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    dtype      text,       -- XSD datatype (when otype = 'L')
    lang       text,       -- Language tag (when otype = 'L')
    PRIMARY KEY (collection, d, s, p, o, otype, dtype, lang)
);
```

首先按照数据集进行聚类，从而可以在集合或数据集级别进行删除。 `otype`、`dtype` 和 `lang` 列包含在聚类键中，用于区分具有相同值但不同元数据类型的字面量——在 RDF 中，`"thing"`、`"thing"@en` 和 `"thing"^^xsd:string` 是语义上不同的值。

## 写入路径

对于每个在集合 `C` 中的四元组 `(D, S, P, O)`，需要向 `quads_by_entity` 写入 **4 行**，并向 `quads_by_collection` 写入 **1 行**。

### 示例

假设在集合 `tenant1` 中的四元组是：

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: https://example.org/knows
Object:   https://example.org/Bob
```

将 4 行写入到 `quads_by_entity`：

| collection | entity | role | p | otype | s | o | d |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | G | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Alice | S | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/knows | P | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Bob | O | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |

将 1 行写入到 `quads_by_collection`：

| collection | d | s | p | o | otype | dtype | lang |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | https://example.org/Alice | https://example.org/knows | https://example.org/Bob | U | | |

### 示例

对于一个标签三元组：

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: http://www.w3.org/2000/01/rdf-schema#label
Object:   "Alice Smith" (lang: en)
```

`otype` 是 `'L'`，`dtype` 是 `'xsd:string'`，`lang` 是 `'en'`。 原始值 `"Alice Smith"` 存储在 `o` 中。 `quads_by_entity` 中只需要 3 行，因为没有为原始值作为实体的行，因为原始值不是可以独立查询的实体。

## 查询模式

### 所有 16 种 DSPO 模式

在下表中，“完美前缀”表示查询使用聚类列的连续前缀。“分区扫描 + 过滤”表示 Cassandra 读取一个分区的一部分并在内存中进行过滤，这仍然有效，但不是纯粹的前缀匹配。

| # | 已知 | 查找实体 | 聚类前缀 | 效率 |
|---|---|---|---|---|
| 1 | D,S,P,O | entity=S, role='S', p=P | 完全匹配 | 完美前缀 |
| 2 | D,S,P,? | entity=S, role='S', p=P | 在 D 上过滤 | 分区扫描 + 过滤 |
| 3 | D,S,?,O | entity=S, role='S' | 在 D, O 上过滤 | 分区扫描 + 过滤 |
| 4 | D,?,P,O | entity=O, role='O', p=P | 在 D 上过滤 | 分区扫描 + 过滤 |
| 5 | ?,S,P,O | entity=S, role='S', p=P | 在 O 上过滤 | 分区扫描 + 过滤 |
| 6 | D,S,?,? | entity=S, role='S' | 在 D 上过滤 | 分区扫描 + 过滤 |
| 7 | D,?,P,? | entity=P, role='P' | 在 D 上过滤 | 分区扫描 + 过滤 |
| 8 | D,?,?,O | entity=O, role='O' | 在 D 上过滤 | 分区扫描 + 过滤 |
| 9 | ?,S,P,? | entity=S, role='S', p=P | — | **完美前缀** |
| 10 | ?,S,?,O | entity=S, role='S' | 在 O 上过滤 | 分区扫描 + 过滤 |
| 11 | ?,?,P,O | entity=O, role='O', p=P | — | **完美前缀** |
| 12 | D,?,?,? | entity=D, role='G' | — | **完美前缀** |
| 13 | ?,S,?,? | entity=S, role='S' | — | **完美前缀** |
| 14 | ?,?,P,? | entity=P, role='P' | — | **完美前缀** |
| 15 | ?,?,?,O | entity=O, role='O' | — | **完美前缀** |
| 16 | ?,?,?,? | — | 全扫描 | 仅探索 |

**关键结果：** 15 种非平凡模式中有 7 种是完美的聚类前缀匹配。 剩下的 8 种是单分区读取，并在分区内进行过滤。 包含至少一个已知元素的每个查询都会命中分区键。

模式 16 (?,?,?,?) 在实践中不会出现，因为集合始终是指定的，这将其简化为模式 12。

### 常见查询示例

**关于一个实体的所有信息：**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice';
```

**实体的所有出方向关系：**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S';
```

**特定实体谓词：**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows';
```

**实体标签（特定语言）：**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'http://www.w3.org/2000/01/rdf-schema#label'
AND otype = 'L';
```

然后，如果需要，可以在应用程序端通过 `lang = 'en'` 进行过滤。

**仅限 URI 值的关系（实体到实体的链接）：**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows' AND otype = 'U';
```

**反向查找 — 指向此实体的对象：**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Bob'
AND role = 'O';
```

## 标签解析和缓存预热

实体中心模型最显著的优势之一是，**标签解析成为一个免费的副作用**。

在传统的基于多表的模型中，获取标签需要单独的轮询查询：检索三元组，识别结果中的实体 URI，然后为每个 URI 获取 `rdfs:label`。 这种 N+1 模式非常昂贵。

在实体中心模型中，查询一个实体会返回其**所有**四元组，包括其标签、类型和其他属性。 当应用程序缓存查询结果时，标签会在任何客户端请求之前被预热。

两种使用模式证实了这在实践中效果良好：

**面向用户的查询**：结果集通常很小，标签至关重要。 实体读取会预热缓存。
**AI/批量查询**：结果集很大，但有严格的限制。 标签要么是不必要的，要么只需要用于已缓存的实体子集。

解决大型结果集（例如 30,000 个实体）的标签的理论问题，可以通过实际观察来缓解，即没有人类或 AI 消费者能够有效地处理如此多的标签。 应用程序级别的查询限制可确保缓存压力保持在可管理范围内。

## 宽分区和重构

重构（RDF-star 风格的关于语句的语句）会创建中心实体，例如，一个源文档支持数千个提取的事实。 这可能会导致宽分区。

缓解因素：

**应用程序级别的查询限制**：所有 GraphRAG 和面向用户的查询都强制执行严格的限制，因此宽分区永远不会在热读取路径上被完全扫描。
**Cassandra 可以高效地执行部分读取**：即使在大型分区上，具有早期停止的聚类列扫描也是快速的。
**集合删除**（唯一可能遍历整个分区的操作）是一个可接受的后台过程。

## 集合删除

由 API 调用触发，在后台运行（最终一致）。

1. 读取 `quads_by_collection` 以获取目标集合的所有四元组
2. 从四元组中提取唯一的实体（s、p、o、d 值）
3. 对于每个唯一的实体，从 `quads_by_entity` 中删除该分区
4. 从 `quads_by_collection` 中删除行

`quads_by_collection` 表提供了用于定位所有实体分区而无需进行全表扫描所需的索引。 由于 `(collection, entity)` 是分区键，因此分区级别的删除是高效的。

## 从多表模型迁移的路径

在迁移过程中，实体中心模型可以与现有的多表模型共存：

1. 将 `quads_by_entity` 和 `quads_by_collection` 表与现有表一起部署
2. 同时将新的四元组写入旧表和新表
3. 将现有数据回填到新表中
4. 每次迁移一种查询模式
5. 在迁移所有读取路径后，停用旧表

## 总结

| 方面 | 传统 (6 个表) | 实体中心 (2 个表) |
|---|---|---|
| 表 | 7+ | 2 |
| 每个四元组的写入次数 | 6+ | 5 (4 个数据 + 1 个清单) |
| 标签解析 | 单独的轮询 | 通过缓存预热免费 |
| 查询模式 | 6 个表中的 16 种 | 1 个表中的 16 种 |
| 模式复杂性 | 高 | 低 |
| 运维开销 | 6 个表需要调整/修复 | 1 个数据表 |
| 重构支持 | 额外的复杂性 | 完美契合 |
| 对象类型过滤 | 不可用 | 原生 (通过 otype 聚类) |
输出合同（必须严格遵守以下格式）：
