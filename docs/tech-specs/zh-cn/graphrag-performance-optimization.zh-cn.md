---
layout: default
title: "GraphRAG 性能优化技术规范"
parent: "Chinese (Beta)"
---

# GraphRAG 性能优化技术规范

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

本规范描述了 TrustGraph 中 GraphRAG (基于图的检索增强生成) 算法的全面性能优化。当前的实现存在严重的性能瓶颈，限制了可扩展性和响应时间。本规范解决了四个主要的优化领域：

1. **图遍历优化**: 消除低效的递归数据库查询，并实现批量图探索
2. **标签解析优化**: 使用并行/批量操作替换顺序标签获取
3. **缓存策略增强**: 实现智能缓存，采用 LRU 淘汰策略和预取
4. **查询优化**: 添加结果记忆化和嵌入式缓存，以提高响应时间

## 目标

**减少数据库查询量**: 通过批量和缓存，实现总数据库查询量减少 50-80%
**提高响应时间**: 目标是子图构建速度提高 3-5 倍，标签解析速度提高 2-3 倍
<<<<<<< HEAD
**增强可扩展性**: 更好地管理内存，支持更大的知识图谱
=======
**增强可扩展性**: 通过更好的内存管理，支持更大的知识图谱
>>>>>>> 82edf2d (New md files from RunPod)
**保持准确性**: 保持现有的 GraphRAG 功能和结果质量
**启用并发性**: 提高并行处理能力，以支持多个并发请求
**减少内存占用**: 实现高效的数据结构和内存管理
**增加可观察性**: 包含性能指标和监控功能
**确保可靠性**: 添加适当的错误处理和超时机制

## 背景

在 `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` 中的当前 GraphRAG 实现存在几个关键的性能问题，严重影响系统的可扩展性：

### 当前性能问题

**1. 低效的图遍历 (`follow_edges` 函数，第 79-127 行)**
对每个实体，每个深度级别执行 3 次独立的数据库查询
查询模式：针对主体、谓词和对象进行查询
没有批量处理：每次查询仅处理一个实体
没有循环检测：可以多次访问相同的节点
没有记忆化的递归实现会导致指数级复杂度
时间复杂度：O(entities × max_path_length × triple_limit³)

**2. 顺序的标签解析 (`get_labelgraph` 函数，第 144-171 行)**
顺序处理每个三元组组件 (主体、谓词、对象)
每次 `maybe_label` 调用可能触发数据库查询
没有并行执行或批量标签查询
导致最多 subgraph_size × 3 次独立的数据库调用

**3. 原始的缓存策略 (`maybe_label` 函数，第 62-77 行)**
简单的字典缓存，没有大小限制或 TTL
没有缓存淘汰策略会导致内存无限增长
缓存未命中会触发独立的数据库查询
没有预取或智能缓存预热

**4. 不佳的查询模式**
实体向量相似性查询在相似请求之间没有缓存
没有对重复查询模式进行结果记忆化
缺少针对常见访问模式的查询优化

**5. 关键的对象生命周期问题 (`rag.py:96-102`)**
**GraphRag 对象每个请求重新创建**: 为每个查询创建一个新的实例，失去所有缓存的好处
**查询对象寿命极短**: 在单个查询执行中创建和销毁 (第 201-207 行)
**标签缓存每个请求重置**: 缓存预热和积累的知识在请求之间丢失
**客户端重新创建开销**: 数据库客户端可能为每个请求重新建立
**没有跨请求优化**: 无法从查询模式或结果共享中受益

### 性能影响分析

当前典型查询的最坏情况：
**实体检索**: 1 次向量相似性查询
**图遍历**: entities × max_path_length × 3 × triple_limit 次查询
**标签解析**: subgraph_size × 3 次独立的标签查询

对于默认参数（50个实体，路径长度2，30个三元组限制，150个子图大小）：
**最小查询次数**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9,451次数据库查询**
**响应时间**: 中等大小图的响应时间为15-30秒
**内存使用**: 缓存会随着时间增长
**缓存有效性**: 0% - 每次请求都会重置缓存
<<<<<<< HEAD
**对象创建开销**: 每个请求都会创建/销毁GraphRag + Query对象

