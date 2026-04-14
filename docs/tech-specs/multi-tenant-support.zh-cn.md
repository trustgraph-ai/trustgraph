---
layout: default
title: "技术规范：多租户支持"
parent: "Chinese (Beta)"
---

# 技术规范：多租户支持

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

通过修复参数名称不匹配的问题，从而解决阻止队列自定义的问题，并添加 Cassandra 键空间参数化，以实现多租户部署。

## 架构上下文

### 基于流的队列解析

TrustGraph 系统使用**基于流的架构**进行动态队列解析，该架构本质上支持多租户：

**流定义**存储在 Cassandra 中，并通过接口定义指定队列名称。
**队列名称使用模板**，其中包含 `{id}` 变量，这些变量会被替换为流实例 ID。
**服务在请求时动态解析队列**，通过查找流配置。
**每个租户可以拥有独特的流**，具有不同的队列名称，从而提供隔离。

示例流接口定义：
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

当租户 A 启动流程 `tenant-a-prod`，而租户 B 启动流程 `tenant-b-prod` 时，它们会自动获得隔离的队列：
`persistent://tg/flow/triples-store:tenant-a-prod`
`persistent://tg/flow/triples-store:tenant-b-prod`

**为多租户设计的服务：**
✅ **知识管理 (核心)** - 动态解析从请求中传递的流程配置中的队列

**需要修复的服务：**
🔴 **配置服务** - 参数名称不匹配，无法自定义队列
🔴 **图书管理员服务** - 预定义的存储管理主题（见下文）
🔴 **所有服务** - 无法自定义 Cassandra keyspace

## 问题描述

### 问题 #1：AsyncProcessor 中的参数名称不匹配
**CLI 定义：** `--config-queue` (命名不明确)
**Argparse 转换：** `config_queue` (在 params 字典中)
**代码查找：** `config_push_queue`
**结果：** 参数被忽略，默认为 `persistent://tg/config/config`
**影响：** 影响所有 32 多个从 AsyncProcessor 继承的服务
**问题：** 多租户部署无法使用租户特定的配置队列
**解决方案：** 将 CLI 参数重命名为 `--config-push-queue`，以提高清晰度（可以接受破坏性更改，因为该功能当前已损坏）

### 问题 #2：配置服务中的参数名称不匹配
**CLI 定义：** `--push-queue` (命名模糊)
**Argparse 转换：** `push_queue` (在 params 字典中)
**代码查找：** `config_push_queue`
**结果：** 参数被忽略
**影响：** 配置服务无法使用自定义推送队列
**解决方案：** 将 CLI 参数重命名为 `--config-push-queue`，以提高一致性和清晰度（可以接受破坏性更改）

### 问题 #3：预定义的 Cassandra Keyspace
**当前：** Keyspace 在各种服务中硬编码为 `"config"`、`"knowledge"`、`"librarian"`
**结果：** 无法为多租户部署自定义 keyspace
**影响：** 配置、核心和图书管理员服务
**问题：** 多个租户无法使用单独的 Cassandra keyspace

### 问题 #4：集合管理架构 ✅ 已完成
**之前：** 集合存储在图书管理员 keyspace 中的单独的集合表中
**之前：** 图书管理员使用 4 个硬编码的存储管理主题来协调集合创建/删除：
  `vector_storage_management_topic`
  `object_storage_management_topic`
  `triples_storage_management_topic`
  `storage_management_response_topic`
**问题（已解决）：**
  无法为多租户部署自定义硬编码主题
  图书管理员和 4 个或更多存储服务之间的复杂异步协调
  单独的 Cassandra 表和管理基础设施
  关键操作的非持久性请求/响应队列
**已实施的解决方案：** 将集合迁移到配置服务存储，使用配置推送进行分发
**状态：** 所有存储后端已迁移到 `CollectionConfigHandler` 模式

## 解决方案

此规范解决了问题 #1、#2、#3 和 #4。

### 第一部分：修复参数名称不匹配

#### 更改 1：AsyncProcessor 基类 - 重命名 CLI 参数
**文件：** `trustgraph-base/trustgraph/base/async_processor.py`
**行：** 260-264

**当前：**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**已修复：**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**理由：**
命名更清晰、更明确
与内部变量名 `config_push_queue` 匹配
允许进行重大更改，因为该功能目前不可用
params.get() 不需要任何代码更改，因为它已经查找正确的名称

