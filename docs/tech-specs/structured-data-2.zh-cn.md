# 结构化数据技术规范 (第二部分)

## 概述

本规范解决了在 TrustGraph 结构化数据集成初始实施过程中发现的问题和差距，如 `structured-data.md` 中所述。

## 问题陈述

### 1. 命名不一致："对象" 与 "行"

当前实现方案在整个代码中使用 "对象" 术语 (例如，`ExtractedObject`，对象提取，对象嵌入)。 这种命名方式过于通用，容易造成混淆：

"对象" 在软件中是一个 overloaded 的术语 (Python 对象，JSON 对象等)。
正在处理的数据本质上是表格数据，即具有定义模式的表格中的行。
"行" 更准确地描述了数据模型，并且与数据库术语一致。

这种不一致性出现在模块名称、类名称、消息类型和文档中。

### 2. 行存储查询限制

当前的行存储实现方案存在重大的查询限制：

**自然语言匹配问题**: 查询难以处理真实世界数据的变化。 例如：
很难在包含 `"CHESTNUT ST"` 的街道数据库中找到关于 `"Chestnut Street"` 的信息。
缩写、大小写差异和格式变化会破坏精确匹配查询。
用户期望语义理解，但存储系统只提供字面匹配。

**模式演化问题**: 更改模式会导致问题：
现有数据可能不符合更新后的模式。
表结构的变化可能会破坏查询和数据完整性。
没有明确的模式更新迁移路径。

### 3. 需要行嵌入

与问题 2 相关，系统需要行数据的向量嵌入，以便：

在结构化数据上进行语义搜索 (找到 "Chestnut Street" 时，数据包含 "CHESTNUT ST")。
模糊查询的相似性匹配。
结合结构化过滤器和语义相似性的混合搜索。
更好的自然语言查询支持。

嵌入服务已指定，但尚未实施。

### 4. 行数据摄取不完整

结构化数据摄取管道尚未完全投入使用：

存在诊断提示，用于对输入格式进行分类 (CSV，JSON 等)。
使用这些提示的摄取服务尚未集成到系统中。
没有将预结构化数据加载到行存储的端到端路径。

## 目标

**模式灵活性**: 允许模式演化，而不会破坏现有数据或需要迁移。
**命名一致性**: 在整个代码库中采用 "行" 术语。
**语义可查询性**: 通过行嵌入支持模糊/语义匹配。
**完整的摄取管道**: 提供将结构化数据加载到存储的端到端路径。

## 技术设计

### 统一的行存储模式

之前的实现方案为每个模式创建了一个单独的 Cassandra 表。 这在模式演化时会导致问题，因为表结构的变化需要迁移。

新的设计使用一个统一的表来存储所有行数据：

```sql
CREATE TABLE rows (
    collection text,
    schema_name text,
    index_name text,
    index_value frozen<list<text>>,
    data map<text, text>,
    source text,
    PRIMARY KEY ((collection, schema_name, index_name), index_value)
)
```

#### 列定义

| 列 | 类型 | 描述 |
|--------|------|-------------|
| `collection` | `text` | 数据收集/导入标识符（来自元数据）|
| `schema_name` | `text` | 此行所遵循的模式名称 |
| `index_name` | `text` | 索引字段名称，以逗号分隔的字符串表示复合索引 |
| `index_value` | `frozen<list<text>>` | 索引值列表 |
| `data` | `map<text, text>` | 行数据，以键值对形式存储 |
| `source` | `text` | 可选的 URI，链接到知识图谱中的来源信息。空字符串或 NULL 表示没有来源。|

#### 索引处理

每行数据会被存储多次，对于模式中定义的每个索引字段，都会存储一次。主键字段被视为索引，没有特殊的标记，以提供未来的灵活性。

**单字段索引示例：**
模式定义 `email` 为索引
`index_name = "email"`
`index_value = ['foo@bar.com']`

**复合索引示例：**
模式定义在 `region` 和 `status` 上创建复合索引
`index_name = "region,status"` (字段名称按排序方式连接)
`index_value = ['US', 'active']` (值与字段名称的顺序相同)

**主键示例：**
模式定义 `customer_id` 为主键
`index_name = "customer_id"`
`index_value = ['CUST001']`

#### 查询模式

