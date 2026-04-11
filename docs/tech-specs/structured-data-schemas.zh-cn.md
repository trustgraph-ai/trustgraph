# 结构化数据 Pulsar 模式更改

## 概述

根据 `STRUCTURED_DATA.md` 规范，本文件提出必要的 Pulsar 模式添加和修改，以支持 TrustGraph 中的结构化数据功能。

## 必需的模式更改

### 1. 核心模式增强

#### 增强的字段定义
现有的 `Field` 类在 `core/primitives.py` 中需要额外的属性：

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # 新字段：
    required = Boolean()  # 字段是否必需
    enum_values = Array(String())  # 针对枚举类型的字段
    indexed = Boolean()  # 字段是否应进行索引
```

### 2. 新的知识模式

#### 2.1 结构化数据提交
新的文件：`knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # 引用配置中的模式
    data = Bytes()  # 原始数据，用于导入
    options = Map(String())  # 格式特定的选项
```

#### 2.2 结构化查询模式

#### 3.1 NLP 到结构化查询服务
新的文件：`services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # 针对查询生成的可选上下文

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # 生成的 GraphQL 查询
    variables = Map(String())  # 如果有的话，GraphQL 变量
    detected_schemas = Array(String())  # 查询的目标模式
    confidence = Double()
```

#### 3.2 结构化查询服务
新的文件：`services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # GraphQL 查询
    variables = Map(String())  # GraphQL 变量
    operation_name = String()  # 针对多操作文档的可选操作名称

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # JSON 编码的 GraphQL 响应数据
    errors = Array(String())  # 如果有的话，GraphQL 错误
```

#### 2.2 对象提取输出
新的文件：`knowledge/object.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # 此对象属于哪个模式
    values = Map(String())  # 字段名称 -> 值
    confidence = Double()
    source_span = String()  # 对象所在的文本范围
```

### 4. 增强的知识模式

#### 4.1 对象嵌入增强
更新 `knowledge/embeddings.py` 以更好地支持结构化对象嵌入：

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # 主键值
    field_embeddings = Map(Array(Double()))  # 针对每个字段的嵌入
```

## 集成点

### 流集成

这些模式将由新的流模块使用：
- `trustgraph-flow/trustgraph/decoding/structured` - 使用 StructuredDataSubmission
- `trustgraph-flow/trustgraph/query/nlp_query/cassandra` - 使用 NLP 查询模式
- `trustgraph-flow/trustgraph/query/objects/cassandra` - 使用结构化查询模式
- `trustgraph-flow/trustgraph/extract/object/row/` - 消耗 Chunk，产生 ExtractedObject
- `trustgraph-flow/trustgraph/storage/objects/cassandra` - 使用 Rows 模式
- `trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - 使用对象嵌入模式

## 实现说明

1. **模式版本控制**: 考虑为 RowSchema 添加 `version` 字段，以便进行未来迁移支持
2. **类型系统**: `Field.type` 应该支持所有 Cassandra 原生类型
3. **批量操作**: 大多数服务都应该支持单个和批量操作
4. **错误处理**: 所有新服务的错误报告应保持一致
5. **向后兼容性**: 现有的模式不受影响，只有字段进行了轻微增强

## 接下来要做的事

1. 在新的结构中实现模式文件
2. 更新现有服务以识别新的模式类型
3. 实现使用这些模式的流模块
4. 为新的服务添加网关/反向网关端点
5. 创建模式验证的单元测试