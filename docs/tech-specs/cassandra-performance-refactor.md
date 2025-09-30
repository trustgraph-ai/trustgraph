# Tech Spec: Cassandra Knowledge Base Performance Refactor

**Status:** Draft
**Author:** Assistant
**Date:** 2025-09-18

## Overview

This specification addresses performance issues in the TrustGraph Cassandra knowledge base implementation and proposes optimizations for RDF triple storage and querying.

## Current Implementation

### Schema Design

The current implementation uses a single table design in `trustgraph-flow/trustgraph/direct/cassandra_kg.py`:

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**Secondary Indexes:**
- `triples_s` ON `s` (subject)
- `triples_p` ON `p` (predicate)
- `triples_o` ON `o` (object)

### Query Patterns

The current implementation supports 8 distinct query patterns:

1. **get_all(collection, limit=50)** - Retrieve all triples for a collection
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(collection, s, limit=10)** - Query by subject
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(collection, p, limit=10)** - Query by predicate
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(collection, o, limit=10)** - Query by object
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(collection, s, p, limit=10)** - Query by subject + predicate
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - Query by predicate + object ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(collection, o, s, limit=10)** - Query by object + subject ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(collection, s, p, o, limit=10)** - Exact triple match
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### Current Architecture

**File: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
- Single `KnowledgeGraph` class handling all operations
- Connection pooling through global `_active_clusters` list
- Fixed table name: `"triples"`
- Keyspace per user model
- SimpleStrategy replication with factor 1

