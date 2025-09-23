# GraphRAG Performance Optimisation Technical Specification

## Overview

This specification describes comprehensive performance optimisations for the GraphRAG (Graph Retrieval-Augmented Generation) algorithm in TrustGraph. The current implementation suffers from significant performance bottlenecks that limit scalability and response times. This specification addresses four primary optimisation areas:

1. **Graph Traversal Optimisation**: Eliminate inefficient recursive database queries and implement batched graph exploration
2. **Label Resolution Optimisation**: Replace sequential label fetching with parallel/batched operations
3. **Caching Strategy Enhancement**: Implement intelligent caching with LRU eviction and prefetching
4. **Query Optimisation**: Add result memoisation and embedding caching for improved response times

## Goals

- **Reduce Database Query Volume**: Achieve 50-80% reduction in total database queries through batching and caching
- **Improve Response Times**: Target 3-5x faster subgraph construction and 2-3x faster label resolution
- **Enhance Scalability**: Support larger knowledge graphs with better memory management
- **Maintain Accuracy**: Preserve existing GraphRAG functionality and result quality
- **Enable Concurrency**: Improve parallel processing capabilities for multiple concurrent requests
- **Reduce Memory Footprint**: Implement efficient data structures and memory management
- **Add Observability**: Include performance metrics and monitoring capabilities
- **Ensure Reliability**: Add proper error handling and timeout mechanisms

## Background

The current GraphRAG implementation in `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` exhibits several critical performance issues that severely impact system scalability:

### Current Performance Problems

**1. Inefficient Graph Traversal (`follow_edges` function, lines 79-127)**
- Makes 3 separate database queries per entity per depth level
- Query pattern: subject-based, predicate-based, and object-based queries for each entity
- No batching: Each query processes only one entity at a time
- No cycle detection: Can revisit the same nodes multiple times
- Recursive implementation without memoisation leads to exponential complexity
- Time complexity: O(entities × max_path_length × triple_limit³)

**2. Sequential Label Resolution (`get_labelgraph` function, lines 144-171)**
- Processes each triple component (subject, predicate, object) sequentially
- Each `maybe_label` call potentially triggers a database query
- No parallel execution or batching of label queries
- Results in up to 3 × subgraph_size individual database calls

**3. Primitive Caching Strategy (`maybe_label` function, lines 62-77)**
- Simple dictionary cache without size limits or TTL
- No cache eviction policy leads to unbounded memory growth
- Cache misses trigger individual database queries
- No prefetching or intelligent cache warming

**4. Suboptimal Query Patterns**
- Entity vector similarity queries not cached between similar requests
- No result memoisation for repeated query patterns
- Missing query optimisation for common access patterns

**5. Critical Object Lifetime Issues (`rag.py:96-102`)**
- **GraphRag object recreated per request**: Fresh instance created for every query, losing all cache benefits
- **Query object extremely short-lived**: Created and destroyed within single query execution (lines 201-207)
- **Label cache reset per request**: Cache warming and accumulated knowledge lost between requests
- **Client recreation overhead**: Database clients potentially re-established for each request
- **No cross-request optimisation**: Cannot benefit from query patterns or result sharing

### Performance Impact Analysis

Current worst-case scenario for a typical query:
- **Entity Retrieval**: 1 vector similarity query
- **Graph Traversal**: entities × max_path_length × 3 × triple_limit queries
- **Label Resolution**: subgraph_size × 3 individual label queries

For default parameters (50 entities, path length 2, 30 triple limit, 150 subgraph size):
- **Minimum queries**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9,451 database queries**
- **Response time**: 15-30 seconds for moderate-sized graphs
- **Memory usage**: Unbounded cache growth over time
- **Cache effectiveness**: 0% - caches reset on every request
- **Object creation overhead**: GraphRag + Query objects created/destroyed per request

This specification addresses these gaps by implementing batched queries, intelligent caching, and parallel processing. By optimizing query patterns and data access, TrustGraph can:
- Support enterprise-scale knowledge graphs with millions of entities
- Provide sub-second response times for typical queries
- Handle hundreds of concurrent GraphRAG requests
- Scale efficiently with graph size and complexity

## Technical Design

### Architecture

The GraphRAG performance optimisation requires the following technical components:

#### 1. **Object Lifetime Architectural Refactor**
   - **Make GraphRag long-lived**: Move GraphRag instance to Processor level for persistence across requests
   - **Preserve caches**: Maintain label cache, embedding cache, and query result cache between requests
   - **Optimize Query object**: Refactor Query as lightweight execution context, not data container
   - **Connection persistence**: Maintain database client connections across requests

   Module: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (modified)

