---
layout: default
title: "Neo4j 用户/集合隔离支持"
parent: "Chinese (Beta)"
---

# Neo4j 用户/集合隔离支持

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 问题陈述

Neo4j 的三元存储和查询实现目前缺乏用户/集合隔离，从而导致多租户安全问题。所有三元都存储在同一个图空间中，且没有任何机制来防止用户访问其他用户的或混合集合的数据。

与 TrustGraph 中的其他存储后端不同：
- **Cassandra**: 使用每个用户和每个集合的单独键空间和表
- **向量存储**（Milvus、Qdrant、Pinecone）: 使用集合特定的命名空间
- **Neo4j**: 目前共享所有数据在一个图（安全漏洞）

## 现有架构

### 数据模型
- **节点**: 标签为 `:Node`，具有 `uri` 属性，标签为 `:Literal`，具有 `value` 属性
- **关系**: 标签为 `:Rel`，具有 `uri` 属性
- **索引**: `Node.uri`、`Literal.value`、`Rel.uri`

### 消息流程
- `Triples` 消息包含 `metadata.user` 和 `metadata.collection` 字段
- 存储服务接收用户/集合信息，但忽略它们
- 查询服务期望在 `TriplesQueryRequest` 中包含 `user` 和 `collection`，但忽略它们

### 现有安全问题
```cypher
# 任何用户都可以查询任何数据 - 无隔离
MATCH (src:Node)-[rel:Rel]->(dest:Node)
RETURN src.uri, rel.uri, dest.uri
```

## 建议解决方案：基于属性的过滤（推荐）

### 概述
添加所有节点的和关系的 `user` 和 `collection` 属性，然后使用这些属性对所有操作进行过滤。 这种方法在保持查询灵活性和向后兼容性的同时，提供强大的隔离。

### 数据模型更改

#### 增强的节点结构
```cypher
// 节点实体
CREATE (n:Node {
  uri: "http://example.com/entity1",
  user: "john_doe",
  collection: "production_v1"
})

// 字面量实体
CREATE (n:Literal {
  value: "literal value",
  user: "john_doe",
  collection: "production_v1"
})
```

#### 增强的关系结构
```cypher
// 具有 user/collection 属性的关系
CREATE (src)-[:Rel {
  uri: "http://example.com/predicate1",
  user: "john_doe",
  collection: "production_v1"
}]->(dest)
```

#### 更新的索引
```cypher
// 用于高效过滤的复合索引
CREATE INDEX node_user_collection_uri FOR (n:Node) ON (n.user, n.collection, n.uri);
CREATE INDEX literal_user_collection_value FOR (n:Literal) ON (n.user, n.collection, n.value);
CREATE INDEX rel_user_collection_uri FOR ()-[r:Rel]-() ON (r.user, r.collection, r.uri);

// 保持现有索引以实现向后兼容性（可选）
CREATE INDEX Node_uri FOR (n:Node) ON (n.uri);
CREATE INDEX Literal_value FOR (n:Literal) ON (n.value);
CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri);
```

### 实现更改

#### 存储服务 (`write.py`)

**当前代码：**
```python
def create_node(self, uri):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri})",
        uri=uri, database_=self.db,
    ).summary
```

**更新后的代码：**
```python
def create_node(self, uri, user, collection):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
        uri=uri, user=user, collection=collection, database_=self.db,
    ).summary
```

**增强的 store_triples 方法：**
```python
async def store_triples(self, message):
    user = message.metadata.user
    collection = message.metadata.collection
    # 存储 triples
    # ...
```

#### 查询更新
（此处应包含修改查询模式以包含 user 和 collection 的代码。 示例：`query_user1_coll1 = "MATCH (n)-[:Rel]->(m) WHERE n.user = 'john_doe' AND n.collection = 'production_v1' RETURN n, m"`）

### 阶段 2：查询更新（第 2 周）
（此处应包含修改查询模式以包含 user 和 collection 的代码。 示例：`query_user1_coll1 = "MATCH (n)-[:Rel]->(m) WHERE n.user = 'john_doe' AND n.collection = 'production_v1' RETURN n, m"`）
1. [ ] 更新所有查询模式，以便包含 user/collection 过滤器
2. [ ] 添加查询验证和安全检查
3. [ ] 更新集成测试
4. [ ] 性能测试，使用过滤后的查询

### 阶段 3：迁移和部署（第 3 周）
1. [ ] 创建现有 Neo4j 实例的迁移脚本
2. [ ] 部署文档和操作手册
3. [ ] 监控和警报，用于隔离违规
4. [ ] 端到端测试，使用多个用户/集合

### 阶段 4：强化（第 4 周）
1. [ ] 移除兼容性模式
2. [ ] 添加全面的审计日志
3. [ ] 安全审查和渗透测试
4. [ ] 性能优化

## 测试策略

### 单元测试
（此处应包含使用 user 和 collection 进行隔离的单元测试示例。 示例：`def test_user_collection_isolation(): ...`）

### 集成测试
- 具有重叠数据的多用户场景
- 跨集合查询（应失败）
- 迁移测试，使用现有数据
- 性能基准测试，使用大量数据

### 安全测试
- 尝试查询其他用户的
- 尝试 SQL 注入，利用 user/collection 参数
- 验证在各种查询模式下是否完全隔离

## 性能考虑

### 索引策略
- 使用 `(user, collection, uri)` 的复合索引，以实现最佳过滤
- 如果某些集合非常大，请考虑使用部分索引
- 监控索引使用情况和查询性能

### 查询优化
- 使用 EXPLAIN 验证过滤查询是否使用了索引
- 考虑查询结果缓存，用于频繁访问的数据
- 剖析与大量用户/集合一起使用时的内存使用情况

### 可扩展性
- 每个用户/集合组合都会创建一个单独的数据岛
- 监控数据库大小和连接池使用情况
- 考虑所需的水平扩展策略

## 安全与合规

### 数据隔离保证
- **物理**: 所有用户数据都带有明确的用户/集合属性
- **逻辑**: 所有查询都通过用户/集合上下文过滤
- **访问控制**: 服务级别的验证防止未经授权的访问

### 审计要求
- 记录所有数据访问，包括用户/集合上下文
- 跟踪数据移动和迁移活动
- 监控隔离违规尝试

### 合规性考虑
- GDPR：更好地定位和删除用户特定数据
- SOC2：清晰的数据隔离和访问控制
- HIPAA：为医疗数据提供强大的租户隔离

## 风险与缓解措施

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|--------|------------|------------|
| 缺少用户/集合过滤器 | 高 | 中 | 强制验证，全面测试 |
| 查询性能下降 | 中 | 低 | 索引优化，查询剖析 |
| 迁移数据损坏 | 高 | 低 | 备份策略，回滚程序 |
| 复杂的跨集合查询 | 中 | 中 | 文档查询模式，提供示例 |

## 成功标准

1. **安全性**: 在生产环境中，没有任何跨用户的数据访问
2. **性能**: 与未过滤的查询相比，影响小于 10%
3. **迁移**: 100% 的现有 Neo4j 数据成功迁移，且没有数据丢失
4. **可用性**: 所有现有的查询模式都与用户/集合上下文工作
5. **合规性**: 完整地记录用户/集合数据访问

## 结论

基于属性的过滤方法，是实现 Neo4j 用户/集合隔离的最佳平衡方案，它既能保证安全性，又能保持查询的灵活性和强大的图查询功能。

这个解决方案确保 TrustGraph 的 Neo4j 后端符合其他存储后端的相同安全标准，同时最大限度地发挥图查询和索引的优势。