无论使用哪个索引，所有查询都遵循相同的模式：

```sql
SELECT * FROM rows
WHERE collection = 'import_2024'
  AND schema_name = 'customers'
  AND index_name = 'email'
  AND index_value = ['foo@bar.com']
```

#### 设计权衡

**优点：**
模式更改不需要更改表结构
行数据对 Cassandra 隐藏 - 字段的添加/删除是透明的
所有访问方法都具有一致的查询模式
不需要 Cassandra 的二级索引（这在大型环境中可能会很慢）
整个过程中都使用 Cassandra 的原生类型（`map`，`frozen<list>`）

**权衡：**
写入放大：每个行插入 = N 次插入（每个索引字段一次）
重复行数据带来的存储开销
类型信息存储在模式配置中，应用程序层进行转换

#### 一致性模型

该设计接受某些简化：

1. **没有行更新**：系统是只追加的。这消除了关于更新同一行的多个副本的一致性问题。

2. **模式更改容错性**：当模式发生更改（例如，添加/删除索引）时，现有行保留其原始索引。旧行将无法通过新索引发现。如果需要，用户可以删除并重新创建模式以确保一致性。

### 分区跟踪和删除

#### 问题

借助分区键 `(collection, schema_name, index_name)`，高效删除需要知道所有要删除的分区键。仅通过 `collection` 或 `collection + schema_name` 删除需要知道所有具有数据的 `index_name` 值。

#### 分区跟踪表

一个辅助查找表跟踪哪些分区存在：

```sql
CREATE TABLE row_partitions (
    collection text,
    schema_name text,
    index_name text,
    PRIMARY KEY ((collection), schema_name, index_name)
)
```

这使得能够高效地发现用于删除操作的分区。

#### 行写入器行为

行写入器维护一个已注册的 `(collection, schema_name)` 对的内存缓存。 在处理一行时：

1. 检查 `(collection, schema_name)` 是否在缓存中
2. 如果未缓存（对于此对的第一个行）：
   查找模式配置以获取所有索引名称
   将条目插入到 `row_partitions` 中，对于每个 `(collection, schema_name, index_name)`
   将该对添加到缓存中
3. 继续写入行数据

行写入器还监视模式配置更改事件。 当模式发生更改时，相关的缓存条目将被清除，以便下一行触发使用更新的索引名称重新注册。

这种方法确保：
查找表写入仅针对每个 `(collection, schema_name)` 对发生一次，而不是针对每行。
查找表反映了数据写入时活动的索引。
导入过程中发生的模式更改可以正确处理。

#### 删除操作

**删除集合：**
```sql
-- 1. Discover all partitions
SELECT schema_name, index_name FROM row_partitions WHERE collection = 'X';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = '...' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table
DELETE FROM row_partitions WHERE collection = 'X';
```

**删除集合 + 模式：**
```sql
-- 1. Discover partitions for this schema
SELECT index_name FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = 'Y' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table entries
DELETE FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';
```

### 行嵌入

行嵌入允许对索引值进行语义/模糊匹配，从而解决自然语言不匹配的问题（例如，在搜索“Chestnut Street”时找到“CHESTNUT ST”）。

#### 设计概述

每个索引值都会被嵌入，并存储在向量存储中（Qdrant）。在查询时，查询内容也会被嵌入，找到相似的向量，然后使用相关的元数据来查找 Cassandra 中的实际行。

#### Qdrant 集合结构

每个 `(user, collection, schema_name, dimension)` 元组对应一个 Qdrant 集合：

**集合命名：** `rows_{user}_{collection}_{schema_name}_{dimension}`
名称会被清理（非字母数字字符替换为 `_`，转换为小写，数字前缀添加 `r_` 前缀）
**理由：** 允许通过删除匹配的 Qdrant 集合来干净地删除一个 `(user, collection, schema_name)` 实例；维度后缀允许不同的嵌入模型共存。

#### 哪些内容会被嵌入

索引值的文本表示：

| 索引类型 | 示例 `index_value` | 要嵌入的文本 |
|------------|----------------------|---------------|
| 单字段 | `['foo@bar.com']` | `"foo@bar.com"` |
| 组合 | `['US', 'active']` | `"US active"` (空格连接) |

#### 点结构

