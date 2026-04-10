# 提取时的数据来源：源层

## 概述

本文档记录了关于提取时数据来源的笔记，用于未来的规范工作。提取时的数据来源记录了数据的“源层”，即数据最初来自哪里，以及它是如何提取和转换的。

这与查询时的数据来源（参见 `query-time-provenance.md`）不同，后者记录的是代理推理过程。

## 问题陈述

### 当前实现

目前，数据来源的工作方式如下：
文档元数据以 RDF 三元组的形式存储在知识图谱中。
文档 ID 将元数据与文档关联起来，因此文档在图中显示为节点。
当从文档中提取出边（关系/事实）时，一个 `subjectOf` 关系将提取出的边链接回原始文档。

### 当前方法的缺点

1. **重复加载元数据：** 文档元数据会被打包并重复加载，每次从该文档中提取一批三元组时都会重复。这既浪费又冗余，相同的元数据会作为“货物”随每次提取输出一起传输。

2. **浅层数据来源：** 当前的 `subjectOf` 关系仅将事实直接链接到顶级文档。无法了解转换链，例如，该事实来自哪个页面，哪个块，使用了哪种提取方法。

### 期望状态

1. **一次加载元数据：** 文档元数据应该只加载一次，并附加到顶级文档节点，而不是重复包含在每个三元组批次中。

2. **丰富的数据来源 DAG：** 捕获从原始文档到所有中间工件，再到提取出的事实的完整转换链。例如，一个 PDF 文档的转换过程：

   ```
   PDF file (source document with metadata)
     → Page 1 (decoded text)
       → Chunk 1
         → Extracted edge/fact (via subjectOf)
         → Extracted edge/fact
       → Chunk 2
         → Extracted edge/fact
     → Page 2
       → Chunk 3
         → ...
   ```

3. **统一存储：** 提取的知识及其来源信息（provenance）都存储在同一个知识图谱中。这使得对来源信息的查询方式与对知识的查询方式相同，即可以从任何事实出发，沿着链条追溯到其确切的来源位置。

4. **稳定的ID：** 每个中间产物（页面、段落）都具有一个稳定的ID，该ID在图中表示为一个节点。

5. **父子链接：** 从派生文档到其父文档，一直链接到顶层源文档，使用一致的关系类型。

6. **精确的事实归属：** 提取的边上的 `subjectOf` 关系指向直接的父节点（段落），而不是顶层文档。可以通过遍历DAG来恢复完整的来源信息。

## 用例

### UC1：GraphRAG响应中的来源归属

**场景：** 用户运行GraphRAG查询，并从代理接收到响应。

**流程：**
1. 用户向GraphRAG代理提交查询。
2. 代理从知识图谱中检索相关的事实，以构建响应。
3. 根据查询时期的来源信息规范，代理报告哪些事实对响应做出了贡献。
4. 每个事实通过来源信息DAG链接到其源段落。
5. 段落链接到页面，页面链接到源文档。

**用户体验结果：** 界面会显示LLM响应以及来源归属信息。用户可以：
查看哪些事实支持了响应。
从事实 → 段落 → 页面 → 文档进行深入了解。
浏览原始的源文档以验证声明。
准确了解事实的来源（哪个页面，哪个部分）。

**价值：** 用户可以根据原始来源验证AI生成的响应，从而建立信任并实现事实核查。

### UC2：调试提取质量

某个事实看起来不正确。追溯到段落 → 页面 → 文档，查看原始文本。是提取出现问题，还是原始来源本身就是错误的？

### UC3：增量重提取

源文档已更新。哪些段落/事实是从它派生的？仅使这些段落/事实失效并重新生成，而不是重新处理所有内容。

### UC4：数据删除/被遗忘的权利

必须删除一个源文档（GDPR、法律等）。遍历DAG以查找并删除所有派生的事实。

### UC5：冲突解决

两个事实相互矛盾。追溯到它们的来源，以了解原因并决定应该信任哪个（更权威的来源、更新的来源等）。

### UC6：来源权威性加权

某些来源比其他来源更具权威性。可以根据其原始文档的权威性/质量对事实进行加权或过滤。

### UC7：提取管道比较

比较来自不同提取方法/版本的输出。哪个提取器从相同的来源生成了更好的事实？

## 集成点

### Librarian

librarian组件已经提供了文档存储，并具有唯一的文档ID。来源信息系统与此现有的基础设施集成。

#### 现有功能（已实现）