#### 2. **Optimized Graph Traversal Engine**
   - Replace recursive `follow_edges` with iterative breadth-first search
   - Implement batched entity processing at each traversal level
   - Add cycle detection using visited node tracking
   - Include early termination when limits are reached

   Module: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **Parallel Label Resolution System**
   - Batch label queries for multiple entities simultaneously
   - Implement async/await patterns for concurrent database access
   - Add intelligent prefetching for common label patterns
   - Include label cache warming strategies

   Module: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **Conservative Label Caching Layer**
   - LRU cache with short TTL for labels only (5min) to balance performance vs consistency
   - Cache metrics and hit ratio monitoring
   - **No embedding caching**: Already cached per-query, no cross-query benefit
   - **No query result caching**: Due to graph mutation consistency concerns

   Module: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **Query Optimisation Framework**
   - Query pattern analysis and optimisation suggestions
   - Batch query coordinator for database access
   - Connection pooling and query timeout management
   - Performance monitoring and metrics collection

   Module: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### Data Models

#### Optimized Graph Traversal State

The traversal engine maintains state to avoid redundant operations:

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

This approach allows:
- Efficient cycle detection through visited entity tracking
- Batched query preparation at each traversal level
- Memory-efficient state management
- Early termination when size limits are reached

#### Enhanced Cache Structure

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

#### Batch Query Structures

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

### APIs

#### New APIs:

**GraphTraversal API**
```python
async def optimized_follow_edges_batch(
    entities: List[str],
    max_depth: int,
    triple_limit: int,
    max_subgraph_size: int
) -> Set[Tuple[str, str, str]]
```

**Batch Label Resolution API**
```python
async def resolve_labels_batch(
    entities: List[str],
    cache_manager: CacheManager
) -> Dict[str, str]
```

**Cache Management API**
```python
class CacheManager:
    async def get_or_fetch_label(self, entity: str) -> str
    async def get_or_fetch_embeddings(self, query: str) -> List[float]
    async def cache_query_result(self, query_hash: str, result: Any, ttl: int)
    def get_cache_statistics(self) -> CacheStatistics
```

#### Modified APIs:

**GraphRag.query()** - Enhanced with performance optimisations:
- Add cache_manager parameter for cache control
- Include performance_metrics return value
- Add query_timeout parameter for reliability

**Query class** - Refactored for batch processing:
- Replace individual entity processing with batch operations
- Add async context managers for resource cleanup
- Include progress callbacks for long-running operations

### Implementation Details

#### Phase 0: Critical Architectural Lifetime Refactor

**Current Problematic Implementation:**
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

**Optimized Long-Lived Architecture:**
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

This architectural change provides:
- **10-20% database query reduction** for graphs with common relationships (vs 0% currently)
- **Eliminated object creation overhead** for every request
- **Persistent connection pooling** and client reuse
- **Cross-request optimization** within cache TTL windows

**Important Cache Consistency Limitation:**
Long-term caching introduces staleness risk when entities/labels are deleted or modified in the underlying graph. The LRU cache with TTL provides a balance between performance gains and data freshness, but cannot detect real-time graph changes.

#### Phase 1: Graph Traversal Optimisation

**Current Implementation Problems:**
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

**Optimized Implementation:**
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

#### Phase 2: Parallel Label Resolution

**Current Sequential Implementation:**
```python
# INEFFICIENT: Sequential processing
for edge in subgraph:
    s = await self.maybe_label(edge[0])  # Individual query
    p = await self.maybe_label(edge[1])  # Individual query
    o = await self.maybe_label(edge[2])  # Individual query
```

**Optimized Parallel Implementation:**
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

#### Phase 3: Advanced Caching Strategy

**LRU Cache with TTL:**
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

#### Phase 4: Query Optimisation and Monitoring

**Performance Metrics Collection:**
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

**Query Timeout and Circuit Breaker:**
```python
async def execute_with_timeout(self, query_func, timeout: int = 30):
    try:
        return await asyncio.wait_for(query_func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Query timeout after {timeout}s")
        raise GraphRagTimeoutError(f"Query exceeded timeout of {timeout}s")
```

## Cache Consistency Considerations

**Data Staleness Trade-offs:**
- **Label cache (5min TTL)**: Risk of serving deleted/renamed entity labels
- **No embedding caching**: Not needed - embeddings already cached per-query
- **No result caching**: Prevents stale subgraph results from deleted entities/relationships

**Mitigation Strategies:**
- **Conservative TTL values**: Balance performance gains (10-20%) with data freshness
- **Cache invalidation hooks**: Optional integration with graph mutation events
- **Monitoring dashboards**: Track cache hit rates vs staleness incidents
- **Configurable cache policies**: Allow per-deployment tuning based on mutation frequency