#### 更改 2：配置服务 - 重命名 CLI 参数
**文件：** `trustgraph-flow/trustgraph/config/service/service.py`
**行：** 276-279

**当前：**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**固定：**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**理由：**
更清晰的命名 - "config-push-queue" 比仅仅 "push-queue" 更明确。
与内部变量名 `config_push_queue` 匹配。
与 AsyncProcessor 的 `--config-push-queue` 参数一致。
即使是重大更改，也是可以接受的，因为该功能目前不可用。
params.get() 中不需要任何代码更改 - 它已经查找正确的名称。

### 第二部分：添加 Cassandra 键空间参数化

#### 更改 3：向 cassandra_config 模块添加键空间参数
**文件：** `trustgraph-base/trustgraph/base/cassandra_config.py`

**添加 CLI 参数**（在 `add_cassandra_args()` 函数中）：
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**添加环境变量支持** (在 `resolve_cassandra_config()` 函数中):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**更新 `resolve_cassandra_config()` 的返回值：**
当前返回：`(hosts, username, password)`
更改为返回：`(hosts, username, password, keyspace)`

**理由：**
与现有的 Cassandra 配置模式一致
通过 `add_cassandra_args()` 可供所有服务使用
支持 CLI 和环境变量配置

#### 变更 4：配置服务 - 使用参数化 Keyspace
**文件：** `trustgraph-flow/trustgraph/config/service/service.py`

**第 30 行** - 移除硬编码的 Keyspace：
```python
# DELETE THIS LINE:
keyspace = "config"
```

**第69-73行** - 更新 Cassandra 配置解析：

**当前：**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**已修复：**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**原因：**
保持与默认值为 "config" 的配置向后兼容。
允许通过 `--cassandra-keyspace` 或 `CASSANDRA_KEYSPACE` 进行覆盖。

#### 变更 5：核心/知识服务 - 使用参数化键空间
**文件：** `trustgraph-flow/trustgraph/cores/service.py`

**第 37 行** - 移除硬编码的键空间：
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**更新 Cassandra 配置解析**（位置类似于配置服务）：
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### 变更 6：图书管理员服务 - 使用参数化键空间
**文件：** `trustgraph-flow/trustgraph/librarian/service.py`

**第 51 行** - 移除硬编码的键空间：
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**更新 Cassandra 配置解析**（位置与配置服务类似）：
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

### 第三部分：将集合管理迁移到配置服务

#### 概述
将集合从 Cassandra librarian 键空间迁移到配置服务存储。这消除了硬编码的存储管理主题，并通过使用现有的配置推送机制进行分发，简化了架构。

#### 当前架构
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### 新架构
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### 变更 7：集合管理器 - 使用配置服务 API
**文件：** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**移除：**
`LibraryTableStore` 的使用（第 33 行，第 40-41 行）
存储管理生产者初始化（第 86-140 行）
`on_storage_response` 方法（第 400-430 行）
`pending_deletions` 跟踪（第 57 行，第 90-96 行，以及整个使用过程）

**添加：**
用于 API 调用的配置服务客户端（请求/响应模式）

**配置客户端设置：**
```python
# In __init__, add config request/response producers/consumers
from trustgraph.schema.services.config import ConfigRequest, ConfigResponse

# Producer for config requests
self.config_request_producer = Producer(
    client=pulsar_client,
    topic=config_request_queue,
    schema=ConfigRequest,
)

# Consumer for config responses (with correlation ID)
self.config_response_consumer = Consumer(
    taskgroup=taskgroup,
    client=pulsar_client,
    flow=None,
    topic=config_response_queue,
    subscriber=f"{id}-config",
    schema=ConfigResponse,
    handler=self.on_config_response,
)

# Tracking for pending config requests
self.pending_config_requests = {}  # request_id -> asyncio.Event
```

