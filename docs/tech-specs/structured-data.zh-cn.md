# 结构化数据技术规范

## 概述

本规范描述了 TrustGraph 与结构化数据流的集成，使系统能够处理可以表示为表格中的行或对象存储中的对象的结构化数据。该集成支持四个主要用例：

1. **非结构化到结构化提取**: 读取非结构化数据源，识别和提取对象结构，并将它们存储在表格格式中。
2. **结构化数据导入**: 将已经采用结构化格式的数据直接导入到结构化存储中，与提取的数据一起存储。
3. **自然语言查询**: 将自然语言问题转换为结构化查询，以从存储中提取匹配的数据。
4. **直接结构化查询**: 直接对数据存储执行结构化查询，以进行精确的数据检索。

## 目标

**统一数据访问**: 提供一个用于访问 TrustGraph 中结构化和非结构化数据的单一接口。
**无缝集成**: 实现 TrustGraph 的基于图的知识表示与传统结构化数据格式之间的平滑互操作性。
**灵活提取**: 支持从各种非结构化源（文档、文本等）自动提取结构化数据。
**查询灵活性**: 允许用户使用自然语言和结构化查询语言查询数据。
**数据一致性**: 维护不同数据表示形式之间的数据完整性和一致性。
**性能优化**: 确保在大规模下高效地存储和检索结构化数据。
**模式灵活性**: 支持“写时模式”和“读时模式”两种方法，以适应各种数据源。
**向后兼容性**: 在添加结构化数据功能的同时，保留现有的 TrustGraph 功能。

## 背景

TrustGraph 目前擅长处理非结构化数据并从各种来源构建知识图。然而，许多企业用例涉及本质上是结构化的数据，例如客户记录、事务日志、库存数据库和其他表格数据集。这些结构化数据集通常需要与非结构化内容一起进行分析，以提供全面的见解。

当前的局限性包括：
不支持导入预结构化数据格式（CSV、JSON 数组、数据库导出）。
无法在从文档中提取表格数据时保留其固有的结构。
缺乏用于结构化数据模式的有效查询机制。
SQL 样式的查询与 TrustGraph 的图查询之间的桥梁缺失。

本规范通过引入补充 TrustGraph 现有功能的结构化数据层来解决这些差距。通过原生支持结构化数据，TrustGraph 可以：
作为结构化和非结构化数据分析的统一平台。
实现跨图关系和表格数据的混合查询。
为习惯于处理结构化数据的用户提供熟悉的接口。
释放数据集成和商业智能中的新用例。

## 技术设计

### 架构

结构化数据集成需要以下技术组件：

1. **NLP-to-Structured-Query 服务**
   将自然语言问题转换为结构化查询。
   支持多种查询语言目标（最初为 SQL 样式的语法）。
   与现有的 TrustGraph NLP 功能集成。
   
   模块: trustgraph-flow/trustgraph/query/nlp_query/cassandra

2. **配置模式支持** ✅ **[完成]**
   扩展配置系统以存储结构化数据模式。
   支持定义表结构、字段类型和关系。
   模式版本控制和迁移功能。

3. **对象提取模块** ✅ **[完成]**
   增强的知识提取流程集成。
   从非结构化源识别和提取结构化对象。
   维护溯源信息和置信度分数。
   注册一个配置处理程序（例如：trustgraph-flow/trustgraph/prompt/template/service.py），以接收配置数据并解码模式信息。
   接收对象并将其解码为 ExtractedObject 对象，并通过 Pulsar 队列进行传递。
   注意：存在于 `trustgraph-flow/trustgraph/extract/object/row/` 的现有代码。这是一个之前的尝试，需要进行重大重构，因为它不符合当前的 API。如果有用，可以使用它，否则从头开始。
   需要一个命令行界面：`kg-extract-objects`

   模块: trustgraph-flow/trustgraph/extract/kg/objects/