**Recommended Cache Configuration by Graph Mutation Rate:**
- **High mutation (>100 changes/hour)**: TTL=60s, smaller cache sizes
- **Medium mutation (10-100 changes/hour)**: TTL=300s (default)
- **Low mutation (<10 changes/hour)**: TTL=600s, larger cache sizes

## Security Considerations

**Query Injection Prevention:**
- Validate all entity identifiers and query parameters
- Use parameterized queries for all database interactions
- Implement query complexity limits to prevent DoS attacks

**Resource Protection:**
- Enforce maximum subgraph size limits
- Implement query timeouts to prevent resource exhaustion
- Add memory usage monitoring and limits

**Access Control:**
- Maintain existing user and collection isolation
- Add audit logging for performance-impacting operations
- Implement rate limiting for expensive operations

## Performance Considerations

### Expected Performance Improvements

**Query Reduction:**
- Current: ~9,000+ queries for typical request
- Optimized: ~50-100 batched queries (98% reduction)

**Response Time Improvements:**
- Graph traversal: 15-20s → 3-5s (4-5x faster)
- Label resolution: 8-12s → 2-4s (3x faster)
- Overall query: 25-35s → 6-10s (3-4x improvement)

**Memory Efficiency:**
- Bounded cache sizes prevent memory leaks
- Efficient data structures reduce memory footprint by ~40%
- Better garbage collection through proper resource cleanup

**Realistic Performance Expectations:**
- **Label cache**: 10-20% query reduction for graphs with common relationships
- **Batching optimization**: 50-80% query reduction (primary optimization)
- **Object lifetime optimization**: Eliminate per-request creation overhead
- **Overall improvement**: 3-4x response time improvement primarily from batching

**Scalability Improvements:**
- Support for 3-5x larger knowledge graphs (limited by cache consistency needs)
- 3-5x higher concurrent request capacity
- Better resource utilization through connection reuse

### Performance Monitoring

**Real-time Metrics:**
- Query execution times by operation type
- Cache hit ratios and effectiveness
- Database connection pool utilisation
- Memory usage and garbage collection impact

**Performance Benchmarking:**
- Automated performance regression testing
- Load testing with realistic data volumes
- Comparison benchmarks against current implementation

## Testing Strategy

### Unit Testing
- Individual component testing for traversal, caching, and label resolution
- Mock database interactions for performance testing
- Cache eviction and TTL expiration testing
- Error handling and timeout scenarios

### Integration Testing
- End-to-end GraphRAG query testing with optimisations
- Database interaction testing with real data
- Concurrent request handling and resource management
- Memory leak detection and resource cleanup verification

### Performance Testing
- Benchmark testing against current implementation
- Load testing with varying graph sizes and complexities
- Stress testing for memory and connection limits
- Regression testing for performance improvements

### Compatibility Testing
- Verify existing GraphRAG API compatibility
- Test with various graph database backends
- Validate result accuracy compared to current implementation

## Implementation Plan

### Direct Implementation Approach
Since APIs are allowed to change, implement optimizations directly without migration complexity:

1. **Replace `follow_edges` method**: Rewrite with iterative batched traversal
2. **Optimize `get_labelgraph`**: Implement parallel label resolution
3. **Add long-lived GraphRag**: Modify Processor to maintain persistent instance
4. **Implement label caching**: Add LRU cache with TTL to GraphRag class

### Scope of Changes
- **Query class**: Replace ~50 lines in `follow_edges`, add ~30 lines batch handling
- **GraphRag class**: Add caching layer (~40 lines)
- **Processor class**: Modify to use persistent GraphRag instance (~20 lines)
- **Total**: ~140 lines of focused changes, mostly within existing classes

## Timeline

**Week 1: Core Implementation**
- Replace `follow_edges` with batched iterative traversal
- Implement parallel label resolution in `get_labelgraph`
- Add long-lived GraphRag instance to Processor
- Implement label caching layer

**Week 2: Testing and Integration**
- Unit tests for new traversal and caching logic
- Performance benchmarking against current implementation
- Integration testing with real graph data
- Code review and optimization

**Week 3: Deployment**
- Deploy optimized implementation
- Monitor performance improvements
- Fine-tune cache TTL and batch sizes based on real usage

## Open Questions

- **Database Connection Pooling**: Should we implement custom connection pooling or rely on existing database client pooling?
- **Cache Persistence**: Should label and embedding caches persist across service restarts?
- **Distributed Caching**: For multi-instance deployments, should we implement distributed caching with Redis/Memcached?
- **Query Result Format**: Should we optimize the internal triple representation for better memory efficiency?
- **Monitoring Integration**: Which metrics should be exposed to existing monitoring systems (Prometheus, etc.)?

## References

- [GraphRAG Original Implementation](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
- [TrustGraph Architecture Principles](architecture-principles.md)
- [Collection Management Specification](collection-management.md)