**修改 `list_collections` (第145-180行):**
```python
async def list_collections(self, user, tag_filter=None, limit=None):
    """List collections from config service"""
    # Send getvalues request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='getvalues',
        type='collections',
    )

    # Send request and wait for response
    response = await self.send_config_request(request)

    # Parse collections from response
    collections = []
    for key, value_json in response.values.items():
        if ":" in key:
            coll_user, collection = key.split(":", 1)
            if coll_user == user:
                metadata = json.loads(value_json)
                collections.append(CollectionMetadata(**metadata))

    # Apply tag filtering in-memory (as before)
    if tag_filter:
        collections = [c for c in collections if any(tag in c.tags for tag in tag_filter)]

    # Apply limit
    if limit:
        collections = collections[:limit]

    return collections

async def send_config_request(self, request):
    """Send config request and wait for response"""
    event = asyncio.Event()
    self.pending_config_requests[request.id] = event

    await self.config_request_producer.send(request)
    await event.wait()

    return self.pending_config_requests.pop(request.id + "_response")

async def on_config_response(self, message, consumer, flow):
    """Handle config response"""
    response = message.value()
    if response.id in self.pending_config_requests:
        self.pending_config_requests[response.id + "_response"] = response
        self.pending_config_requests[response.id].set()
```

**修改 `update_collection` (第182-312行):**
```python
async def update_collection(self, user, collection, name, description, tags):
    """Update collection via config service"""
    # Create metadata
    metadata = CollectionMetadata(
        user=user,
        collection=collection,
        name=name,
        description=description,
        tags=tags,
    )

    # Send put request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='put',
        type='collections',
        key=f'{user}:{collection}',
        value=json.dumps(metadata.to_dict()),
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config update failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and create collections
```

**修改 `delete_collection` (第314-398行):**
```python
async def delete_collection(self, user, collection):
    """Delete collection via config service"""
    # Send delete request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='delete',
        type='collections',
        key=f'{user}:{collection}',
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config delete failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and delete collections
```

**集合元数据格式:**
存储在配置表中，格式为：`class='collections', key='user:collection'`
值是 JSON 序列化的 CollectionMetadata (不包含时间戳字段)
字段：`user`, `collection`, `name`, `description`, `tags`
示例：`class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### 变更 8: Librarian Service - 移除存储管理基础设施
**文件:** `trustgraph-flow/trustgraph/librarian/service.py`

**移除:**
存储管理生产者 (173-190 行):
  `vector_storage_management_producer`
  `object_storage_management_producer`
  `triples_storage_management_producer`
存储响应消费者 (192-201 行)
`on_storage_response` 处理程序 (467-473 行)

**修改:**
CollectionManager 初始化 (215-224 行) - 移除存储生产者参数

**注意:** 外部集合 API 保持不变:
`list-collections`
`update-collection`
`delete-collection`

#### 变更 9: 从 LibraryTableStore 中移除 Collections 表
**文件:** `trustgraph-flow/trustgraph/tables/library.py`

**删除:**
Collections 表的 CREATE 语句 (114-127 行)
Collections 预处理语句 (205-240 行)
所有集合方法 (578-717 行):
  `ensure_collection_exists`
  `list_collections`
  `update_collection`
  `delete_collection`
  `get_collection`
  `create_collection`

**原因:**
集合现在存储在配置表中
这是一个破坏性变更，但无需数据迁移
显著简化了 librarian service

#### 变更 10: 存储服务 - 基于配置的集合管理 ✅ 已完成

**状态:** 所有 11 个存储后端都已迁移到使用 `CollectionConfigHandler`。

**受影响的服务 (总共 11 个):**
文档嵌入: milvus, pinecone, qdrant
图嵌入: milvus, pinecone, qdrant
对象存储: cassandra
三元组存储: cassandra, falkordb, memgraph, neo4j

**文件:**
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
`trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
`trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`

**实现模式 (所有服务):**

1. **在 `__init__` 中注册配置处理程序:**
```python
# Add after AsyncProcessor initialization
self.register_config_handler(self.on_collection_config)
self.known_collections = set()  # Track (user, collection) tuples
```

2. **实现配置处理器：**
```python
async def on_collection_config(self, config, version):
    """Handle collection configuration updates"""
    logger.info(f"Collection config version: {version}")

    if "collections" not in config:
        return

    # Parse collections from config
    # Key format: "user:collection" in config["collections"]
    config_collections = set()
    for key in config["collections"].keys():
        if ":" in key:
            user, collection = key.split(":", 1)
            config_collections.add((user, collection))

    # Determine changes
    to_create = config_collections - self.known_collections
    to_delete = self.known_collections - config_collections

    # Create new collections (idempotent)
    for user, collection in to_create:
        try:
            await self.create_collection_internal(user, collection)
            self.known_collections.add((user, collection))
            logger.info(f"Created collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to create {user}/{collection}: {e}")

    # Delete removed collections (idempotent)
    for user, collection in to_delete:
        try:
            await self.delete_collection_internal(user, collection)
            self.known_collections.discard((user, collection))
            logger.info(f"Deleted collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to delete {user}/{collection}: {e}")
```