**父子文档链接：**
`parent_id` 字段在 `DocumentMetadata` 中 - 将子文档链接到父文档。
`document_type` 字段 - 值：`"source"`（原始）或 `"extracted"`（派生）。
`add-child-document` API - 创建具有自动 `document_type = "extracted"` 的子文档。
`list-children` API - 检索父文档的所有子文档。
级联删除 - 删除父文档会自动删除所有子文档。

**文档识别：**
文档ID由客户端指定（不是自动生成）。
文档按复合 `(user, document_id)` 在Cassandra中键入。
对象ID（UUID）在内部生成，用于blob存储。

**元数据支持：**
`metadata: list[Triple]` 字段 - RDF三元组用于结构化元数据。
`title`、`comments`、`tags` - 基本文档元数据。
`time` - 时间戳，`kind` - MIME类型。

**存储架构：**
元数据存储在Cassandra中（`librarian` 键空间，`document` 表）。
内容存储在MinIO/S3 blob存储中（`library` 存储桶）。
智能内容交付：小于 2MB 的文档嵌入，较大的文档流式传输。

#### 关键文件

`trustgraph-flow/trustgraph/librarian/librarian.py` - 核心 librarian 操作。
`trustgraph-flow/trustgraph/librarian/service.py` - 服务处理器，文档加载。
`trustgraph-flow/trustgraph/tables/library.py` - Cassandra 表存储。
`trustgraph-base/trustgraph/schema/services/library.py` - 模式定义。

#### 需要解决的问题

librarian 具有构建块，但目前：
1. 父子链接仅限于一级深度 - 没有多级DAG遍历辅助功能。
2. 没有标准的关系类型词汇表（例如，`derivedFrom`、`extractedFrom`）。
3. 来源信息元数据（提取方法、置信度、段落位置）尚未标准化。
4. 没有查询API来遍历从事实到源的全程来源信息链。

## 端到端流程设计

管道中的每个处理器都遵循一致的模式：
从上游接收文档ID。
从librarian中获取内容。
生成子产物。
对于每个子产物：保存到librarian，向图发出边，将ID转发到下游。

### 处理流程

有两个流程，具体取决于文档类型：

#### PDF文档流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID to PDF extractor                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PDF Extractor (per page)                                                │
│   1. Fetch PDF content from librarian using document ID                 │
│   2. Extract pages as text                                              │
│   3. For each page:                                                     │
│      a. Save page as child document in librarian (parent = root doc)   │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send page document ID to chunker                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch page content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = page)      │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          Post-chunker optimization: messages carry both
          chunk ID (for provenance) and content (to avoid
          librarian round-trip). Chunks are small (2-4KB).
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor (per chunk)                                         │
│   1. Receive chunk ID + content directly (no librarian fetch needed)   │
│   2. Extract facts/triples and embeddings from chunk content            │
│   3. For each triple:                                                   │
│      a. Emit triple to knowledge graph                                  │
│      b. Emit reified edge linking triple → chunk ID (edge pointing     │
│         to edge - first use of reification support)                     │
│   4. For each embedding:                                                │
│      a. Emit embedding with its entity ID                               │
│      b. Link entity ID → chunk ID in knowledge graph                   │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 文本文档流程

文本文档会跳过 PDF 提取器，直接进入分块处理：

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID directly to chunker (skip PDF extractor)    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch text content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = root doc) │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor                                                     │
│   (same as PDF flow)                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

结果生成的有向无环图（DAG）的层数减少了一层：

```
PDF:  Document → Pages → Chunks → Triples/Embeddings
Text: Document → Chunks → Triples/Embeddings
```

该设计同时适用于这两种情况，因为分块器以通用方式处理其输入 - 它使用接收到的任何文档 ID 作为父级，无论该 ID 是源文档还是页面。

### 元数据模式 (PROV-O)

溯源元数据使用 W3C PROV-O 本体。这提供了一个标准词汇表，并为未来提取输出的签名/身份验证提供了支持。

#### PROV-O 核心概念

| PROV-O 类型 | TrustGraph 用法 |
|-------------|------------------|
| `prov:Entity` | 文档、页面、块、三元组、嵌入 |
| `prov:Activity` | 提取操作的实例 |
| `prov:Agent` | TG 组件（PDF 提取器、分块器等）及其版本 |

#### PROV-O 关系

