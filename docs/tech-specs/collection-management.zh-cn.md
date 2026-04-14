---
layout: default
title: "Collection Management Technical Specification"
parent: "Chinese (Beta)"
---

# Collection Management Technical Specification

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Overview

本规范描述了 TrustGraph 的集合管理功能，要求显式创建集合，并提供对集合生命周期的直接控制。在开始使用之前，必须显式创建集合，以确保 librarian 元数据与所有存储后端之间的正确同步。该功能支持四个主要用例：

1. **集合创建 (Collection Creation)**: 在存储数据之前，显式创建集合。
2. **集合列表 (Collection Listing)**: 查看系统中所有现有的集合。
3. **集合元数据管理 (Collection Metadata Management)**: 更新集合的名称、描述和标签。
4. **集合删除 (Collection Deletion)**: 删除集合及其关联的数据，包括所有存储类型。

## Goals

**显式集合创建 (Explicit Collection Creation)**: 要求在存储数据之前创建集合。
**存储同步 (Storage Synchronization)**: 确保集合存在于所有存储后端（向量、对象、三元组）中。
**集合可见性 (Collection Visibility)**: 允许用户列出并检查其环境中的所有集合。
**集合清理 (Collection Cleanup)**: 允许删除不再需要的集合。
**集合组织 (Collection Organization)**: 支持标签和标记，以便更好地跟踪和发现集合。
**元数据管理 (Metadata Management)**: 为集合关联有意义的元数据，以提高操作的清晰度。
**集合发现 (Collection Discovery)**: 通过过滤和搜索，更容易找到特定的集合。
**操作透明性 (Operational Transparency)**: 提供对集合生命周期和使用的清晰可见性。
**资源管理 (Resource Management)**: 允许清理未使用的集合，以优化资源利用率。
**数据完整性 (Data Integrity)**: 阻止在存储中出现没有元数据跟踪的孤立集合。

## Background

以前，TrustGraph 中的集合是在数据加载操作期间隐式创建的，这会导致同步问题，即集合可能存在于存储后端中，但 librarian 中没有相应的元数据。这带来了管理挑战和潜在的数据孤立问题。

显式集合创建模型通过以下方式解决了这些问题：
通过 `tg-set-collection` 要求在开始使用之前创建集合。
将集合创建广播到所有存储后端。
维护 librarian 元数据和存储之间的同步状态。
阻止写入不存在的集合。
提供清晰的集合生命周期管理。

本规范定义了显式集合管理模型。通过要求显式创建集合，TrustGraph 确保：
集合从创建开始就在 librarian 元数据中进行跟踪。
在接收数据之前，所有存储后端都了解集合。
存储中不存在孤立的集合。
对集合生命周期具有清晰的操作可见性和控制。
当操作引用不存在的集合时，提供一致的错误处理。

## Technical Design

### Architecture

集合管理系统将实现于现有的 TrustGraph 基础设施中：

1. **Librarian Service Integration**
   集合管理操作将被添加到现有的 librarian 服务中。
   不需要新的服务 - 利用现有的身份验证和访问模式。
   处理集合列表、删除和元数据管理。

   模块: trustgraph-librarian

2. **Cassandra Collection Metadata Table**
   在现有的 librarian keyspace 中创建一个新的表。
   存储具有用户范围访问权限的集合元数据。
   主键：(user_id, collection_id)，用于适当的多租户支持。

   模块: trustgraph-librarian

3. **Collection Management CLI**
   用于集合操作的命令行界面。
   提供列表、删除、标签和标记管理命令。
   与现有的 CLI 框架集成。

   模块: trustgraph-cli

### Data Models

#### Cassandra Collection Metadata Table

集合元数据将存储在 librarian keyspace 中的结构化 Cassandra 表中：

```sql
CREATE TABLE collections (
    user text,
    collection text,
    name text,
    description text,
    tags set<text>,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (user, collection)
);
```

表结构:
**user** + **collection**: 复合主键，确保用户隔离
**name**: 人类可读的集合名称
**description**: 集合用途的详细描述
**tags**: 用于分类和过滤的标签集合
**created_at**: 集合创建时间戳
**updated_at**: 最后修改时间戳

此方法允许:
多租户集合管理，具有用户隔离
通过用户和集合进行高效查询
灵活的标签系统，用于组织
生命周期跟踪，用于运营洞察

