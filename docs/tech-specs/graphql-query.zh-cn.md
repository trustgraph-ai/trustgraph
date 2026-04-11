# GraphQL 查询技术规范

## 概述

<<<<<<< HEAD
本规范描述了用于 TrustGraph 结构化数据存储在 Apache Cassandra 中的 GraphQL 查询接口的实现。 在结构化数据功能方面，本规范基于结构化数据规范 (structured-data.md)，详细说明了如何对包含提取和摄取的结构化对象的 Cassandra 表执行 GraphQL 查询。
=======
本规范描述了用于 TrustGraph 结构化数据存储在 Apache Cassandra 中的 GraphQL 查询接口的实现。 在结构化数据功能方面，本规范基于结构化数据规范 (structured-data.md)，详细说明了如何针对包含提取和导入的结构化对象的 Cassandra 表执行 GraphQL 查询。
>>>>>>> 82edf2d (New md files from RunPod)

GraphQL 查询服务将提供一个灵活、类型安全的接口，用于查询存储在 Cassandra 中的结构化数据。 它将动态适应模式更改，支持包括对象之间的关系在内的复杂查询，并与 TrustGraph 现有的基于消息的架构无缝集成。

## 目标

**动态模式支持**: 在不重新启动服务的情况下，自动适应配置中的模式更改
**GraphQL 标准兼容性**: 提供与现有 GraphQL 工具和客户端兼容的标准 GraphQL 接口
**高效的 Cassandra 查询**: 将 GraphQL 查询转换为高效的 Cassandra CQL 查询，同时尊重分区键和索引
**关系解析**: 支持用于不同对象类型之间关系的 GraphQL 字段解析器
**类型安全**: 基于模式定义，确保类型安全地执行查询并生成响应
**可扩展的性能**: 通过适当的连接池和查询优化，高效地处理并发查询
**请求/响应集成**: 保持与 TrustGraph 基于 Pulsar 的请求/响应模式的兼容性
**错误处理**: 提供全面的错误报告，用于模式不匹配、查询错误和数据验证问题

## 背景

<<<<<<< HEAD
结构化数据存储实现 (trustgraph-flow/trustgraph/storage/objects/cassandra/) 根据存储在 TrustGraph 配置系统中的模式定义，将对象写入 Cassandra 表。 这些表使用复合分区键结构，具有集合和基于模式定义的键，从而可以在集合中实现高效的查询。
=======
结构化数据存储实现 (trustgraph-flow/trustgraph/storage/objects/cassandra/) 根据存储在 TrustGraph 配置系统中的模式定义，将对象写入 Cassandra 表。 这些表使用复合分区键结构，以及基于集合和模式定义的键，从而实现集合内部的高效查询。
>>>>>>> 82edf2d (New md files from RunPod)

当前的局限性，本规范旨在解决：
缺少用于存储在 Cassandra 中的结构化数据的查询接口
无法利用 GraphQL 的强大查询功能来处理结构化数据
缺少对相关对象之间关系遍历的支持
<<<<<<< HEAD
缺少用于结构化数据访问的标准化查询语言

GraphQL 查询服务将通过以下方式弥补这些差距：
提供用于查询 Cassandra 表的标准 GraphQL 接口
=======
缺少一种用于结构化数据访问的标准查询语言

GraphQL 查询服务将通过以下方式弥补这些差距：
为查询 Cassandra 表提供标准的 GraphQL 接口
>>>>>>> 82edf2d (New md files from RunPod)
从 TrustGraph 配置动态生成 GraphQL 模式
高效地将 GraphQL 查询转换为 Cassandra CQL
通过字段解析器支持关系解析

## 技术设计

### 架构

GraphQL 查询服务将作为新的 TrustGraph 流处理器实现，遵循既定的模式：

**模块位置**: `trustgraph-flow/trustgraph/query/objects/cassandra/`

**主要组件**:

1. **GraphQL 查询服务处理器**
   扩展基础 FlowProcessor 类
   实现类似于现有查询服务的请求/响应模式
   监控配置以进行模式更新
   保持与配置同步的 GraphQL 模式

2. **动态模式生成器**
   将 TrustGraph RowSchema 定义转换为 GraphQL 类型
   创建具有适当字段定义的 GraphQL 对象类型
   生成具有基于集合的解析器的根 Query 类型
   在配置更改时更新 GraphQL 模式

3. **查询执行器**
   使用 Strawberry 库解析传入的 GraphQL 查询
   根据当前模式验证查询
   执行查询并返回结构化响应
   通过详细的错误消息优雅地处理错误

4. **Cassandra 查询转换器**
   将 GraphQL 选择转换为 CQL 查询
   根据可用的索引和分区键优化查询
   处理过滤、分页和排序
   管理连接池和会话生命周期

5. **关系解析器**
<<<<<<< HEAD
   实现用于对象之间关系的字段解析器
=======
   实现对象之间关系的字段解析器
>>>>>>> 82edf2d (New md files from RunPod)
   执行批量加载以避免 N+1 查询
   在请求上下文中缓存解析的关系
   支持正向和反向关系遍历

### 配置模式监控

该服务将注册一个配置处理程序以接收模式更新：

```python
self.register_config_handler(self.on_schema_config)
```

当模式发生变化时：
1. 从配置中解析新的模式定义
2. 重新生成 GraphQL 类型和解析器
3. 更新可执行的模式
4. 清除任何依赖于模式的缓存

### GraphQL 模式生成

对于配置中的每个 RowSchema，生成：

1. **GraphQL 对象类型**:
   映射字段类型（string → String, integer → Int, float → Float, boolean → Boolean）
   将必需字段标记为 GraphQL 中的非空值
   从模式中添加字段描述

2. **根查询字段**:
<<<<<<< HEAD
   集合查询（例如，`customers`，`transactions`）
=======
   集合查询（例如，`customers`, `transactions`）
>>>>>>> 82edf2d (New md files from RunPod)
   基于索引字段的过滤参数
   分页支持（limit, offset）
   可排序字段的排序选项

3. **关系字段**:
   从模式中识别外键关系
   为相关对象创建字段解析器
   支持单对象和列表关系

### 查询执行流程

1. **请求接收**:
   从 Pulsar 接收 ObjectsQueryRequest
   提取 GraphQL 查询字符串和变量
   识别用户和集合上下文

2. **查询验证**:
   使用 Strawberry 解析 GraphQL 查询
<<<<<<< HEAD
   验证与当前模式
=======
   验证与当前模式的匹配
>>>>>>> 82edf2d (New md files from RunPod)
   检查字段选择和参数类型

3. **CQL 生成**:
   分析 GraphQL 选择
   构建带有适当 WHERE 子句的 CQL 查询
   将集合包含在分区键中
   根据 GraphQL 参数应用过滤器

4. **查询执行**:
   对 Cassandra 执行 CQL 查询
   将结果映射到 GraphQL 响应结构
   解析任何关系字段
   格式化响应以符合 GraphQL 规范

5. **响应发送**:
   创建包含结果的 ObjectsQueryResponse
   包含任何执行错误
   通过 Pulsar 发送带有相关 ID 的响应

### 数据模型

<<<<<<< HEAD
> **注意**: `trustgraph-base/trustgraph/schema/services/structured_query.py` 中存在现有的 StructuredQueryRequest/Response 模式。但是，它缺少关键字段（用户、集合），并且使用了次优类型。以下模式代表推荐的演进，应该替换现有的模式，或者创建新的 ObjectsQueryRequest/Response 类型。
=======
> **注意**: `trustgraph-base/trustgraph/schema/services/structured_query.py` 中已存在一个 StructuredQueryRequest/Response 模式。但是，它缺少关键字段（用户、集合），并且使用了次优类型。以下模式代表推荐的演进，应替换现有模式或创建为新的 ObjectsQueryRequest/Response 类型。
>>>>>>> 82edf2d (New md files from RunPod)