本规范通过实现批量查询、智能缓存和并行处理来解决这些问题。通过优化查询模式和数据访问，TrustGraph可以：
支持拥有数百万个实体的企业级知识图谱
为典型的查询提供亚秒级的响应时间
=======
**对象创建开销**: 每个请求会创建/销毁GraphRag + Query对象

本规范通过实现批量查询、智能缓存和并行处理来解决这些问题。通过优化查询模式和数据访问，TrustGraph可以：
支持拥有数百万个实体的企业级知识图谱
为典型查询提供亚秒级的响应时间
>>>>>>> 82edf2d (New md files from RunPod)
处理数百个并发的GraphRAG请求
随着图的大小和复杂性而高效扩展

## 技术设计

### 架构

GraphRAG性能优化需要以下技术组件：

#### 1. **对象生命周期架构重构**
   **使GraphRag具有长期生命周期**: 将GraphRag实例移动到处理器级别，以便在请求之间保持持久性
   **保留缓存**: 在请求之间维护标签缓存、嵌入缓存和查询结果缓存
   **优化Query对象**: 将Query重构为轻量级的执行上下文，而不是数据容器
   **连接持久化**: 在请求之间保持数据库客户端连接

   模块: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (已修改)

#### 2. **优化的图遍历引擎**
   使用迭代广度优先搜索替换递归的`follow_edges`
   在每个遍历级别实现批量实体处理
   添加循环检测，使用已访问节点跟踪
   在达到限制时包含早期终止

   模块: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **并行标签解析系统**
   批量查询多个实体的标签
   使用async/await模式进行并发数据库访问
   添加智能预取，用于常见的标签模式
   包含标签缓存预热策略

   模块: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **保守的标签缓存层**
   使用LRU缓存，仅对标签使用，TTL为5分钟，以平衡性能与一致性
   监控缓存指标和命中率
   **不缓存嵌入**: 已经针对每个查询进行缓存，没有跨查询的好处
   **不缓存查询结果**: 由于图的突变一致性问题

   模块: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **查询优化框架**
   查询模式分析和优化建议
   批量查询协调器，用于数据库访问
   连接池和查询超时管理
   性能监控和指标收集

   模块: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### 数据模型

#### 优化的图遍历状态

遍历引擎维护状态以避免重复操作：

```python
@dataclass
class TraversalState:
    visited_entities: Set[str]
    current_level_entities: Set[str]
    next_level_entities: Set[str]
    subgraph: Set[Tuple[str, str, str]]
    depth: int
    query_batch: List[TripleQuery]
```

这种方法允许：
<<<<<<< HEAD
通过跟踪访问的实体实现高效的循环检测
=======
通过跟踪访问过的实体实现高效的循环检测
>>>>>>> 82edf2d (New md files from RunPod)
在每个遍历层级进行批量查询准备
内存效率高的状态管理
当达到大小限制时，可以提前终止

#### 增强的缓存结构

```python
@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    access_count: int
    ttl: Optional[float]

class CacheManager:
    label_cache: LRUCache[str, CacheEntry]
    embedding_cache: LRUCache[str, CacheEntry]
    query_result_cache: LRUCache[str, CacheEntry]
    cache_stats: CacheStatistics
```

#### 批量查询结构

```python
@dataclass
class BatchTripleQuery:
    entities: List[str]
    query_type: QueryType  # SUBJECT, PREDICATE, OBJECT
    limit_per_entity: int

@dataclass
class BatchLabelQuery:
    entities: List[str]
    predicate: str = LABEL
```

### API 接口

#### 新增 API 接口：

**图遍历 API**
```python
async def optimized_follow_edges_batch(
    entities: List[str],
    max_depth: int,
    triple_limit: int,
    max_subgraph_size: int
) -> Set[Tuple[str, str, str]]
```

**批量标签解析 API**
```python
async def resolve_labels_batch(
    entities: List[str],
    cache_manager: CacheManager
) -> Dict[str, str]
```