#### 集合生命周期

在进行任何数据操作之前，必须在 librarian 中显式创建集合：

1. **集合创建** (两种路径):

   **路径 A: 用户发起创建** 通过 `tg-set-collection`:
   用户提供集合 ID、名称、描述和标签
   Librarian 在 `collections` 表中创建元数据记录
   Librarian 向所有存储后端广播 "create-collection"
   所有存储处理器创建集合并确认成功
   集合现在可以用于数据操作

   **路径 B: 在文档提交时自动创建**:
   用户提交指定集合 ID 的文档
   Librarian 检查集合是否存在于元数据表中
   如果不存在: Librarian 使用默认值创建元数据 (name=collection_id, 描述/标签为空)
   Librarian 向所有存储后端广播 "create-collection"
   所有存储处理器创建集合并确认成功
   文档处理继续，此时集合已建立

   两种路径都确保集合存在于 librarian 元数据中，并且所有存储后端都已同步，然后再允许进行数据操作。

2. **存储验证**: 写入操作验证集合是否存在:
   存储处理器在接受写入操作之前检查集合状态
   写入不存在的集合会返回错误
   这可以防止直接写入绕过 librarian 的集合创建逻辑

3. **查询行为**: 查询操作可以优雅地处理不存在的集合:
   查询不存在的集合会返回空结果
   不会为查询操作抛出错误
   允许探索，而无需集合存在

4. **元数据更新**: 用户可以在创建后更新集合元数据:
   通过 `tg-set-collection` 更新名称、描述和标签
   更新仅应用于 librarian 元数据
   存储后端保留集合，但元数据更新不会传播

5. **显式删除**: 用户通过 `tg-delete-collection` 删除集合:
   Librarian 向所有存储后端广播 "delete-collection"
   等待来自所有存储处理器的确认
   仅在存储清理完成后删除 librarian 元数据记录
   确保存储中没有孤立数据

**关键原则**: librarian 是集合创建的唯一控制点。 无论是通过用户命令还是文档提交发起，librarian 都会确保在允许进行数据操作之前，正确跟踪元数据并与存储后端同步。

需要的操作:
**创建集合**: 通过 `tg-set-collection` 进行用户操作，或在文档提交时自动进行
**更新集合元数据**: 用户操作，用于修改名称、描述和标签
**删除集合**: 用户操作，用于删除集合及其数据，删除所有存储中的数据
**列出集合**: 用户操作，用于查看带有标签过滤的集合

#### 多存储集合管理

集合存在于 TrustGraph 中的多个存储后端中:
**向量存储** (Qdrant, Milvus, Pinecone): 存储嵌入和向量数据
**对象存储** (Cassandra): 存储文档和文件数据
**三元存储** (Cassandra, Neo4j, Memgraph, FalkorDB): 存储图/RDF 数据

Each store type implements:
**Collection State Tracking**: Maintain knowledge of which collections exist
**Collection Creation**: Accept and process "create-collection" operations
**Collection Validation**: Check collection exists before accepting writes
**Collection Deletion**: Remove all data for specified collection

The librarian service coordinates collection operations across all store types, ensuring:
Collections created in all backends before use
All backends confirm creation before returning success
Synchronized collection lifecycle across storage types
Consistent error handling when collections don't exist

#### Collection State Tracking by Storage Type

Each storage backend tracks collection state differently based on its capabilities:

**Cassandra Triple Store:**
Uses existing `triples_collection` table
Creates system marker triple when collection created
Query: `SELECT collection FROM triples_collection WHERE collection = ? LIMIT 1`
Efficient single-partition check for collection existence

**Qdrant/Milvus/Pinecone Vector Stores:**
Native collection APIs provide existence checking
Collections created with proper vector configuration
`collection_exists()` method uses storage API
Collection creation validates dimension requirements

**Neo4j/Memgraph/FalkorDB Graph Stores:**
Use `:CollectionMetadata` nodes to track collections
Node properties: `{user, collection, created_at}`
Query: `MATCH (c:CollectionMetadata {user: $user, collection: $collection})`
Separate from data nodes for clean separation
Enables efficient collection listing and validation

**Cassandra Object Store:**
Uses collection metadata table or marker rows
Similar pattern to triple store
Validates collection before document writes

### APIs