3. **初始化启动时的已知集合：**
```python
async def start(self):
    """Start the processor"""
    await super().start()
    await self.sync_known_collections()

async def sync_known_collections(self):
    """Query backend to populate known_collections set"""
    # Backend-specific implementation:
    # - Milvus/Pinecone/Qdrant: List collections/indexes matching naming pattern
    # - Cassandra: Query keyspaces or collection metadata
    # - Neo4j/Memgraph/FalkorDB: Query CollectionMetadata nodes
    pass
```

4. **重构现有的处理方法：**
```python
# Rename and remove response sending:
# handle_create_collection → create_collection_internal
# handle_delete_collection → delete_collection_internal

async def create_collection_internal(self, user, collection):
    """Create collection (idempotent)"""
    # Same logic as current handle_create_collection
    # But remove response producer calls
    # Handle "already exists" gracefully
    pass

async def delete_collection_internal(self, user, collection):
    """Delete collection (idempotent)"""
    # Same logic as current handle_delete_collection
    # But remove response producer calls
    # Handle "not found" gracefully
    pass
```

5. **移除存储管理基础设施：**
   移除 `self.storage_request_consumer` 的配置和启动
   移除 `self.storage_response_producer` 的配置
   移除 `on_storage_management` 的调度器方法
   移除存储管理的指标
   移除导入：`StorageManagementRequest`, `StorageManagementResponse`

**后端特定注意事项：**

**向量存储 (Milvus, Pinecone, Qdrant):** 跟踪 `(user, collection)` 在 `known_collections` 中的逻辑，但可能会为每个维度创建多个后端集合。继续采用延迟创建模式。删除操作必须删除所有维度变体。

**Cassandra Objects:** 集合是行属性，而不是结构。跟踪键空间级别的信息。

**图数据库 (Neo4j, Memgraph, FalkorDB):** 启动时查询 `CollectionMetadata` 节点。在同步时创建/删除元数据节点。

**Cassandra 三元组:** 使用 `KnowledgeGraph` API 进行集合操作。

**关键设计要点：**

**最终一致性:** 没有请求/响应机制，配置推送是广播的
**幂等性:** 所有创建/删除操作都必须可以安全重试
**错误处理:** 记录错误，但不要阻止配置更新
**自愈:** 失败的操作将在下一次配置推送时重试
**集合键格式:** `"user:collection"` 在 `config["collections"]` 中

#### 变更 11：更新集合模式 - 移除时间戳
**文件:** `trustgraph-base/trustgraph/schema/services/collection.py`

**修改 CollectionMetadata (第 13-21 行):**
移除 `created_at` 和 `updated_at` 字段：
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**修改 CollectionManagementRequest (第 25-47 行):**
移除时间戳字段：
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**Rationale:**
Timestamps don't add value for collections
Config service maintains its own version tracking
Simplifies schema and reduces storage

#### Benefits of Config Service Migration

1. ✅ **Eliminates hardcoded storage management topics** - Solves multi-tenant blocker
2. ✅ **Simpler coordination** - No complex async waiting for 4+ storage responses
3. ✅ **Eventual consistency** - Storage services update independently via config push
4. ✅ **Better reliability** - Persistent config push vs non-persistent request/response
5. ✅ **Unified configuration model** - Collections treated as configuration
6. ✅ **Reduces complexity** - Removes ~300 lines of coordination code
7. ✅ **Multi-tenant ready** - Config already supports tenant isolation via keyspace
8. ✅ **Version tracking** - Config service version mechanism provides audit trail

## Implementation Notes

### Backward Compatibility

**Parameter Changes:**
CLI parameter renames are breaking changes but acceptable (feature currently non-functional)
Services work without parameters (use defaults)
Default keyspaces preserved: "config", "knowledge", "librarian"
Default queue: `persistent://tg/config/config`

**Collection Management:**
**Breaking change:** Collections table removed from librarian keyspace
**No data migration provided** - acceptable for this phase
External collection API unchanged (list/update/delete operations)
Collection metadata format simplified (timestamps removed)

### Testing Requirements