#### 请求模式 (ObjectsQueryRequest)

```python
from pulsar.schema import Record, String, Map, Array

class ObjectsQueryRequest(Record):
    user = String()              # Cassandra keyspace (follows pattern from TriplesQueryRequest)
    collection = String()        # Data collection identifier (required for partition key)
    query = String()             # GraphQL query string
    variables = Map(String())    # GraphQL variables (consider enhancing to support all JSON types)
    operation_name = String()    # Operation to execute for multi-operation documents
```

**对现有 StructuredQueryRequest 的更改原因：**
添加了 `user` 和 `collection` 字段，以匹配其他查询服务的模式。
<<<<<<< HEAD
这些字段对于识别 Cassandra 键空间和集合至关重要。
=======
这些字段对于标识 Cassandra 键空间和集合至关重要。
>>>>>>> 82edf2d (New md files from RunPod)
变量目前仍然是 Map(String())，但理想情况下应该支持所有 JSON 类型。

#### 响应模式 (ObjectsQueryResponse)

```python
from pulsar.schema import Record, String, Array
from ..core.primitives import Error

class GraphQLError(Record):
    message = String()
    path = Array(String())       # Path to the field that caused the error
    extensions = Map(String())   # Additional error metadata

class ObjectsQueryResponse(Record):
    error = Error()              # System-level error (connection, timeout, etc.)
    data = String()              # JSON-encoded GraphQL response data
    errors = Array(GraphQLError) # GraphQL field-level errors
    extensions = Map(String())   # Query metadata (execution time, etc.)
```

**对现有 StructuredQueryResponse 更改的理由：**
区分系统错误 (`error`) 和 GraphQL 错误 (`errors`)
使用结构化的 GraphQLError 对象，而不是字符串数组
<<<<<<< HEAD
添加 `extensions` 字段，以符合 GraphQL 规范
=======
添加 `extensions` 字段以符合 GraphQL 规范
>>>>>>> 82edf2d (New md files from RunPod)
为了兼容性，将数据保留为 JSON 字符串，尽管使用原生类型会更好

### Cassandra 查询优化

该服务将通过以下方式优化 Cassandra 查询：

1. **尊重分区键：**
   始终在查询中包含集合
   高效使用 schema 定义的主键
   避免全表扫描

2. **利用索引：**
   使用二级索引进行过滤
   尽可能组合多个过滤器
   当查询可能效率低下时，发出警告

3. **批量加载：**
   收集关系查询
   批量执行以减少网络请求次数
   在请求上下文中缓存结果

4. **连接管理：**
   维护持久的 Cassandra 会话
   使用连接池
   在发生故障时处理重连

### 示例 GraphQL 查询

<<<<<<< HEAD
#### 简单的集合查询
=======
#### 简单集合查询
>>>>>>> 82edf2d (New md files from RunPod)
```graphql
{
  customers(status: "active") {
    customer_id
    name
    email
    registration_date
  }
}
```

#### 查询与关系
```graphql
{
  orders(order_date_gt: "2024-01-01") {
    order_id
    total_amount
    customer {
      name
      email
    }
    items {
      product_name
      quantity
      price
    }
  }
}
```

#### 分页查询
```graphql
{
  products(limit: 20, offset: 40) {
    product_id
    name
    price
    category
  }
}
```

### 实现依赖

**Strawberry GraphQL**: 用于 GraphQL 模式定义和查询执行
**Cassandra Driver**: 用于数据库连接（已在存储模块中使用）
**TrustGraph Base**: 用于 FlowProcessor 和模式定义
**Configuration System**: 用于模式监控和更新

### 命令行界面

该服务将提供一个 CLI 命令：`kg-query-objects-graphql-cassandra`

