---
layout: default
title: "向量存储生命周期管理"
parent: "Chinese (Beta)"
---

# 向量存储生命周期管理

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

本文档描述了 TrustGraph 如何管理跨不同后端实现（Qdrant、Pinecone、Milvus）的向量存储集合。该设计解决了在不硬编码维度值的情况下，支持具有不同维度的嵌入向量的挑战。

## 问题陈述

向量存储在创建集合/索引时需要指定嵌入维度。但是：
不同的嵌入模型会产生不同的维度（例如，384、768、1536）
直到生成第一个嵌入向量，维度才已知
单个 TrustGraph 集合可能会接收来自多个模型的嵌入向量
强制指定一个维度（例如，384）会导致使用其他嵌入向量大小时出现故障

## 设计原则

1. **延迟创建**: 集合是在首次写入时按需创建的，而不是在集合管理操作期间创建的。
2. **基于维度的命名**: 集合名称包含嵌入维度作为后缀。
3. **优雅降级**: 对不存在的集合执行的查询返回空结果，而不是错误。
4. **多维度支持**: 单个逻辑集合可以有多个物理集合（每个维度一个）。

## 架构

### 集合命名约定

向量存储集合使用维度后缀来支持多种嵌入向量大小：

**文档嵌入：**
Qdrant: `d_{user}_{collection}_{dimension}`
Pinecone: `d-{user}-{collection}-{dimension}`
Milvus: `doc_{user}_{collection}_{dimension}`

**图嵌入：**
Qdrant: `t_{user}_{collection}_{dimension}`
Pinecone: `t-{user}-{collection}-{dimension}`
Milvus: `entity_{user}_{collection}_{dimension}`

示例：
`d_alice_papers_384` - Alice 的论文集合，使用 384 维的嵌入向量
`d_alice_papers_768` - 相同的逻辑集合，使用 768 维的嵌入向量
`t_bob_knowledge_1536` - Bob 的知识图谱，使用 1536 维的嵌入向量

### 生命周期阶段

#### 1. 集合创建请求

**请求流程：**
```
User/System → Librarian → Storage Management Topic → Vector Stores
```

**行为：**
库管理员将 `create-collection` 请求广播到所有存储后端。
向量存储处理器确认该请求，但**不创建物理集合**。
立即返回成功响应。
实际集合的创建将在第一次写入时延迟。

**理由：**
在创建时，维度是未知的。
避免创建具有错误维度的集合。
简化集合管理逻辑。

#### 2. 写入操作（延迟创建）

**写入流程：**
```
Data → Storage Processor → Check Collection → Create if Needed → Insert
```

**行为：**
1. 从向量中提取嵌入维度：`dim = len(vector)`
2. 使用维度后缀构建集合名称
3. 检查是否存在具有该特定维度的集合
4. 如果不存在：
   创建具有正确维度的集合
   记录：`"Lazily creating collection {name} with dimension {dim}"`
5. 将嵌入信息插入到特定维度的集合中

**示例场景：**
```
1. User creates collection "papers"
   → No physical collections created yet

2. First document with 384-dim embedding arrives
   → Creates d_user_papers_384
   → Inserts data

3. Second document with 768-dim embedding arrives
   → Creates d_user_papers_768
   → Inserts data

Result: Two physical collections for one logical collection
```

#### 3. 查询操作

**查询流程：**
```
Query Vector → Determine Dimension → Check Collection → Search or Return Empty
```

**行为：**
1. 从查询向量中提取维度：`dim = len(vector)`
2. 使用维度后缀构建集合名称
3. 检查集合是否存在
4. 如果存在：
   执行相似度搜索
   返回结果
5. 如果不存在：
   记录日志：`"Collection {name} does not exist, returning empty results"`
   返回空列表（不引发错误）

**同一查询中的多个维度：**
如果查询包含不同维度的向量
每个维度查询其对应的集合
结果进行聚合
缺失的集合将被跳过（不被视为错误）

**原理：**
查询空集合是一种有效的用例
返回空结果在语义上是正确的
避免在系统启动或在数据摄取之前发生的错误

#### 4. 集合删除

**删除流程：**
```
Delete Request → List All Collections → Filter by Prefix → Delete All Matches
```

**行为：**
1. 构造前缀模式：`d_{user}_{collection}_` (注意尾随的下划线)
2. 列出向量存储中的所有集合
3. 过滤与前缀匹配的集合
4. 删除所有匹配的集合
5. 记录每个删除操作：`"Deleted collection {name}"`
6. 汇总日志：`"Deleted {count} collection(s) for {user}/{collection}"`