每个 Qdrant 点包含：

```json
{
  "id": "<uuid>",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "index_name": "street_name",
    "index_value": ["CHESTNUT ST"],
    "text": "CHESTNUT ST"
  }
}
```

| Payload Field | Description |
|---------------|-------------|
| `index_name` | 此嵌入所代表的索引字段。|
| `index_value` | 原始值列表（用于 Cassandra 查找）。|
| `text` | 嵌入的文本（用于调试/显示）。|

注意：`user`、`collection` 和 `schema_name` 可以从 Qdrant 集合名称中推断出来。|

#### 查询流程

1. 用户查询用户 U、集合 X、模式 Y 中的“Chestnut Street”。|
2. 嵌入查询文本。|
3. 确定与前缀 `rows_U_X_Y_` 匹配的 Qdrant 集合名称。|
4. 在匹配的 Qdrant 集合中搜索最接近的向量。|
5. 获取包含 `index_name` 和 `index_value` 的有效负载的匹配点。|
6. 查询 Cassandra：|
   ```sql
   SELECT * FROM rows
   WHERE collection = 'X'
     AND schema_name = 'Y'
     AND index_name = '<from payload>'
     AND index_value = <from payload>
   ```
7. 返回匹配的行

#### 可选：按索引名称过滤

查询可以选择性地按 `index_name` 进行过滤，以便在 Qdrant 中仅搜索特定字段：

**"查找所有匹配 'Chestnut' 的字段"** → 搜索集合中的所有向量
**"查找 'Chestnut' 匹配的 street_name"** → 过滤 `payload.index_name = 'street_name'`

#### 架构

行嵌入遵循 GraphRAG 使用的 **两阶段模式**（图嵌入、文档嵌入）：

**第一阶段：嵌入计算** (`trustgraph-flow/trustgraph/embeddings/row_embeddings/`) - 消耗 `ExtractedObject`，通过嵌入服务计算嵌入，输出 `RowEmbeddings`
**第二阶段：嵌入存储** (`trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/`) - 消耗 `RowEmbeddings`，将向量写入 Qdrant

Cassandra 行写入器是一个独立的并行消费者：

**Cassandra 行写入器** (`trustgraph-flow/trustgraph/storage/rows/cassandra`) - 消耗 `ExtractedObject`，将行写入 Cassandra

所有三个服务都从同一个流中读取，从而使它们彼此解耦。 这允许：
独立地扩展 Cassandra 写入与嵌入生成与向量存储
如果不需要，可以禁用嵌入服务
一个服务中的故障不会影响其他服务
与 GraphRAG 管道保持一致的架构

#### 写入路径

**第一阶段（行嵌入处理器）：** 接收到 `ExtractedObject` 时：

1. 查找模式以找到索引字段
2. 对于每个索引字段：
   构建索引值的文本表示
   通过嵌入服务计算嵌入
3. 输出一个包含所有计算向量的 `RowEmbeddings` 消息

**第二阶段（行嵌入-写入-Qdrant）：** 接收到 `RowEmbeddings` 时：

1. 对于消息中的每个嵌入：
   从 `(user, collection, schema_name, dimension)` 确定 Qdrant 集合
   如果需要，创建集合（首次写入时延迟创建）
   使用向量和有效载荷进行更新

#### 消息类型

```python
@dataclass
class RowIndexEmbedding:
    index_name: str              # The indexed field name(s)
    index_value: list[str]       # The field value(s)
    text: str                    # Text that was embedded
    vectors: list[list[float]]   # Computed embedding vectors

@dataclass
class RowEmbeddings:
    metadata: Metadata
    schema_name: str
    embeddings: list[RowIndexEmbedding]
```

#### 删除集成

Qdrant 集合通过在集合名称模式上进行前缀匹配来发现：

**删除 `(user, collection)`：**
1. 列出所有与前缀 `rows_{user}_{collection}_` 匹配的 Qdrant 集合
2. 删除每个匹配的集合
3. 删除 Cassandra 行分区（如上文所述）
4. 清理 `row_partitions` 条目

**删除 `(user, collection, schema_name)`：**
1. 列出所有与前缀 `rows_{user}_{collection}_{schema_name}_` 匹配的 Qdrant 集合
2. 删除每个匹配的集合（处理多个维度）
3. 删除 Cassandra 行分区
4. 清理 `row_partitions`