Collection Management APIs (Librarian):
**Create/Update Collection**: Create new collection or update existing metadata via `tg-set-collection`
**List Collections**: Retrieve collections for a user with optional tag filtering
**Delete Collection**: Remove collection and associated data, cascading to all store types

Storage Management APIs (All Storage Processors):
**Create Collection**: Handle "create-collection" operation, establish collection in storage
**Delete Collection**: Handle "delete-collection" operation, remove all collection data
**Collection Exists Check**: Internal validation before accepting write operations

Data Operation APIs (Modified Behavior):
**Write APIs**: Validate collection exists before accepting data, return error if not
**Query APIs**: Return empty results for non-existent collections without error

### Implementation Details

The implementation will follow existing TrustGraph patterns for service integration and CLI command structure.

#### Collection Deletion Cascade

When a user initiates collection deletion through the librarian service:

1. **Metadata Validation**: Verify collection exists and user has permission to delete
2. **Store Cascade**: Librarian coordinates deletion across all store writers:
   Vector store writer: Remove embeddings and vector indexes for the user and collection
   Object store writer: Remove documents and files for the user and collection
   Triple store writer: Remove graph data and triples for the user and collection
3. **Metadata Cleanup**: Remove collection metadata record from Cassandra
4. **Error Handling**: If any store deletion fails, maintain consistency through rollback or retry mechanisms

#### Collection Management Interface

**⚠️ LEGACY APPROACH - REPLACED BY CONFIG-BASED PATTERN**

The queue-based architecture described below has been replaced with a config-based approach using `CollectionConfigHandler`. All storage backends now receive collection updates via config push messages instead of dedicated management queues.

~~All store writers implement a standardized collection management interface with a common schema:~~

~~**Message Schema (`StorageManagementRequest`):**~~
```json
{
  "operation": "create-collection" | "delete-collection",
  "user": "user123",
  "collection": "documents-2024"
}
```

~~**队列架构：**~~
~~**向量存储管理队列** (`vector-storage-management`): 向量/嵌入式存储~~
~~**对象存储管理队列** (`object-storage-management`): 对象/文档存储~~
~~**三元组存储管理队列** (`triples-storage-management`): 图/RDF 存储~~
~~**存储响应队列** (`storage-management-response`): 所有响应都发送到此处~~

**当前实现：**

所有存储后端现在都使用 `CollectionConfigHandler`:
**配置推送集成**: 存储服务注册以接收配置推送通知
**自动同步**: 基于配置更改创建/删除集合
**声明式模型**: 集合在配置服务中定义，后端同步以匹配
**无请求/响应**: 消除协调开销和响应跟踪
**集合状态跟踪**: 通过 `known_collections` 缓存维护
**幂等操作**: 安全地多次处理相同的配置

每个存储后端实现：
`create_collection(user: str, collection: str, metadata: dict)` - 创建集合结构
`delete_collection(user: str, collection: str)` - 移除所有集合数据
`collection_exists(user: str, collection: str) -> bool` - 在写入之前进行验证

#### Cassandra 三元组存储重构

作为此实现的组成部分，Cassandra 三元组存储将从每个集合一个表的模型重构为统一的表模型：

**当前架构：**
每个用户的键空间，每个集合的单独表
模式：`(s, p, o)` with `PRIMARY KEY (s, p, o)`
表名：用户集合成为单独的 Cassandra 表

**新的架构：**
每个用户的键空间，用于所有集合的单个 "triples" 表
模式：`(collection, s, p, o)` with `PRIMARY KEY (collection, s, p, o)`
通过集合分区实现集合隔离

**需要更改的内容：**