**缓存管理 API**
```python
class CacheManager:
    async def get_or_fetch_label(self, entity: str) -> str
    async def get_or_fetch_embeddings(self, query: str) -> List[float]
    async def cache_query_result(self, query_hash: str, result: Any, ttl: int)
    def get_cache_statistics(self) -> CacheStatistics
```

#### 修改后的 API：

**GraphRag.query()** - 增强了性能优化：
<<<<<<< HEAD
添加了 cache_manager 参数以进行缓存控制
包含 performance_metrics 返回值
添加了 query_timeout 参数以提高可靠性

**Query 类** - 进行了重构，用于批量处理：
将单个实体处理替换为批量操作
添加了异步上下文管理器以进行资源清理
=======
添加 `cache_manager` 参数以进行缓存控制
包含 `performance_metrics` 返回值
添加 `query_timeout` 参数以提高可靠性

**Query 类** - 重新设计，用于批量处理：
将单个实体处理替换为批量操作
添加异步上下文管理器以进行资源清理
>>>>>>> 82edf2d (New md files from RunPod)
包含进度回调函数，用于长时间运行的操作

### 实施细节

#### 阶段 0：关键架构生命周期重构

**当前存在问题的实现：**
```python
# INEFFICIENT: GraphRag recreated every request
class Processor(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        # PROBLEM: New GraphRag instance per request!
        self.rag = GraphRag(
            embeddings_client = flow("embeddings-request"),
            graph_embeddings_client = flow("graph-embeddings-request"),
            triples_client = flow("triples-request"),
            prompt_client = flow("prompt-request"),
            verbose=True,
        )
        # Cache starts empty every time - no benefit from previous requests
        response = await self.rag.query(...)

# VERY SHORT-LIVED: Query object created/destroyed per request
class GraphRag:
    async def query(self, query, user="trustgraph", collection="default", ...):
        q = Query(rag=self, user=user, collection=collection, ...)  # Created
        kg = await q.get_labelgraph(query)  # Used briefly
        # q automatically destroyed when function exits
```

<<<<<<< HEAD
**优化后的长期运行架构：**
=======
**优化后的长寿命架构：**
>>>>>>> 82edf2d (New md files from RunPod)
```python
class Processor(FlowProcessor):
    def __init__(self, **params):
        super().__init__(**params)
        self.rag_instance = None  # Will be initialized once
        self.client_connections = {}

    async def initialize_rag(self, flow):
        """Initialize GraphRag once, reuse for all requests"""
        if self.rag_instance is None:
            self.rag_instance = LongLivedGraphRag(
                embeddings_client=flow("embeddings-request"),
                graph_embeddings_client=flow("graph-embeddings-request"),
                triples_client=flow("triples-request"),
                prompt_client=flow("prompt-request"),
                verbose=True,
            )
        return self.rag_instance

    async def on_request(self, msg, consumer, flow):
        # REUSE the same GraphRag instance - caches persist!
        rag = await self.initialize_rag(flow)

        # Query object becomes lightweight execution context
        response = await rag.query_with_context(
            query=v.query,
            execution_context=QueryContext(
                user=v.user,
                collection=v.collection,
                entity_limit=entity_limit,
                # ... other params
            )
        )

class LongLivedGraphRag:
    def __init__(self, ...):
        # CONSERVATIVE caches - balance performance vs consistency
        self.label_cache = LRUCacheWithTTL(max_size=5000, ttl=300)  # 5min TTL for freshness
        # Note: No embedding cache - already cached per-query, no cross-query benefit
        # Note: No query result cache due to consistency concerns
        self.performance_metrics = PerformanceTracker()

    async def query_with_context(self, query: str, context: QueryContext):
        # Use lightweight QueryExecutor instead of heavyweight Query object
        executor = QueryExecutor(self, context)  # Minimal object
        return await executor.execute(query)

@dataclass
class QueryContext:
    """Lightweight execution context - no heavy operations"""
    user: str
    collection: str
    entity_limit: int
    triple_limit: int
    max_subgraph_size: int
    max_path_length: int

class QueryExecutor:
    """Lightweight execution context - replaces old Query class"""
    def __init__(self, rag: LongLivedGraphRag, context: QueryContext):
        self.rag = rag
        self.context = context
        # No heavy initialization - just references

    async def execute(self, query: str):
        # All heavy lifting uses persistent rag caches
        return await self.rag.execute_optimized_query(query, self.context)
```