| 谓词 | 含义 | 示例 |
|-----------|---------|---------|
| `prov:wasDerivedFrom` | 一个实体源自另一个实体 | 页面 wasDerivedFrom 文档 |
| `prov:wasGeneratedBy` | 一个实体由一个活动生成 | 页面 wasGeneratedBy PDFExtractionActivity |
| `prov:used` | 一个活动使用一个实体作为输入 | PDFExtractionActivity used Document |
| `prov:wasAssociatedWith` | 一个活动由一个代理执行 | PDFExtractionActivity wasAssociatedWith tg:PDFExtractor |

#### 每个级别的元数据

**源文档（由 Librarian 产生）：**
```
doc:123 a prov:Entity .
doc:123 dc:title "Research Paper" .
doc:123 dc:source <https://example.com/paper.pdf> .
doc:123 dc:date "2024-01-15" .
doc:123 dc:creator "Author Name" .
doc:123 tg:pageCount 42 .
doc:123 tg:mimeType "application/pdf" .
```

**页面 (由 PDF 提取器生成):**
```
page:123-1 a prov:Entity .
page:123-1 prov:wasDerivedFrom doc:123 .
page:123-1 prov:wasGeneratedBy activity:pdf-extract-456 .
page:123-1 tg:pageNumber 1 .

activity:pdf-extract-456 a prov:Activity .
activity:pdf-extract-456 prov:used doc:123 .
activity:pdf-extract-456 prov:wasAssociatedWith tg:PDFExtractor .
activity:pdf-extract-456 tg:componentVersion "1.2.3" .
activity:pdf-extract-456 prov:startedAtTime "2024-01-15T10:30:00Z" .
```

**块 (由分块器发出):**
```
chunk:123-1-1 a prov:Entity .
chunk:123-1-1 prov:wasDerivedFrom page:123-1 .
chunk:123-1-1 prov:wasGeneratedBy activity:chunk-789 .
chunk:123-1-1 tg:chunkIndex 1 .
chunk:123-1-1 tg:charOffset 0 .
chunk:123-1-1 tg:charLength 2048 .

activity:chunk-789 a prov:Activity .
activity:chunk-789 prov:used page:123-1 .
activity:chunk-789 prov:wasAssociatedWith tg:Chunker .
activity:chunk-789 tg:componentVersion "1.0.0" .
activity:chunk-789 tg:chunkSize 2048 .
activity:chunk-789 tg:chunkOverlap 200 .
```

**强调 (由知识提取器发出):**
```
# The extracted triple (edge)
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph containing the extracted triples
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 prov:wasGeneratedBy activity:extract-999 .

activity:extract-999 a prov:Activity .
activity:extract-999 prov:used chunk:123-1-1 .
activity:extract-999 prov:wasAssociatedWith tg:KnowledgeExtractor .
activity:extract-999 tg:componentVersion "2.1.0" .
activity:extract-999 tg:llmModel "claude-3" .
activity:extract-999 tg:ontology <http://example.org/ontologies/business-v1> .
```

**嵌入 (存储在向量存储中，而不是三元组存储中):**

嵌入存储在向量存储中，包含元数据，而不是作为 RDF 三元组。每个嵌入记录包含：

| 字段 | 描述 | 示例 |
|-------|-------------|---------|
| vector | 嵌入向量 | [0.123, -0.456, ...] |
| entity | 嵌入所代表的节点 URI | `entity:JohnSmith` |
| chunk_id | 源块 (来源) | `chunk:123-1-1` |
| model | 使用的嵌入模型 | `text-embedding-ada-002` |
| component_version | TG 嵌入器版本 | `1.0.0` |

`entity` 字段将嵌入链接到知识图谱 (节点 URI)。 `chunk_id` 字段提供回溯到源块的来源信息，从而可以向上遍历 DAG，到达原始文档。

#### TrustGraph 命名空间扩展

在 `tg:` 命名空间下，定义了用于提取特定元数据的自定义谓词：

| 谓词 | 域 | 描述 |
|-----------|--------|-------------|
| `tg:contains` | Subgraph | 指向此提取子图中包含的三元组 |
| `tg:pageCount` | Document | 源文档中的总页数 |
| `tg:mimeType` | Document | 源文档的 MIME 类型 |
| `tg:pageNumber` | Page | 源文档中的页码 |
| `tg:chunkIndex` | Chunk | 父级中的块索引 |
| `tg:charOffset` | Chunk | 父级文本中的字符偏移量 |
| `tg:charLength` | Chunk | 块的字符长度 |
| `tg:chunkSize` | Activity | 配置的块大小 |
| `tg:chunkOverlap` | Activity | 配置的块之间的重叠 |
| `tg:componentVersion` | Activity | TG 组件的版本 |
| `tg:llmModel` | Activity | 用于提取的 LLM |
| `tg:ontology` | Activity | 用于指导提取的本体 URI |
| `tg:embeddingModel` | Activity | 用于嵌入的模型 |
| `tg:sourceText` | Statement | 从提取的三元组的精确文本 |
| `tg:sourceCharOffset` | Statement | 源文本在块中的字符偏移量 |
| `tg:sourceCharLength` | Statement | 源文本的字符长度 |