1. **TrustGraph 类重构** (`trustgraph/direct/cassandra.py`):
   移除构造函数中的 `table` 参数，使用固定的 "triples" 表
   在所有方法中添加 `collection` 参数
   更新模式以包含集合作为第一列
   **索引更新**: 将创建新的索引以支持所有 8 个查询模式：
     在 `(s)` 上创建索引以进行基于主体的查询
     在 `(p)` 上创建索引以进行基于谓词的查询
     在 `(o)` 上创建索引以进行基于对象的查询
     注意：Cassandra 不支持多列二级索引，因此这些是单列索引

   **查询模式性能：**
     ✅ `get_all()` - 在 `collection` 上进行分区扫描
     ✅ `get_s(s)` - 效率地使用主键 (`collection, s`)
     ✅ `get_p(p)` - 使用 `idx_p` 并进行 `collection` 过滤
     ✅ `get_o(o)` - 使用 `idx_o` 并进行 `collection` 过滤
     ✅ `get_sp(s, p)` - 效率地使用主键 (`collection, s, p`)
     ⚠️ `get_po(p, o)` - 需要 `ALLOW FILTERING` (使用 `idx_p` 或 `idx_o` 加上过滤)
     ✅ `get_os(o, s)` - 使用 `idx_o` 并进行额外的 `s` 过滤
     ✅ `get_spo(s, p, o)` - 效率地使用完整主键

   **关于 ALLOW FILTERING 的说明**: `get_po` 查询模式需要 `ALLOW FILTERING`，因为它需要谓词和对象约束，而没有合适的复合索引。 这是一个可以接受的，因为此查询模式比在典型的三元组存储用例中基于主体的查询不太常见。

2. **存储写入器更新** (`trustgraph/storage/triples/cassandra/write.py`):
   维护每个用户单个 TrustGraph 连接，而不是每个 (用户, 集合)
   将集合传递给插入操作
   通过减少连接数提高资源利用率

3. **查询服务更新** (`trustgraph/query/triples/cassandra/service.py`):
   每个用户的单个 TrustGraph 连接
   将集合传递给所有查询操作
   保持相同的查询逻辑，并带有集合参数

**优点：**
**简化集合删除**: 使用 `collection` 分区键删除所有 4 个表
**资源效率**: 减少数据库连接和表对象
**跨集合操作**: 更容易实现跨多个集合的操作
**一致的架构**: 与统一的集合元数据方法保持一致
**集合验证**: 可以通过 `triples_collection` 表轻松检查集合是否存在

集合操作在可能的情况下将是原子操作，并提供适当的错误处理和验证。

## 安全性考虑

集合管理操作需要适当的授权，以防止未经授权的访问或删除集合。 访问控制将与现有的 TrustGraph 安全模型保持一致。

## 性能考虑

集合列表操作可能需要分页，以适应具有大量集合的环境。 元数据查询应针对常见的过滤模式进行优化。

## 测试策略

综合测试将涵盖：
集合创建工作流程的端到端流程
存储后端同步
对不存在集合的写入验证
对不存在集合的查询处理
集合删除在所有存储中的级联操作
错误处理和恢复场景
每个存储后端的单元测试
跨存储操作的集成测试

## 实施状态

### ✅ 已完成的组件

1. **Librarian 集合管理服务** (`trustgraph-flow/trustgraph/librarian/collection_manager.py`)
   集合元数据 CRUD 操作（列表、更新、删除）
   通过 `LibraryTableStore` 与 Cassandra 集合元数据表集成
   集合删除在所有存储类型上的级联协调
   具有适当错误管理的异步请求/响应处理

2. **集合元数据模式** (`trustgraph-base/trustgraph/schema/services/collection.py`)
   `CollectionManagementRequest` 和 `CollectionManagementResponse` 模式
   `CollectionMetadata` 模式用于集合记录
   集合请求/响应队列主题定义

3. **存储管理模式** (`trustgraph-base/trustgraph/schema/services/storage.py`)
   `StorageManagementRequest` 和 `StorageManagementResponse` 模式
   定义了存储管理队列主题
   存储级别集合操作的消息格式

4. **Cassandra 4-表模式** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py`)
   用于查询性能的复合分区键
   `triples_collection` 表用于 SPO 查询和删除跟踪
   集合删除使用读后删除模式实现

### ✅ 迁移到基于配置的模式 - 已完成

**所有存储后端已从基于队列的模式迁移到基于配置的 `CollectionConfigHandler` 模式。**

已完成的迁移：
✅ `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`

所有后端现在：
继承自 `CollectionConfigHandler`
通过 `self.register_config_handler(self.on_collection_config)` 注册配置推送通知
实施 `create_collection(user, collection, metadata)` 和 `delete_collection(user, collection)`
使用 `collection_exists(user, collection)` 在写入之前进行验证
自动与配置服务更改同步

移除了旧的基于队列的基础设施：
✅ 移除了 `StorageManagementRequest` 和 `StorageManagementResponse` 模式
✅ 移除了存储管理队列主题定义
✅ 移除了所有后端中的存储管理生产者/消费者
✅ 移除了所有后端中的 `on_storage_management` 处理程序