**Parameter Testing:**
1. Verify `--config-push-queue` parameter works on graph-embeddings service
2. Verify `--config-push-queue` parameter works on text-completion service
3. Verify `--config-push-queue` parameter works on config service
4. Verify `--cassandra-keyspace` parameter works for config service
5. Verify `--cassandra-keyspace` parameter works for cores service
6. Verify `--cassandra-keyspace` parameter works for librarian service
7. Verify services work without parameters (uses defaults)
8. Verify multi-tenant deployment with custom queue names and keyspace

**Collection Management Testing:**
9. Verify `list-collections` operation via config service
10. Verify `update-collection` creates/updates in config table
11. Verify `delete-collection` removes from config table
12. Verify config push is triggered on collection updates
13. Verify tag filtering works with config-based storage
14. Verify collection operations work without timestamp fields

### Multi-Tenant Deployment Example
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## 影响分析

### 受变更 1-2 影响的服务 (CLI 参数重命名)
所有继承自 AsyncProcessor 或 FlowProcessor 的服务：
config-service
cores-service
librarian-service
graph-embeddings
document-embeddings
text-completion-* (所有提供者)
extract-* (所有提取器)
query-* (所有查询服务)
retrieval-* (所有 RAG 服务)
storage-* (所有存储服务)
还有 20 多个服务

### 受变更 3-6 影响的服务 (Cassandra Keyspace)
config-service
cores-service
librarian-service

### 受变更 7-11 影响的服务 (集合管理)

**即时变更：**
librarian-service (collection_manager.py, service.py)
tables/library.py (删除 collections 表)
schema/services/collection.py (删除时间戳)

**已完成的变更 (变更 10)：** ✅
所有存储服务 (共 11 个) - 已迁移到配置推送，用于通过 `CollectionConfigHandler` 更新集合
存储管理模式已从 `storage.py` 中移除

## 未来考虑

### 基于用户的 Keyspace 模式

一些服务使用 **基于用户的 Keyspace** 动态模式，其中每个用户都拥有自己的 Cassandra Keyspace：

**使用基于用户的 Keyspace 的服务：**
1. **三元组查询服务** (`trustgraph-flow/trustgraph/query/triples/cassandra/service.py:65`)
   使用 `keyspace=query.user`
2. **对象查询服务** (`trustgraph-flow/trustgraph/query/objects/cassandra/service.py:479`)
   使用 `keyspace=self.sanitize_name(user)`
3. **知识图谱直接访问** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py:18`)
   默认参数 `keyspace="trustgraph"`

**状态：** 这些 **未进行修改**，在本规范中。

**需要未来审查：**
评估基于用户的 Keyspace 模式是否会产生租户隔离问题
考虑是否需要为多租户部署使用 Keyspace 前缀模式 (例如，`tenant_a_user1`)
审查是否存在用户 ID 在租户之间的冲突
评估是否更倾向于使用单个共享 Keyspace，每个租户使用基于用户的行隔离

**注意：** 这不会阻止当前的 multi-tenant 实现，但在进行生产 multi-tenant 部署之前应进行审查。

## 实施阶段

### 第一阶段：参数修复 (变更 1-6)
修复 `--config-push-queue` 参数命名
添加 `--cassandra-keyspace` 参数支持
**结果：** 启用了 multi-tenant 队列和 Keyspace 配置

### 第二阶段：集合管理迁移 (变更 7-9, 11)
将集合存储迁移到配置服务
从 librarian 中删除 collections 表
更新集合模式 (删除时间戳)
**结果：** 消除硬编码的存储管理主题，简化 librarian

### 第三阶段：存储服务更新 (变更 10) ✅ 已完成
所有存储服务已更新为使用配置推送进行集合管理，通过 `CollectionConfigHandler`
移除了存储管理请求/响应基础设施
移除了旧的模式定义
**结果：** 实现了基于配置的集合管理

## 引用
GitHub Issue: https://github.com/trustgraph-ai/trustgraph/issues/582
相关文件：
  `trustgraph-base/trustgraph/base/async_processor.py`
  `trustgraph-base/trustgraph/base/cassandra_config.py`
  `trustgraph-base/trustgraph/schema/core/topic.py`
  `trustgraph-base/trustgraph/schema/services/collection.py`
  `trustgraph-flow/trustgraph/config/service/service.py`
  `trustgraph-flow/trustgraph/cores/service.py`
  `trustgraph-flow/trustgraph/librarian/service.py`
  `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  `trustgraph-flow/trustgraph/tables/library.py`