<<<<<<< HEAD
这种架构上的改变提供了：
**对于具有常见关系的图，数据库查询减少 10-20%**（相对于目前 0% 的减少）
**消除了每个请求中的对象创建开销**
=======
这一架构变更提供了：
**对于具有常见关系的图，数据库查询减少 10-20%**（相对于目前 0% 的减少）
**消除了每个请求的对象的创建开销**
>>>>>>> 82edf2d (New md files from RunPod)
**持久连接池和客户端重用**
**缓存 TTL 窗口内的跨请求优化**

**重要的缓存一致性限制：**
长期缓存会带来数据陈旧的风险，尤其是在底层图中删除或修改实体/标签时。 LRU 缓存和 TTL 在性能提升和数据新鲜度之间提供了一种平衡，但无法检测到实时图的变化。

#### 第一阶段：图遍历优化

**当前实现的缺点：**
```python
# INEFFICIENT: 3 queries per entity per level
async def follow_edges(self, ent, subgraph, path_length):
    # Query 1: s=ent, p=None, o=None
    res = await self.rag.triples_client.query(s=ent, p=None, o=None, limit=self.triple_limit)
    # Query 2: s=None, p=ent, o=None
    res = await self.rag.triples_client.query(s=None, p=ent, o=None, limit=self.triple_limit)
    # Query 3: s=None, p=None, o=ent
    res = await self.rag.triples_client.query(s=None, p=None, o=ent, limit=self.triple_limit)
```

**优化实现：**
```python
async def optimized_traversal(self, entities: List[str], max_depth: int) -> Set[Triple]:
    visited = set()
    current_level = set(entities)
    subgraph = set()

    for depth in range(max_depth):
        if not current_level or len(subgraph) >= self.max_subgraph_size:
            break

        # Batch all queries for current level
        batch_queries = []
        for entity in current_level:
            if entity not in visited:
                batch_queries.extend([
                    TripleQuery(s=entity, p=None, o=None),
                    TripleQuery(s=None, p=entity, o=None),
                    TripleQuery(s=None, p=None, o=entity)
                ])

        # Execute all queries concurrently
        results = await self.execute_batch_queries(batch_queries)

        # Process results and prepare next level
        next_level = set()
        for result in results:
            subgraph.update(result.triples)
            next_level.update(result.new_entities)

        visited.update(current_level)
        current_level = next_level - visited

    return subgraph
```

#### 第二阶段：并行标签解析

**当前的顺序实现方式：**
```python
# INEFFICIENT: Sequential processing
for edge in subgraph:
    s = await self.maybe_label(edge[0])  # Individual query
    p = await self.maybe_label(edge[1])  # Individual query
    o = await self.maybe_label(edge[2])  # Individual query
```

<<<<<<< HEAD
**优化后的并行实现：**
=======
**优化并行实现：**
>>>>>>> 82edf2d (New md files from RunPod)
```python
async def resolve_labels_parallel(self, subgraph: List[Triple]) -> List[Triple]:
    # Collect all unique entities needing labels
    entities_to_resolve = set()
    for s, p, o in subgraph:
        entities_to_resolve.update([s, p, o])

    # Remove already cached entities
    uncached_entities = [e for e in entities_to_resolve if e not in self.label_cache]

    # Batch query for all uncached labels
    if uncached_entities:
        label_results = await self.batch_label_query(uncached_entities)
        self.label_cache.update(label_results)

    # Apply labels to subgraph
    return [
        (self.label_cache.get(s, s), self.label_cache.get(p, p), self.label_cache.get(o, o))
        for s, p, o in subgraph
    ]
```

#### 第三阶段：高级缓存策略