4. **结构化存储写入模块** ✅ **[完成]**
   从 Pulsar 队列接收 ExtractedObject 格式的对象。
   初始实现针对 Apache Cassandra 作为结构化数据存储。
   处理基于遇到的模式动态创建表。
   管理模式到 Cassandra 表的映射以及数据转换。
   提供批量和流式写入操作以进行性能优化。
   没有 Pulsar 输出 - 这是一个数据流中的终端服务。

   **模式处理**:
   监控传入的 ExtractedObject 消息以查找模式引用。
   首次遇到新模式时，自动创建相应的 Cassandra 表。
   维护已知模式的缓存，以避免重复的表创建尝试。
   应该考虑是直接接收模式定义，还是依赖于 ExtractedObject 消息中的模式名称。

   **Cassandra 表映射**:
   键空间（Keyspace）的名称源自 ExtractedObject 的 Metadata 中的 `user` 字段。
   表的名称源自 ExtractedObject 中的 `schema_name` 字段。
   Metadata 中的集合（Collection）成为分区键的一部分，以确保：
     Cassandra 节点之间的数据自然分布。
     特定集合内的查询效率。
     不同数据导入/来源之间的逻辑隔离。
   主键结构：`PRIMARY KEY ((collection, <schema_primary_key_fields>), <clustering_keys>)`
     集合始终是分区键的第一部分。
     遵循定义的模式的主键字段作为组合分区键的一部分。
     这要求查询指定集合，以确保可预测的性能。
   字段定义映射到 Cassandra 列，并进行类型转换：
     `string` → `text`
     `integer` → `int` 或 `bigint`，具体取决于大小提示。
     `float` → `float` 或 `double`，具体取决于精度需求。
     `boolean` → `boolean`
     `timestamp` → `timestamp`
     `enum` → `text`，并进行应用程序级别的验证。
   索引字段创建 Cassandra 的二级索引（不包括主键中的字段）。
   必需字段在应用程序级别强制执行（Cassandra 不支持 NOT NULL）。

   **对象存储**:
   从 ExtractedObject.values 映射中提取值。
   在插入之前执行类型转换和验证。
   优雅地处理缺失的可选字段。
   维护有关对象来源的元数据（源文档、置信度分数）。
   支持幂等写入，以处理消息重放场景。

   **实现说明**:
   位于 `trustgraph-flow/trustgraph/storage/objects/cassandra/` 的现有代码已过时，不符合当前的 API。
   应该参考 `trustgraph-flow/trustgraph/storage/triples/cassandra` 作为工作存储处理器的示例。
   在决定重构或重写之前，需要评估现有代码以查找任何可重用组件。

   模块：trustgraph-flow/trustgraph/storage/objects/cassandra

5. **结构化查询服务** ✅ **[完成]**
   接受定义格式的结构化查询。
   对结构化存储执行查询。
   返回与查询条件匹配的对象。
   支持分页和结果过滤。

   模块：trustgraph-flow/trustgraph/query/objects/cassandra

6. **代理工具集成**
   用于代理框架的新工具类。
   使代理能够查询结构化数据存储。
   提供自然语言和结构化查询接口。
   与现有的代理决策过程集成。

7. **结构化数据摄取服务**
   接受多种格式（JSON、CSV、XML）的结构化数据。
   根据定义的模式解析和验证传入数据。
   将数据转换为规范化的对象流。
   将对象发送到适当的消息队列进行处理。
   支持批量上传和流式摄取。

   模块：trustgraph-flow/trustgraph/decoding/structured

8. **对象嵌入服务**
   为结构化对象生成向量嵌入。
   启用结构化数据的语义搜索。
   支持结合结构化查询和语义相似性的混合搜索。
   与现有的向量存储集成。

   模块：trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant

### 数据模型

#### 模式存储机制

模式存储在 TrustGraph 的配置系统中使用以下结构：

**类型**: `schema`（所有结构化数据模式的固定值）
**键**: 模式的唯一名称/标识符（例如，`customer_records`、`transaction_log`）
**值**: 包含结构的 JSON 模式定义

示例配置条目：
```
Type: schema
Key: customer_records
Value: {
  "name": "customer_records",
  "description": "Customer information table",
  "fields": [
    {
      "name": "customer_id",
      "type": "string",
      "primary_key": true
    },
    {
      "name": "name",
      "type": "string",
      "required": true
    },
    {
      "name": "email",
      "type": "string",
      "required": true
    },
    {
      "name": "registration_date",
      "type": "timestamp"
    },
    {
      "name": "status",
      "type": "string",
      "enum": ["active", "inactive", "suspended"]
    }
  ],
  "indexes": ["email", "registration_date"]
}
```

此方法允许：
动态模式定义，无需代码更改
轻松的模式更新和版本控制
与现有 TrustGraph 配置管理的一致集成
支持在单个部署中使用的多个模式

### API

新增 API：
  用于上述类型的 Pulsar 模式
  新流程中的 Pulsar 接口
  需要一种方法来指定模式类型，以便流程知道要加载哪些
    模式类型
  向网关和反向网关添加了 API

修改后的 API：
知识提取端点 - 添加结构化对象输出选项
代理端点 - 添加结构化数据工具支持

### 实施细节

遵循现有约定 - 这些只是新的处理模块。
除了 trustgraph-base 中的模式项之外，所有内容都位于 trustgraph-flow 包中。


需要在 Workbench 中进行一些 UI 工作，以便演示/试用此
功能。

## 安全注意事项

没有额外的注意事项。

## 性能注意事项

关于使用 Cassandra 查询和索引的一些问题，以确保查询
不会降低速度。

## 测试策略

使用现有的测试策略，将构建单元测试、契约测试和集成测试。

## 迁移计划

无。

## 时间线

未指定。

## 开放问题

是否可以使其与其它存储类型一起工作？ 我们的目标是使用
  接口，使适用于一种存储的模块也适用于
  其他存储。

## 参考文献

n/a。