**Integration Points:**
- **Write Path:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
- **Query Path:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`
- **Knowledge Store:** `trustgraph-flow/trustgraph/tables/knowledge.py`

## Performance Issues Identified

### Schema-Level Issues

1. **Inefficient Primary Key Design**
   - Current: `PRIMARY KEY (collection, s, p, o)`
   - Results in poor clustering for common access patterns
   - Forces expensive secondary index usage

2. **Secondary Index Overuse** ⚠️
   - Three secondary indexes on high-cardinality columns (s, p, o)
   - Secondary indexes in Cassandra are expensive and don't scale well
   - Queries 6 & 7 require `ALLOW FILTERING` indicating poor data modeling

3. **Hot Partition Risk**
   - Single partition key `collection` can create hot partitions
   - Large collections will concentrate on single nodes
   - No distribution strategy for load balancing

### Query-Level Issues

1. **ALLOW FILTERING Usage** ⚠️
   - Two query types (get_po, get_os) require `ALLOW FILTERING`
   - These queries scan multiple partitions and are extremely expensive
   - Performance degrades linearly with data size

2. **Inefficient Access Patterns**
   - No optimization for common RDF query patterns
   - Missing compound indexes for frequent query combinations
   - No consideration for graph traversal patterns

3. **Lack of Query Optimization**
   - No prepared statements caching
   - No query hints or optimization strategies
   - No consideration for pagination beyond simple LIMIT

## Problem Statement

The current Cassandra knowledge base implementation has two critical performance bottlenecks:

### 1. Inefficient get_po Query Performance

The `get_po(collection, p, o)` query is extremely inefficient due to requiring `ALLOW FILTERING`:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**Why this is problematic:**
- `ALLOW FILTERING` forces Cassandra to scan all partitions within the collection
- Performance degrades linearly with data size
- This is a common RDF query pattern (finding subjects that have a specific predicate-object relationship)
- Creates significant load on the cluster as data grows

### 2. Poor Clustering Strategy

The current primary key `PRIMARY KEY (collection, s, p, o)` provides minimal clustering benefits:

**Issues with current clustering:**
- `collection` as partition key doesn't distribute data effectively
- Most collections contain diverse data making clustering ineffective
- No consideration for common access patterns in RDF queries
- Large collections create hot partitions on single nodes
- Clustering columns (s, p, o) don't optimize for typical graph traversal patterns

**Impact:**
- Queries don't benefit from data locality
- Poor cache utilization
- Uneven load distribution across cluster nodes
- Scalability bottlenecks as collections grow

## Proposed Solution: 4-Table Denormalization Strategy

### Overview

Replace the single `triples` table with four purpose-built tables, each optimized for specific query patterns. This eliminates the need for secondary indexes and ALLOW FILTERING while providing optimal performance for all query types. The fourth table enables efficient collection deletion despite compound partition keys.

### New Schema Design

**Table 1: Subject-Centric Queries (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
- **Optimizes:** get_s, get_sp, get_os
- **Partition Key:** (collection, s) - Better distribution than collection alone
- **Clustering:** (p, o) - Enables efficient predicate/object lookups for a subject

**Table 2: Predicate-Object Queries (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
- **Optimizes:** get_p, get_po (eliminates ALLOW FILTERING!)
- **Partition Key:** (collection, p) - Direct access by predicate
- **Clustering:** (o, s) - Efficient object-subject traversal

**Table 3: Object-Centric Queries (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
- **Optimizes:** get_o
- **Partition Key:** (collection, o) - Direct access by object
- **Clustering:** (s, p) - Efficient subject-predicate traversal

**Table 4: Collection Management & SPO Queries (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
- **Optimizes:** get_spo, delete_collection
- **Partition Key:** collection only - Enables efficient collection-level operations
- **Clustering:** (s, p, o) - Standard triple ordering
- **Purpose:** Dual use for exact SPO lookups and as deletion index

### Query Mapping

| Original Query | Target Table | Performance Improvement |
|----------------|-------------|------------------------|
| get_all(collection) | triples_s | ALLOW FILTERING (acceptable for scan) |
| get_s(collection, s) | triples_s | Direct partition access |
| get_p(collection, p) | triples_p | Direct partition access |
| get_o(collection, o) | triples_o | Direct partition access |
| get_sp(collection, s, p) | triples_s | Partition + clustering |
| get_po(collection, p, o) | triples_p | **No more ALLOW FILTERING!** |
| get_os(collection, o, s) | triples_o | Partition + clustering |
| get_spo(collection, s, p, o) | triples_collection | Exact key lookup |
| delete_collection(collection) | triples_collection | Read index, batch delete all |

### Collection Deletion Strategy

With compound partition keys, we cannot simply execute `DELETE FROM table WHERE collection = ?`. Instead:

1. **Read Phase:** Query `triples_collection` to enumerate all triples:
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   This is efficient since `collection` is the partition key for this table.

2. **Delete Phase:** For each triple (s, p, o), delete from all 4 tables using full partition keys:
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   Batched in groups of 100 for efficiency.

**Trade-off Analysis:**
- ✅ Maintains optimal query performance with distributed partitions
- ✅ No hot partitions for large collections
- ❌ More complex deletion logic (read-then-delete)
- ❌ Deletion time proportional to collection size

### Benefits

1. **Eliminates ALLOW FILTERING** - Every query has an optimal access path (except get_all scan)
2. **No Secondary Indexes** - Each table IS the index for its query pattern
3. **Better Data Distribution** - Composite partition keys spread load effectively
4. **Predictable Performance** - Query time proportional to result size, not total data
5. **Leverages Cassandra Strengths** - Designed for Cassandra's architecture
6. **Enables Collection Deletion** - triples_collection serves as deletion index

## Implementation Plan

### Files Requiring Changes

#### Primary Implementation File

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - Complete rewrite required

**Current Methods to Refactor:**
```python
# Schema initialization
def init(self) -> None  # Replace single table with three tables

# Insert operations
def insert(self, collection, s, p, o) -> None  # Write to all three tables