**LRU 缓存与 TTL：**
```python
class LRUCacheWithTTL:
    def __init__(self, max_size: int, default_ttl: int = 3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Check TTL expiration
            if time.time() - self.access_times[key] > self.default_ttl:
                del self.cache[key]
                del self.access_times[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    async def put(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.access_times[oldest_key]

        self.cache[key] = value
        self.access_times[key] = time.time()
```

#### 第四阶段：查询优化和监控

**性能指标收集：**
```python
@dataclass
class PerformanceMetrics:
    total_queries: int
    cache_hits: int
    cache_misses: int
    avg_response_time: float
    subgraph_construction_time: float
    label_resolution_time: float
    total_entities_processed: int
    memory_usage_mb: float
```

**查询超时和断路器：**
```python
async def execute_with_timeout(self, query_func, timeout: int = 30):
    try:
        return await asyncio.wait_for(query_func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Query timeout after {timeout}s")
        raise GraphRagTimeoutError(f"Query exceeded timeout of {timeout}s")
```

## 缓存一致性考虑

**数据时效性权衡：**
**标签缓存 (5 分钟 TTL)**：存在提供已删除/重命名的实体标签的风险。
**不缓存嵌入 (embeddings)**：不需要 - 嵌入已按查询缓存。
**不缓存结果**：防止从已删除的实体/关系中获取过时的子图结果。

**缓解策略：**
**保守的 TTL 值**：在性能提升 (10-20%) 和数据新鲜度之间取得平衡。
**缓存失效钩子**：可选地与图的修改事件集成。
<<<<<<< HEAD
**监控仪表板**：跟踪缓存命中率与数据时效性事件。
**可配置的缓存策略**：允许根据修改频率进行按部署的调整。

**根据图修改速率推荐的缓存配置：**
=======
**监控仪表板**：跟踪缓存命中率与数据陈旧事件。
**可配置的缓存策略**：允许根据修改频率进行按部署的调整。

**基于图修改速率的推荐缓存配置：**
>>>>>>> 82edf2d (New md files from RunPod)
**高修改速率 (>100 次/小时)**：TTL=60 秒，较小的缓存大小。
**中等修改速率 (10-100 次/小时)**：TTL=300 秒 (默认值)。
**低修改速率 (<10 次/小时)**：TTL=600 秒，较大的缓存大小。

## 安全性考虑

**查询注入防护：**
验证所有实体标识符和查询参数。
对所有数据库交互使用参数化查询。
实施查询复杂度限制以防止拒绝服务 (DoS) 攻击。

**资源保护：**
强制执行最大子图大小限制。
实施查询超时以防止资源耗尽。
添加内存使用情况监控和限制。

**访问控制：**
维护现有的用户和集合隔离。
添加对影响性能的操作的审计日志。
实施速率限制以防止对昂贵操作的滥用。

## 性能考虑

### 预期的性能提升

**查询减少：**
<<<<<<< HEAD
当前：典型请求需要 ~9,000+ 次查询。
优化后：~50-100 个批处理查询 (减少 98%)。
=======
当前：典型请求约 9,000+ 个查询。
优化后：约 50-100 个批处理查询 (减少 98%)。
>>>>>>> 82edf2d (New md files from RunPod)

**响应时间改进：**
图遍历：15-20 秒 → 3-5 秒 (快 4-5 倍)。
标签解析：8-12 秒 → 2-4 秒 (快 3 倍)。
总体查询：25-35 秒 → 6-10 秒 (提升 3-4 倍)。

**内存效率：**
限制的缓存大小可防止内存泄漏。
<<<<<<< HEAD
高效的数据结构可减少内存占用 ~40%。
=======
高效的数据结构可将内存占用减少约 40%。
>>>>>>> 82edf2d (New md files from RunPod)
通过适当的资源清理实现更好的垃圾回收。

**现实的性能期望：**
**标签缓存**：对于具有常见关系的图，查询减少 10-20%。
**批处理优化**：查询减少 50-80% (主要优化)。
**对象生命周期优化**：消除每个请求的创建开销。
**总体改进**：主要通过批处理实现响应时间提升 3-4 倍。