#### 模块位置

| 阶段 | 模块 | 入口点 |
|-------|--------|-------------|
| 阶段 1 | `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | `row-embeddings` |
| 阶段 2 | `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | `row-embeddings-write-qdrant` |

### 行嵌入查询 API

行嵌入查询是与 GraphQL 行查询服务**不同的 API**：

| API | 目的 | 后端 |
|-----|---------|---------|
| 行查询 (GraphQL) | 对索引字段进行精确匹配 | Cassandra |
| 行嵌入查询 | 模糊/语义匹配 | Qdrant |

这种分离保持了关注点的清晰：
GraphQL 服务专注于精确、结构化的查询
嵌入 API 处理语义相似性
用户工作流程：通过嵌入进行模糊搜索以查找候选对象，然后进行精确查询以获取完整的行数据

#### 请求/响应模式

```python
@dataclass
class RowEmbeddingsRequest:
    vectors: list[list[float]]    # Query vectors (pre-computed embeddings)
    user: str = ""
    collection: str = ""
    schema_name: str = ""
    index_name: str = ""          # Optional: filter to specific index
    limit: int = 10               # Max results per vector

@dataclass
class RowIndexMatch:
    index_name: str = ""          # The matched index field(s)
    index_value: list[str] = []   # The matched value(s)
    text: str = ""                # Original text that was embedded
    score: float = 0.0            # Similarity score

@dataclass
class RowEmbeddingsResponse:
    error: Error | None = None
    matches: list[RowIndexMatch] = []
```

#### 查询处理器

模块：`trustgraph-flow/trustgraph/query/row_embeddings/qdrant`

入口点：`row-embeddings-query-qdrant`

处理器：
1. 接收带有查询向量的 `RowEmbeddingsRequest`
2. 通过前缀匹配找到合适的 Qdrant 集合
3. 搜索最近的向量，并可选择使用 `index_name` 过滤器
4. 返回包含匹配索引信息的 `RowEmbeddingsResponse`

#### API 网关集成

网关通过标准的请求/响应模式公开行嵌入查询：

| 组件 | 位置 |
|-----------|----------|
| 调度器 | `trustgraph-flow/trustgraph/gateway/dispatch/row_embeddings_query.py` |
| 注册 | 将 `"row-embeddings"` 添加到 `request_response_dispatchers` 中，位于 `manager.py` |

流程接口名称：`row-embeddings`

流程蓝图中的接口定义：
```json
{
  "interfaces": {
    "row-embeddings": {
      "request": "non-persistent://tg/request/row-embeddings:{id}",
      "response": "non-persistent://tg/response/row-embeddings:{id}"
    }
  }
}
```

#### Python SDK 支持

SDK 提供了用于行嵌入查询的方法：

```python
# Flow-scoped query (preferred)
api = Api(url)
flow = api.flow().id("default")

# Query with text (SDK computes embeddings)
matches = flow.row_embeddings_query(
    text="Chestnut Street",
    collection="my_collection",
    schema_name="addresses",
    index_name="street_name",  # Optional filter
    limit=10
)

# Query with pre-computed vectors
matches = flow.row_embeddings_query(
    vectors=[[0.1, 0.2, ...]],
    collection="my_collection",
    schema_name="addresses"
)

# Each match contains:
for match in matches:
    print(match.index_name)   # e.g., "street_name"
    print(match.index_value)  # e.g., ["CHESTNUT ST"]
    print(match.text)         # e.g., "CHESTNUT ST"
    print(match.score)        # e.g., 0.95
```

#### 命令行工具

命令：`tg-invoke-row-embeddings`

```bash
# Query by text (computes embedding automatically)
tg-invoke-row-embeddings \
  --text "Chestnut Street" \
  --collection my_collection \
  --schema addresses \
  --index street_name \
  --limit 10

# Query by vector file
tg-invoke-row-embeddings \
  --vectors vectors.json \
  --collection my_collection \
  --schema addresses

# Output formats
tg-invoke-row-embeddings --text "..." --format json
tg-invoke-row-embeddings --text "..." --format table
```

#### 典型用法示例

行嵌入查询通常用作模糊到精确查找流程的一部分：