# Query operations (API unchanged, implementation optimized)
def get_all(self, collection, limit=50)      # Use triples_by_subject
def get_s(self, collection, s, limit=10)     # Use triples_by_subject
def get_p(self, collection, p, limit=10)     # Use triples_by_po
def get_o(self, collection, o, limit=10)     # Use triples_by_object
def get_sp(self, collection, s, p, limit=10) # Use triples_by_subject
def get_po(self, collection, p, o, limit=10) # Use triples_by_po (NO ALLOW FILTERING!)
def get_os(self, collection, o, s, limit=10) # Use triples_by_subject
def get_spo(self, collection, s, p, o, limit=10) # Use triples_by_subject

# Collection management
def delete_collection(self, collection) -> None  # Delete from all three tables
```

#### Integration Files (No Logic Changes Required)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
- No changes needed - uses existing KnowledgeGraph API
- Benefits automatically from performance improvements

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
- No changes needed - uses existing KnowledgeGraph API
- Benefits automatically from performance improvements

### Test Files Requiring Updates

#### Unit Tests
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
- Update test expectations for schema changes
- Add tests for multi-table consistency
- Verify no ALLOW FILTERING in query plans

**`tests/unit/test_query/test_triples_cassandra_query.py`**
- Update performance assertions
- Test all 8 query patterns against new tables
- Verify query routing to correct tables

#### Integration Tests
**`tests/integration/test_cassandra_integration.py`**
- End-to-end testing with new schema
- Performance benchmarking comparisons
- Data consistency verification across tables

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
- Update schema validation tests
- Test migration scenarios

### Implementation Strategy

#### Phase 1: Schema and Core Methods
1. **Rewrite `init()` method** - Create four tables instead of one
2. **Rewrite `insert()` method** - Batch writes to all four tables
3. **Implement prepared statements** - For optimal performance
4. **Add table routing logic** - Direct queries to optimal tables
5. **Implement collection deletion** - Read from triples_collection, batch delete from all tables

#### Phase 2: Query Method Optimization
1. **Rewrite each get_* method** to use optimal table
2. **Remove all ALLOW FILTERING** usage
3. **Implement efficient clustering key usage**
4. **Add query performance logging**

#### Phase 3: Collection Management
1. **Update `delete_collection()`** - Remove from all three tables
2. **Add consistency verification** - Ensure all tables stay in sync
3. **Implement batch operations** - For atomic multi-table operations

### Key Implementation Details

#### Batch Write Strategy
```python
def insert(self, collection, s, p, o):
    batch = BatchStatement()

    # Insert into all four tables
    batch.add(self.insert_subject_stmt, (collection, s, p, o))
    batch.add(self.insert_po_stmt, (collection, p, o, s))
    batch.add(self.insert_object_stmt, (collection, o, s, p))
    batch.add(self.insert_collection_stmt, (collection, s, p, o))

    self.session.execute(batch)
```

#### Query Routing Logic
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_p table - NO ALLOW FILTERING!
    return self.session.execute(
        self.get_po_stmt,
        (collection, p, o, limit)
    )

def get_spo(self, collection, s, p, o, limit=10):
    # Route to triples_collection table for exact SPO lookup
    return self.session.execute(
        self.get_spo_stmt,
        (collection, s, p, o, limit)
    )
```

#### Collection Deletion Logic
```python
def delete_collection(self, collection):
    # Step 1: Read all triples from collection table
    rows = self.session.execute(
        f"SELECT s, p, o FROM {self.collection_table} WHERE collection = %s",
        (collection,)
    )

    # Step 2: Batch delete from all 4 tables
    batch = BatchStatement()
    count = 0

    for row in rows:
        s, p, o = row.s, row.p, row.o

        # Delete using full partition keys for each table
        batch.add(SimpleStatement(
            f"DELETE FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? AND s = ?"
        ), (collection, p, o, s))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? AND p = ?"
        ), (collection, o, s, p))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.collection_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        count += 1

        # Execute every 100 triples to avoid oversized batches
        if count % 100 == 0:
            self.session.execute(batch)
            batch = BatchStatement()

    # Execute remaining deletions
    if count % 100 != 0:
        self.session.execute(batch)

    logger.info(f"Deleted {count} triples from collection {collection}")
```