#### 词汇引导 (每个集合)

知识图谱是本体无关的，并且初始化为空。 当首次将 PROV-O provenance 数据写入集合时，必须使用 RDF 标签引导所有类和谓词的词汇。 这可确保在查询和 UI 中提供人类可读的显示。

**PROV-O 类:**
```
prov:Entity rdfs:label "Entity" .
prov:Activity rdfs:label "Activity" .
prov:Agent rdfs:label "Agent" .
```

**PROV-O谓词：**
```
prov:wasDerivedFrom rdfs:label "was derived from" .
prov:wasGeneratedBy rdfs:label "was generated by" .
prov:used rdfs:label "used" .
prov:wasAssociatedWith rdfs:label "was associated with" .
prov:startedAtTime rdfs:label "started at" .
```

**TrustGraph谓词：**
```
tg:contains rdfs:label "contains" .
tg:pageCount rdfs:label "page count" .
tg:mimeType rdfs:label "MIME type" .
tg:pageNumber rdfs:label "page number" .
tg:chunkIndex rdfs:label "chunk index" .
tg:charOffset rdfs:label "character offset" .
tg:charLength rdfs:label "character length" .
tg:chunkSize rdfs:label "chunk size" .
tg:chunkOverlap rdfs:label "chunk overlap" .
tg:componentVersion rdfs:label "component version" .
tg:llmModel rdfs:label "LLM model" .
tg:ontology rdfs:label "ontology" .
tg:embeddingModel rdfs:label "embedding model" .
tg:sourceText rdfs:label "source text" .
tg:sourceCharOffset rdfs:label "source character offset" .
tg:sourceCharLength rdfs:label "source character length" .
```

**实施说明：** 这个词汇库初始化应该具有幂等性，即可以多次运行而不会创建重复项。 它可以触发在集合中的第一个文档处理过程中，或者作为单独的集合初始化步骤。

#### 子块来源信息（期望）

为了获得更细粒度的来源信息，记录三元组是从块中的哪个位置提取出来的将非常有用。 这可以实现：

在用户界面中突出显示确切的原始文本
验证提取的准确性与原始文本
在句子级别调试提取质量

**带有位置跟踪的示例：**
```
# The extracted triple
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph with sub-chunk provenance
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
subgraph:001 tg:sourceCharOffset 1547 .
subgraph:001 tg:sourceCharLength 46 .
```

**带有文本范围的示例（备选方案）：**
```
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceRange "1547-1593" .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
```

**实现注意事项：**

基于 LLM 的提取可能无法自然地提供字符位置。
可以提示 LLM 在提取的三元组旁边返回原始句子/短语。
或者，可以进行后处理，将提取的实体模糊匹配回原始文本。
提取复杂度和溯源粒度之间的权衡。
使用结构化提取方法可能更容易实现，而不是使用自由形式的 LLM 提取。

这被标记为期望目标 - 首先应实现基本的块级溯源，如果可行，子块跟踪可以作为未来的增强功能。

### 双重存储模型

溯源 DAG 是随着文档在流水线中流动而逐步构建的：

| 存储 | 存储内容 | 目的 |
|-------|---------------|---------|
| Librarian | 文档内容 + 父子链接 | 内容检索、级联删除 |
| Knowledge Graph | 父子边 + 元数据 | 溯源查询、事实归属 |

两个存储都维护相同的 DAG 结构。 Librarian 存储内容；Graph 存储关系，并支持遍历查询。

### 关键设计原则

1. **文档 ID 作为流动的单位** - 处理程序传递 ID，而不是内容。 需要时从 Librarian 检索内容。

2. **在源头一次发出** - 元数据在处理开始时写入到 Graph 中，而不是在下游重复。

3. **一致的处理程序模式** - 每个处理程序都遵循相同的接收/检索/生成/保存/发出/转发模式。

4. **渐进的 DAG 构建** - 每个处理程序添加其级别到 DAG 中。 完整的溯源链是逐步构建的。

5. **分块后优化** - 在分块之后，消息同时携带 ID 和内容。 块很小（2-4KB），因此包含内容可以避免不必要的 Librarian 往返，同时通过 ID 保持溯源。