参数：
`--cassandra-host`: Cassandra 集群联系点
`--cassandra-username`: 身份验证用户名
`--cassandra-password`: 身份验证密码
`--config-type`: 用于模式的配置类型（默认："schema"）
标准 FlowProcessor 参数（Pulsar 配置等）

## API 集成

### Pulsar 主题

**输入主题**: `objects-graphql-query-request`
Schema: ObjectsQueryRequest
接收来自网关服务的 GraphQL 查询

**输出主题**: `objects-graphql-query-response`
Schema: ObjectsQueryResponse
返回查询结果和错误

### 网关集成

网关和反向网关需要端点来：
1. 接受来自客户端的 GraphQL 查询
2. 通过 Pulsar 将其转发到查询服务
3. 将响应返回给客户端
4. 支持 GraphQL 内省查询

### 代理工具集成

一个新的代理工具类将启用：
自然语言到 GraphQL 查询的生成
直接 GraphQL 查询执行
结果解释和格式化
与代理决策流程的集成

## 安全注意事项

**查询深度限制**: 阻止深度嵌套的查询，以防止性能问题
**查询复杂度分析**: 限制查询复杂度以防止资源耗尽
**字段级权限**: 未来支持基于用户角色的字段级访问控制
**输入验证**: 验证和清理所有查询输入以防止注入攻击
**速率限制**: 为每个用户/集合实施查询速率限制

## 性能注意事项

**查询规划**: 在执行之前分析查询以优化 CQL 生成
**结果缓存**: 考虑缓存频繁访问的数据，位于字段解析器级别
**连接池**: 维护与 Cassandra 的高效连接池
**批量操作**: 尽可能组合多个查询以减少延迟
**监控**: 跟踪查询性能指标以进行优化

## 测试策略

### 单元测试
从 RowSchema 定义生成模式
GraphQL 查询解析和验证
CQL 查询生成逻辑
字段解析器实现

### 契约测试
Pulsar 消息契约合规性
GraphQL 模式有效性
响应格式验证
错误结构验证

### 集成测试
对测试 Cassandra 实例执行端到端查询
模式更新处理
关系解析
分页和过滤
错误场景

### 性能测试
负载下的查询吞吐量
各种查询复杂度的响应时间
大结果集下的内存使用情况
连接池效率

## 迁移计划

<<<<<<< HEAD
由于这是一个新功能，因此不需要迁移。该服务将：
=======
由于这是一个新功能，因此不需要迁移。 该服务将：
>>>>>>> 82edf2d (New md files from RunPod)
1. 从配置中读取现有模式
2. 连接到存储模块创建的现有 Cassandra 表
3. 立即在部署后开始接受查询

## 时间表

第 1-2 周：核心服务实现和模式生成
第 3 周：查询执行和 CQL 转换
第 4 周：关系解析和优化
第 5 周：测试和性能调整
第 6 周：网关集成和文档

## 开放问题

1. **模式演进**: 服务应该如何处理查询期间的模式转换？
   选项：在模式更新期间排队查询
   选项：同时支持多个模式版本

2. **缓存策略**: 是否应该缓存查询结果？
   考虑：基于时间的过期
   考虑：基于事件的失效

3. **联邦支持**: 该服务是否应该支持 GraphQL 联邦，以与其他数据源组合？
   将启用跨结构化和图形数据的统一查询

4. **订阅支持**: 该服务是否应该支持 GraphQL 订阅以进行实时更新？
   需要网关中的 WebSocket 支持

5. **自定义标量**: 是否应该支持自定义标量类型，用于特定领域的的数据类型？
   示例：DateTime、UUID、JSON 字段

## 参考文献

结构化数据技术规范：`docs/tech-specs/structured-data.md`
Strawberry GraphQL 文档：https://strawberry.rocks/
GraphQL 规范：https://spec.graphql.org/
Apache Cassandra CQL 参考：https://cassandra.apache.org/doc/stable/cassandra/cql/
TrustGraph Flow Processor 文档：内部文档