**可扩展性改进：**
支持 3-5 倍更大的知识图 (受缓存一致性需求限制)。
3-5 倍更高的并发请求容量。
通过连接重用实现更好的资源利用率。

### 性能监控

**实时指标：**
按操作类型划分的查询执行时间。
缓存命中率和有效性。
数据库连接池利用率。
内存使用情况和垃圾回收影响。

<<<<<<< HEAD
**性能基准测试 (Xìngnéng Jīzhǔ Cèshì):**
自动化性能回归测试 (Zìdònghuà xìngnéng huíguī cèshì)
使用真实数据量的负载测试 (Shǐyòng zhēnshí shùjùliàng de fùzài cèshì)
与当前实现相比的基准测试 (Yǔ xiàncái shíxiàn xiāngbǐ de jīzhǔ cèshì)
=======
**性能基准测试:**
自动化性能回归测试
使用真实数据量的负载测试
与当前实现相比的基准测试
>>>>>>> 82edf2d (New md files from RunPod)

## 测试策略 (Cèshì Cèlüè)

<<<<<<< HEAD
### 单元测试 (Dānyuán Cèshì)
对遍历、缓存和标签解析等各个组件进行单独测试 (Duì biànlì, cáichǔ hé biāoqiān jiěshì děng gège zǔjiàn jìnxíng dānduǒ cèshì)
模拟数据库交互以进行性能测试 (Mónǐ shùjùkù jiāohù yǐ jìnxíng xìngnéng cèshì)
缓存驱逐和 TTL 过期测试 (Cáichǔ qūzhí hé TTL guòqí cèshì)
错误处理和超时场景测试 (Cuòwù chǔlǐ hé chāoshí chǎngjǐng cèshì)

### 集成测试 (Jíchéng Cèshì)
使用优化后的 GraphRAG 查询的端到端测试 (Shǐyòng yōuhuà hòu de GraphRAG shōuchá de duān dào duān cèshì)
使用真实数据的数据库交互测试 (Shǐyòng zhēnshí shùjù de shùjùkù jiāohù cèshì)
并发请求处理和资源管理测试 (Bìngfā qǐngqiú chǔlǐ hé zīyuán guǎnlǐ cèshì)
内存泄漏检测和资源清理验证 (Nèicún liūlèi jiǎncè hé zīyuán qīnglǐ yànzhèng)

### 性能测试 (Xìngnéng Cèshì)
与当前实现相比的基准测试 (Yǔ xiàncái shíxiàn xiāngbǐ de jīzhǔ cèshì)
使用不同大小和复杂度的图的负载测试 (Shǐyòng bùtóng dàxiǎo hé fùzá dù de tú de fùzài cèshì)
压力测试以确定内存和连接限制 (Yālì cèshì yǐ quèdìng nèicún hé liánjiē xiànzhì)
用于性能改进的回归测试 (Yòng yú xìngnéng gǎijìn de huíguī cèshì)

### 兼容性测试 (Jiānróng Xìng Cèshì)
验证现有 GraphRAG API 的兼容性 (Yànzhèng xiàn yǒu GraphRAG API de jiānróng xìng)
使用各种图数据库后端进行测试 (Shǐyòng gè zhǒng tú shùjùkù hòudùàn jìnxíng cèshì)
验证与当前实现相比的结果准确性 (Yànzhèng yǔ xiàncái shíxiàn xiāngbǐ de jiéguǒ zhǔnquè xìng)
=======
### 单元测试
对遍历、缓存和标签解析的各个组件进行测试
模拟数据库交互以进行性能测试
缓存驱逐和 TTL 过期测试
错误处理和超时场景

### 集成测试
使用优化后的 GraphRAG 查询进行端到端测试
使用真实数据进行数据库交互测试
并发请求处理和资源管理
内存泄漏检测和资源清理验证

### 性能测试
与当前实现相比的基准测试
使用不同大小和复杂度的图进行负载测试
压力测试以检查内存和连接限制
针对性能改进进行的回归测试

### 兼容性测试
验证现有 GraphRAG API 的兼容性
使用各种图数据库后端进行测试
验证与当前实现相比的结果准确性
>>>>>>> 82edf2d (New md files from RunPod)