## 实现任务

### Librarian 更改

#### 当前状态

通过将文档 ID 发送到第一个处理程序来启动文档处理。
没有连接到三元存储 - 元数据与提取输出一起打包。
`add-child-document` 创建一级父子链接。
`list-children` 仅返回直接子节点。

#### 需要的更改

**1. 新接口：三元存储连接**

Librarian 需要直接将文档元数据边发射到知识图谱，以在启动处理时进行操作。
向 Librarian 服务添加三元存储客户端/发布器。
在处理启动时：以图谱边的方式（一次）发射根文档元数据。

**2. 文档类型词汇表**

标准化子文档的 `document_type` 值：
`source` - 原始上传的文档。
`page` - 从源头提取的页面（PDF 等）。
`chunk` - 从页面或源头派生的文本块。

#### 接口更改摘要

| 接口 | 更改 |
|-----------|--------|
| 三元存储 | 新的出站连接 - 发射文档元数据边 |
| 处理启动 | 在转发文档 ID 之前，向图谱发射元数据 |

### PDF 提取器更改

#### 当前状态

接收文档内容（或流式传输大型文档）。
从 PDF 页面提取文本。
将页面内容转发到分块器。
没有与 Librarian 或三元存储交互。

#### 需要的更改

**1. 新接口：Librarian 客户端**

PDF 提取器需要将每个页面作为子文档保存到 Librarian 中。
向 PDF 提取器服务添加 Librarian 客户端。
对于每个页面：使用父文档 ID 调用 `add-child-document`。

**2. 新接口：三元存储连接**

PDF 提取器需要将父子边发射到知识图谱。
添加三元存储客户端/发布器。
对于每个页面：发射一个链接页面文档到父文档的边。

**3. 更改输出格式**

而是直接转发页面内容，而是转发页面文档 ID。
Chunker 将使用 ID 从 librarian 获取内容

#### 接口变更摘要

| 接口 | 变更 |
|-----------|--------|
| Librarian | 新的输出 - 保存子文档 |
| Triple store | 新的输出 - 发射父子边 |
| 输出消息 | 从内容更改为文档 ID |

### Chunker 变更

#### 当前状态

接收页面/文本内容
分割成块
将块内容转发到下游处理器
不与 librarian 或 triple store 交互

#### 必需的变更

**1. 更改输入处理**

接收文档 ID 而不是内容，从 librarian 获取。
向 chunker 服务添加 librarian 客户端
使用文档 ID 获取页面内容

**2. 新接口：Librarian 客户端（写入）**

将每个块保存为 librarian 中的子文档。
对于每个块：使用 parent = 页面文档 ID 调用 `add-child-document`

**3. 新接口：Triple store 连接**

向知识图谱发射父子边。
添加 triple store 客户端/发布器
对于每个块：发射链接块文档到页面文档的边

**4. 更改输出格式**

同时转发块文档 ID 和块内容（块处理后的优化）。
下游处理器接收 ID 用于溯源 + 用于处理的内容

#### 接口变更摘要

| 接口 | 变更 |
|-----------|--------|
| 输入消息 | 从内容更改为文档 ID |
| Librarian | 新的输出（读取 + 写入）- 获取内容，保存子文档 |
| Triple store | 新的输出 - 发射父子边 |
| 输出消息 | 从仅包含内容更改为 ID + 内容 |

### Knowledge Extractor 变更

#### 当前状态

接收块内容
提取三元组和嵌入
发送到 triple store 和 embedding store
`subjectOf` 关系指向顶级文档（不是块）

#### 必需的变更

**1. 更改输入处理**

接收块文档 ID 以及内容。
使用块 ID 用于溯源链接（内容已包含在优化中）

**2. 更新三元组溯源**

将提取的三元组链接到块（而不是顶级文档）。
使用重构来创建指向边的边
`subjectOf` 关系：三元组 → 块文档 ID
首次使用现有的重构支持

**3. 更新嵌入溯源**

将嵌入实体 ID 链接到块。
发射边：嵌入实体 ID → 块文档 ID

#### 接口变更摘要

| 接口 | 变更 |
|-----------|--------|
| 输入消息 | 期望块 ID + 内容（不是仅包含内容） |
| Triple store | 使用重构进行三元组 → 块溯源 |
| 嵌入溯源 | 将实体 ID 链接到块 ID |

## 引用

查询时溯源：`docs/tech-specs/query-time-provenance.md`
PROV-O 标准用于溯源建模
知识图谱中现有的源元数据（需要审计）