**示例：**
```
Collections in store:
- d_alice_papers_384
- d_alice_papers_768
- d_alice_reports_384
- d_bob_papers_384

Delete "papers" for alice:
→ Deletes: d_alice_papers_384, d_alice_papers_768
→ Keeps: d_alice_reports_384, d_bob_papers_384
```

**原理：**
确保彻底清理所有维度变体。
模式匹配可防止意外删除不相关的集合。
从用户角度来看，这是一个原子操作（所有维度一起删除）。

## 行为特性

### 正常操作

**集合创建：**
✓ 立即返回成功。
✓ 不分配任何物理存储空间。
✓ 快速操作（没有后端 I/O）。

**首次写入：**
✓ 创建具有正确维度的集合。
✓ 由于集合创建的开销，速度略慢。
✓ 之后对同一维度的写入速度很快。

**在任何写入之前进行查询：**
✓ 返回空结果。
✓ 没有错误或异常。
✓ 系统保持稳定。

**混合维度写入：**
✓ 自动为每个维度创建单独的集合。
✓ 每个维度都隔离在自己的集合中。
✓ 没有维度冲突或模式错误。

**集合删除：**
✓ 移除所有维度变体。
✓ 彻底清理。
✓ 没有孤立的集合。

### 边界情况

**多个嵌入模型：**
```
Scenario: User switches from model A (384-dim) to model B (768-dim)
Behavior:
- Both dimensions coexist in separate collections
- Old data (384-dim) remains queryable with 384-dim vectors
- New data (768-dim) queryable with 768-dim vectors
- Cross-dimension queries return results only for matching dimension
```

**并发首次写入：**
```
Scenario: Multiple processes write to same collection simultaneously
Behavior:
- Each process checks for existence before creating
- Most vector stores handle concurrent creation gracefully
- If race condition occurs, second create is typically idempotent
- Final state: Collection exists and both writes succeed
```

**维度迁移：**
```
Scenario: User wants to migrate from 384-dim to 768-dim embeddings
Behavior:
- No automatic migration
- Old collection (384-dim) persists
- New collection (768-dim) created on first new write
- Both dimensions remain accessible
- Manual deletion of old dimension collections possible
```

**空集合查询：**
```
Scenario: Query a collection that has never received data
Behavior:
- Collection doesn't exist (never created)
- Query returns empty list
- No error state
- System logs: "Collection does not exist, returning empty results"
```

## 实现说明

### 存储后端特定说明

**Qdrant:**
使用 `collection_exists()` 进行存在性检查
使用 `get_collections()` 在删除期间进行列表操作
集合创建需要 `VectorParams(size=dim, distance=Distance.COSINE)`

**Pinecone:**
使用 `has_index()` 进行存在性检查
使用 `list_indexes()` 在删除期间进行列表操作
索引创建需要等待 "ready" 状态
Serverless 规格配置为云/区域

**Milvus:**
直接类 (`DocVectors`, `EntityVectors`) 管理生命周期
内部缓存 `self.collections[(dim, user, collection)]` 用于提高性能
集合名称经过清理（仅限字母数字 + 下划线）
支持具有自动递增 ID 的模式

### 性能考虑

**首次写入延迟:**
由于集合创建而产生的额外开销
Qdrant: ~100-500 毫秒
Pinecone: ~10-30 秒 (serverless 预配置)
Milvus: ~500-2000 毫秒 (包括索引)

**查询性能:**
存在性检查会增加最小的开销 (~1-10 毫秒)
集合存在后，不会对性能产生影响
每个维度集合都独立优化

**存储开销:**
每个集合的元数据非常少
主要开销是每个维度的存储
权衡：存储空间与维度灵活性

## 未来考虑

**自动维度合并:**
可以添加后台进程来识别和合并未使用的维度变体
这将需要重新嵌入或降维

**维度发现:**
可以公开 API 来列出集合中使用的所有维度
对于管理和监控非常有用

**默认维度偏好:**
可以跟踪每个集合的 "主" 维度
用于在维度上下文不可用的情况下进行查询

**存储配额:**
可能需要每个集合的维度限制
防止维度变体的过度繁殖

## 迁移说明

**从预维度后缀系统:**
旧集合：`d_{user}_{collection}` (没有维度后缀)
新集合：`d_{user}_{collection}_{dim}` (带有维度后缀)
没有自动迁移 - 旧集合仍然可以访问
如果需要，请考虑手动迁移脚本
可以同时运行这两种命名方案

## 引用

集合管理：`docs/tech-specs/collection-management.md`
存储模式：`trustgraph-base/trustgraph/schema/services/storage.py`
Librarian 服务：`trustgraph-flow/trustgraph/librarian/service.py`