## 实施计划 (Shíshī Jìhuà)

<<<<<<< HEAD
### 直接实施方法 (Zhíjiē Shíshī Fāngfǎ)
由于允许 API 更改，因此在不引入迁移复杂性的情况下，直接实施优化：(Yóuyú yǔnxǔ API gēnggǎi, yīncǐ zài bù yǐnrù qiān yí fùzá xìng de qíngkuàng xià, zhíjiē shíshī yōuhuà:)

1. **替换 `follow_edges` 方法**: 使用迭代批量遍历重写 (Tiānyuē `follow_edges` fāngfǎ: Shǐyòng diànxìng pīliàng biànlì chóngxīn xiě)
2. **优化 `get_labelgraph`**: 实施并行标签解析 (Yōuhuà `get_labelgraph`: Shíshī bìngxíng biāoqiān jiěshì)
3. **添加长期 GraphRag**: 修改处理器以维护持久实例 (Tiānjiā chángqí GraphRag: Gǎixiāng chǔlǐ qì yǐ wéihù chíjiǔ yǐnshì)
4. **实施标签缓存**: 为 GraphRag 类添加 LRU 缓存和 TTL (Shíshī biāoqiān cáichǔ: Wèi GraphRag lèi tiānjiā LRU cáichǔ hé TTL)

### 变更范围 (Biàngēng Fànwéi)
**查询类 (Query Class)**: 替换 `follow_edges` 中的 ~50 行代码，添加 ~30 行批量处理代码 (Tiānyuē `follow_edges` zhōng de ~50 háng dàimǎ, tiānjiā ~30 háng pīliàng chǔlǐ dàimǎ)
**GraphRag 类 (GraphRag Class)**: 添加缓存层 (~40 行代码) (Tiānjiā cáichǔ céng (~40 háng dàimǎ))
**处理器类 (Processor Class)**: 修改为使用持久的 GraphRag 实例 (~20 行代码) (Gǎixiāng wéi shǐyòng chíjiǔ de GraphRag yǐnshì (~20 háng dàimǎ))
**总计 (Zǒngjì)**: ~140 行专注于的变更，主要在现有类中 (~140 háng zhuānzhù yú de biàngēng, zhǔyào zài xiàn yǒu lèi zhōng)
=======
### 直接实施方法
由于允许 API 更改，因此无需迁移复杂性，可以直接实现优化：

1. **替换 `follow_edges` 方法**: 使用迭代批量遍历重写
2. **优化 `get_labelgraph`**: 实现并行标签解析
3. **添加长期 GraphRag**: 修改 Processor 以维护持久实例
4. **实现标签缓存**: 为 GraphRag 类添加 LRU 缓存和 TTL

### 变更范围
**查询类**: 替换 `follow_edges` 中的约 50 行代码，添加约 30 行批量处理代码
**GraphRag 类**: 添加缓存层（约 40 行代码）
**Processor 类**: 修改为使用持久的 GraphRag 实例（约 20 行代码）
**总计**: 约 140 行代码的集中性变更，主要在现有类中
>>>>>>> 82edf2d (New md files from RunPod)

## 时间线 (Shíjiān Xiàn)

<<<<<<< HEAD
**第一周: 核心实施 (Dì Yī Zhōu: Héxīn Shíshī)**
使用批量迭代遍历替换 `follow_edges` (Shǐyòng pīliàng diànxìng biànlì tiānyuē `follow_edges`)
在 `get_labelgraph` 中实施并行标签解析 (Zài `get_labelgraph` zhōng shíshī bìngxíng biāoqiān jiěshì)
向处理器添加长期 GraphRag 实例 (Xiàng chǔlǐ qì tiānjiā chángqí GraphRag yǐnshì)
实施标签缓存层 (Shíshī biāoqiān cáichǔ céng)