#### Prepared Statement Optimization
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    self.insert_object_stmt = self.session.prepare(
        f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
    )
    self.insert_collection_stmt = self.session.prepare(
        f"INSERT INTO {self.collection_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    # ... query statements
```

## Migration Strategy

### Data Migration Approach

#### Option 1: Blue-Green Deployment (Recommended)
1. **Deploy new schema alongside existing** - Use different table names temporarily
2. **Dual-write period** - Write to both old and new schemas during transition
3. **Background migration** - Copy existing data to new tables
4. **Switch reads** - Route queries to new tables once data is migrated
5. **Drop old tables** - After verification period

#### Option 2: In-Place Migration
1. **Schema addition** - Create new tables in existing keyspace
2. **Data migration script** - Batch copy from old table to new tables
3. **Application update** - Deploy new code after migration completes
4. **Old table cleanup** - Remove old table and indexes

### Backward Compatibility

#### Deployment Strategy
```python
# Environment variable to control table usage during migration
USE_LEGACY_TABLES = os.getenv('CASSANDRA_USE_LEGACY', 'false').lower() == 'true'

class KnowledgeGraph:
    def __init__(self, ...):
        if USE_LEGACY_TABLES:
            self.init_legacy_schema()
        else:
            self.init_optimized_schema()
```

#### Migration Script
```python
def migrate_data():
    # Read from old table
    old_triples = session.execute("SELECT collection, s, p, o FROM triples")

    # Batch write to new tables
    for batch in batched(old_triples, 100):
        batch_stmt = BatchStatement()
        for row in batch:
            # Add to all three new tables
            batch_stmt.add(insert_subject_stmt, row)
            batch_stmt.add(insert_po_stmt, (row.collection, row.p, row.o, row.s))
            batch_stmt.add(insert_object_stmt, (row.collection, row.o, row.s, row.p))
        session.execute(batch_stmt)
```

### Validation Strategy

#### Data Consistency Checks
```python
def validate_migration():
    # Count total records in old vs new tables
    old_count = session.execute("SELECT COUNT(*) FROM triples WHERE collection = ?", (collection,))
    new_count = session.execute("SELECT COUNT(*) FROM triples_by_subject WHERE collection = ?", (collection,))

    assert old_count == new_count, f"Record count mismatch: {old_count} vs {new_count}"

    # Spot check random samples
    sample_queries = generate_test_queries()
    for query in sample_queries:
        old_result = execute_legacy_query(query)
        new_result = execute_optimized_query(query)
        assert old_result == new_result, f"Query results differ for {query}"
```

## Testing Strategy

### Performance Testing

#### Benchmark Scenarios
1. **Query Performance Comparison**
   - Before/after performance metrics for all 8 query types
   - Focus on get_po performance improvement (eliminate ALLOW FILTERING)
   - Measure query latency under various data sizes

2. **Load Testing**
   - Concurrent query execution
   - Write throughput with batch operations
   - Memory and CPU utilization

3. **Scalability Testing**
   - Performance with increasing collection sizes
   - Multi-collection query distribution
   - Cluster node utilization

#### Test Data Sets
- **Small:** 10K triples per collection
- **Medium:** 100K triples per collection
- **Large:** 1M+ triples per collection
- **Multiple collections:** Test partition distribution

### Functional Testing

#### Unit Test Updates
```python
# Example test structure for new implementation
class TestCassandraKGPerformance:
    def test_get_po_no_allow_filtering(self):
        # Verify get_po queries don't use ALLOW FILTERING
        with patch('cassandra.cluster.Session.execute') as mock_execute:
            kg.get_po('test_collection', 'predicate', 'object')
            executed_query = mock_execute.call_args[0][0]
            assert 'ALLOW FILTERING' not in executed_query

    def test_multi_table_consistency(self):
        # Verify all tables stay in sync
        kg.insert('test', 's1', 'p1', 'o1')

        # Check all tables contain the triple
        assert_triple_exists('triples_by_subject', 'test', 's1', 'p1', 'o1')
        assert_triple_exists('triples_by_po', 'test', 'p1', 'o1', 's1')
        assert_triple_exists('triples_by_object', 'test', 'o1', 's1', 'p1')
```

#### Integration Test Updates
```python
class TestCassandraIntegration:
    def test_query_performance_regression(self):
        # Ensure new implementation is faster than old
        old_time = benchmark_legacy_get_po()
        new_time = benchmark_optimized_get_po()
        assert new_time < old_time * 0.5  # At least 50% improvement

    def test_end_to_end_workflow(self):
        # Test complete write -> query -> delete cycle
        # Verify no performance degradation in integration
```

### Rollback Plan

#### Quick Rollback Strategy
1. **Environment variable toggle** - Switch back to legacy tables immediately
2. **Keep legacy tables** - Don't drop until performance is proven
3. **Monitoring alerts** - Automated rollback triggers based on error rates/latency

#### Rollback Validation
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## Risks and Considerations

### Performance Risks
- **Write latency increase** - 4x write operations per insert (33% more than 3-table approach)
- **Storage overhead** - 4x storage requirement (33% more than 3-table approach)
- **Batch write failures** - Need proper error handling
- **Deletion complexity** - Collection deletion requires read-then-delete loop

### Operational Risks
- **Migration complexity** - Data migration for large datasets
- **Consistency challenges** - Ensuring all tables stay synchronized
- **Monitoring gaps** - Need new metrics for multi-table operations

### Mitigation Strategies
1. **Gradual rollout** - Start with small collections
2. **Comprehensive monitoring** - Track all performance metrics
3. **Automated validation** - Continuous consistency checking
4. **Quick rollback capability** - Environment-based table selection

## Success Criteria

### Performance Improvements
- [ ] **Eliminate ALLOW FILTERING** - get_po and get_os queries run without filtering
- [ ] **Query latency reduction** - 50%+ improvement in query response times
- [ ] **Better load distribution** - No hot partitions, even load across cluster nodes
- [ ] **Scalable performance** - Query time proportional to result size, not total data

### Functional Requirements
- [ ] **API compatibility** - All existing code continues to work unchanged
- [ ] **Data consistency** - All three tables remain synchronized
- [ ] **Zero data loss** - Migration preserves all existing triples
- [ ] **Backward compatibility** - Ability to rollback to legacy schema

### Operational Requirements
- [ ] **Safe migration** - Blue-green deployment with rollback capability
- [ ] **Monitoring coverage** - Comprehensive metrics for multi-table operations
- [ ] **Test coverage** - All query patterns tested with performance benchmarks
- [ ] **Documentation** - Updated deployment and operational procedures

## Timeline

### Phase 1: Implementation
- [ ] Rewrite `cassandra_kg.py` with multi-table schema
- [ ] Implement batch write operations
- [ ] Add prepared statement optimization
- [ ] Update unit tests

### Phase 2: Integration Testing
- [ ] Update integration tests
- [ ] Performance benchmarking
- [ ] Load testing with realistic data volumes
- [ ] Validation scripts for data consistency

### Phase 3: Migration Planning
- [ ] Blue-green deployment scripts
- [ ] Data migration tools
- [ ] Monitoring dashboard updates
- [ ] Rollback procedures

### Phase 4: Production Deployment
- [ ] Staged rollout to production
- [ ] Performance monitoring and validation
- [ ] Legacy table cleanup
- [ ] Documentation updates

## Conclusion

This multi-table denormalization strategy directly addresses the two critical performance bottlenecks:

1. **Eliminates expensive ALLOW FILTERING** by providing optimal table structures for each query pattern
2. **Improves clustering effectiveness** through composite partition keys that distribute load properly

The approach leverages Cassandra's strengths while maintaining complete API compatibility, ensuring existing code benefits automatically from the performance improvements.