```python
# Step 1: Fuzzy search via embeddings
matches = flow.row_embeddings_query(
    text="chestnut street",
    collection="geo",
    schema_name="streets"
)

# Step 2: Exact lookup via GraphQL for full row data
for match in matches:
    query = f'''
    query {{
        streets(where: {{ {match.index_name}: {{ eq: "{match.index_value[0]}" }} }}) {{
            street_name
            city
            zip_code
        }}
    }}
    '''
    rows = flow.rows_query(query, collection="geo")
```

这种两步模式可以实现：
当用户搜索 "Chestnut Street" 时，找到 "CHESTNUT ST"
检索包含所有字段的完整行数据
结合语义相似性和结构化数据访问

### 行数据导入

暂定于后续阶段。将与其他导入更改一起设计。

## 实施影响

### 当前状态分析

现有的实现包含两个主要组件：

| 组件 | 位置 | 行数 | 描述 |
|-----------|----------|-------|-------------|
| 查询服务 | `trustgraph-flow/trustgraph/query/objects/cassandra/service.py` | ~740 | 整体式：GraphQL 模式生成、过滤器解析、Cassandra 查询、请求处理 |
| 写入器 | `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py` | ~540 | 每个模式的表创建、二级索引、插入/删除 |

**当前的查询模式：**
```sql
SELECT * FROM {keyspace}.o_{schema_name}
WHERE collection = 'X' AND email = 'foo@bar.com'
ALLOW FILTERING
```

**新的查询模式：**
```sql
SELECT * FROM {keyspace}.rows
WHERE collection = 'X' AND schema_name = 'customers'
  AND index_name = 'email' AND index_value = ['foo@bar.com']
```

### 关键变更

1. **查询语义简化：** 新的模式仅支持对 `index_value` 的精确匹配。当前的 GraphQL 过滤器（`gt`、`lt`、`contains` 等）要么：
   变为对返回数据的后过滤（如果仍然需要）
   被移除，转而使用嵌入 API 进行模糊匹配

2. **GraphQL 代码紧密耦合：** 当前的 `service.py` 包含了 Strawberry 类型生成、过滤器解析以及 Cassandra 相关的查询。添加另一个行存储后端会重复大约 400 行的 GraphQL 代码。

### 提出的重构

重构分为两部分：

#### 1. 提取 GraphQL 代码

将可重用的 GraphQL 组件提取到共享模块中：

```
trustgraph-flow/trustgraph/query/graphql/
├── __init__.py
├── types.py        # Filter types (IntFilter, StringFilter, FloatFilter)
├── schema.py       # Dynamic schema generation from RowSchema
└── filters.py      # Filter parsing utilities
```

这实现了：
在不同的行存储后端中实现重用
更清晰的分层
更容易独立地测试 GraphQL 逻辑

#### 2. 实现新的表模式

重构特定于 Cassandra 的代码，以使用统一的表：

**写入器 (Writer)** (`trustgraph-flow/trustgraph/storage/rows/cassandra/`):
使用单个 `rows` 表，而不是每个模式的表
写入 N 个副本到每行（每个索引一个）
注册到 `row_partitions` 表
更简单的表创建（一次性设置）

**查询服务 (Query Service)** (`trustgraph-flow/trustgraph/query/rows/cassandra/`):
查询统一的 `rows` 表
使用提取的 GraphQL 模块进行模式生成
简化的过滤处理（仅在数据库级别进行精确匹配）

### 模块重命名

作为“object”→“row”命名清理的一部分：

| 当前 (Current) | 新 (New) |
|---------|-----|
| `storage/objects/cassandra/` | `storage/rows/cassandra/` |
| `query/objects/cassandra/` | `query/rows/cassandra/` |
| `embeddings/object_embeddings/` | `embeddings/row_embeddings/` |

### 新模块

| 模块 (Module) | 目的 (Purpose) |
|--------|---------|
| `trustgraph-flow/trustgraph/query/graphql/` | 共享 GraphQL 工具
| `trustgraph-flow/trustgraph/query/row_embeddings/qdrant/` | 行嵌入查询 API
| `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | 行嵌入计算（第一阶段）
| `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | 行嵌入存储（第二阶段）

## 引用

[结构化数据技术规范](structured-data.md)