**第二周: 测试和集成 (Dì Èr Zhōu: Cèshì hé Jíchéng)**
对新的遍历和缓存逻辑进行单元测试 (Duì xīn de biànlì hé cáichǔ luójí jìnxíng dānyuán cèshì)
与当前实现相比进行性能基准测试 (Yǔ xiàncái shíxiàn xiāngbǐ jìnxíng xìngnéng jīzhǔ cèshì)
使用真实图数据进行集成测试 (Shǐyòng zhēnshí tú shùjù jìnxíng jíchéng cèshì)
代码审查和优化 (Dàimǎ shěnchá hé yōuhuà)

**第三周: 部署 (Dì Sān Zhōu: Bùshǔ)**
部署优化后的实现 (Bùshǔ yōuhuà hòu de shíshī)
监控性能改进 (Jiānkòng xìngnéng gǎijìn)
根据实际使用情况微调缓存 TTL 和批量大小 (Gēnjù shíjì shǐyòng qíngkuàng wēitiáo cáichǔ TTL hé pīliàng dàxiǎo)
=======
**第一周：核心实施**
使用批量迭代遍历替换 `follow_edges`
在 `get_labelgraph` 中实现并行标签解析
在 Processor 中添加长期 GraphRag 实例
实现标签缓存层

**第二周：测试和集成**
对新的遍历和缓存逻辑进行单元测试
与当前实现相比的性能基准测试
使用真实图数据的集成测试
代码审查和优化

**第三周：部署**
部署优化的实现
监控性能改进
根据实际使用情况微调缓存 TTL 和批次大小
>>>>>>> 82edf2d (New md files from RunPod)

## 开放性问题 (Kāifàng Xìng Wèntí)

<<<<<<< HEAD
**数据库连接池 (Shùjùkù Liánjiē Chí)**: 我们应该实施自定义连接池，还是依赖于现有的数据库客户端连接池？(Wǒmen yīnggāi shíshī zìdìngyì liánjiē chí, háishì yīlài yú xiàn yǒu de shùjùkù kèfāngliánjiē chí?)
**缓存持久性 (Cáichǔ Chíjiǔ Xìng)**: 标签和嵌入式缓存是否应该在服务重启后持久存在？(Biāoqiān hé qiànrùshì cáichǔ shìfǒu yīnggāi zài fúwù chóngqí hòu chíjiǔ cúnzài?)
**分布式缓存 (Fēn Bùshì Cáichǔ)**: 对于多实例部署，我们是否应该实施具有 Redis/Memcached 的分布式缓存？(Duìyú duō yǐnshì bùshǔ, wǒmen shìfǒu yīnggāi shíshī yǒuyú Redis/Memcached de fēn bùshì cáichǔ?)
**查询结果格式 (Shōuchá Jiéguǒ Géshì)**: 我们是否应该优化内部三元组表示以获得更好的内存效率？(Wǒmen shìfǒu yīnggāi yōuhuà nèibù sān yuánzǔ biǎoshì yǐ huòdé gèng hǎo de nèicún xiàolǜ?)
**监控集成 (Jiānkòng Jíchéng)**: 哪些指标应该暴露给现有的监控系统（Prometheus 等）？(Nǎxiē zhǐbiāo yīnggāi bàolù gěi xiàn yǒu de jiānkòng xìtǒng (Prometheus děng)?)

## 参考文献 (Cānkǎo Z tàiliào)

GraphRAG API 文档 (GraphRAG API 文档)
示例代码 (Lìmiàn dàimǎ)
相关论文 (Xiāngguān lùnwén)
=======
**数据库连接池**: 我们应该实现自定义连接池，还是依赖于现有的数据库客户端池？
**缓存持久性**: 标签和嵌入式缓存是否应该在服务重启后持久存在？
**分布式缓存**: 对于多实例部署，我们是否应该实现使用 Redis/Memcached 的分布式缓存？
**查询结果格式**: 我们是否应该优化内部三元组表示以获得更好的内存效率？
**监控集成**: 哪些指标应该暴露给现有的监控系统（Prometheus 等）？

## 参考文献

[GraphRAG 原始实现](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
[TrustGraph 架构原则](architecture-principles.md)
[集合管理规范](collection-management.md)
>>>>>>> 82edf2d (New md files from RunPod)
