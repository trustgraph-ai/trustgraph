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

## Proposed Solution: Multi-Table Denormalization Strategy

### Overview

Replace the single `triples` table with three purpose-built tables, each optimized for specific query patterns. This eliminates the need for secondary indexes and ALLOW FILTERING while providing optimal performance for all query types.

### New Schema Design

**Table 1: Subject-Centric Queries**
```sql
CREATE TABLE triples_by_subject (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
- **Optimizes:** get_s, get_sp, get_spo, get_os
- **Partition Key:** (collection, s) - Better distribution than collection alone
- **Clustering:** (p, o) - Enables efficient predicate/object lookups for a subject

**Table 2: Predicate-Object Queries**
```sql
CREATE TABLE triples_by_po (
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

**Table 3: Object-Centric Queries**
```sql
CREATE TABLE triples_by_object (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
- **Optimizes:** get_o, get_os
- **Partition Key:** (collection, o) - Direct access by object
- **Clustering:** (s, p) - Efficient subject-predicate traversal

### Query Mapping

| Original Query | Target Table | Performance Improvement |
|----------------|-------------|------------------------|
| get_all(collection) | triples_by_subject | Token-based pagination |
| get_s(collection, s) | triples_by_subject | Direct partition access |
| get_p(collection, p) | triples_by_po | Direct partition access |
| get_o(collection, o) | triples_by_object | Direct partition access |
| get_sp(collection, s, p) | triples_by_subject | Partition + clustering |
| get_po(collection, p, o) | triples_by_po | **No more ALLOW FILTERING!** |
| get_os(collection, o, s) | triples_by_subject | Partition + clustering |
| get_spo(collection, s, p, o) | triples_by_subject | Exact key lookup |

### Benefits

1. **Eliminates ALLOW FILTERING** - Every query has an optimal access path
2. **No Secondary Indexes** - Each table IS the index for its query pattern
3. **Better Data Distribution** - Composite partition keys spread load effectively
4. **Predictable Performance** - Query time proportional to result size, not total data
5. **Leverages Cassandra Strengths** - Designed for Cassandra's architecture

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
1. **Rewrite `init()` method** - Create three tables instead of one
2. **Rewrite `insert()` method** - Batch writes to all three tables
3. **Implement prepared statements** - For optimal performance
4. **Add table routing logic** - Direct queries to optimal tables

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

    # Insert into all three tables
    batch.add(SimpleStatement(
        "INSERT INTO triples_by_subject (collection, s, p, o) VALUES (?, ?, ?, ?)"
    ), (collection, s, p, o))

    batch.add(SimpleStatement(
        "INSERT INTO triples_by_po (collection, p, o, s) VALUES (?, ?, ?, ?)"
    ), (collection, p, o, s))

    batch.add(SimpleStatement(
        "INSERT INTO triples_by_object (collection, o, s, p) VALUES (?, ?, ?, ?)"
    ), (collection, o, s, p))

    self.session.execute(batch)
```

#### Query Routing Logic
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_by_po table - NO ALLOW FILTERING!
    return self.session.execute(
        "SELECT s FROM triples_by_po WHERE collection = ? AND p = ? AND o = ? LIMIT ?",
        (collection, p, o, limit)
    )
```

#### Prepared Statement Optimization
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        "INSERT INTO triples_by_subject (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        "INSERT INTO triples_by_po (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    # ... etc for all tables and queries
```

## Testing Strategy

[To be defined based on solution approach]

## Risks and Considerations

[To be assessed based on proposed changes]