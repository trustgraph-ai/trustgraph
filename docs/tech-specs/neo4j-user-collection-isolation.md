# Neo4j User/Collection Isolation Support

## Problem Statement

The Neo4j triples storage and query implementation currently lacks user/collection isolation, which creates a multi-tenancy security issue. All triples are stored in the same graph space without any mechanism to prevent users from accessing other users' data or mixing collections.

Unlike other storage backends in TrustGraph:
- **Cassandra**: Uses separate keyspaces per user and tables per collection 
- **Vector stores** (Milvus, Qdrant, Pinecone): Use collection-specific namespaces
- **Neo4j**: Currently shares all data in a single graph (security vulnerability)

## Current Architecture

### Data Model
- **Nodes**: `:Node` label with `uri` property, `:Literal` label with `value` property
- **Relationships**: `:Rel` label with `uri` property
- **Indexes**: `Node.uri`, `Literal.value`, `Rel.uri`

### Message Flow
- `Triples` messages contain `metadata.user` and `metadata.collection` fields
- Storage service receives user/collection info but ignores it
- Query service expects `user` and `collection` in `TriplesQueryRequest` but ignores them

### Current Security Issue
```cypher
# Any user can query any data - no isolation
MATCH (src:Node)-[rel:Rel]->(dest:Node) 
RETURN src.uri, rel.uri, dest.uri
```

## Proposed Solution: Property-Based Filtering (Recommended)

### Overview
Add `user` and `collection` properties to all nodes and relationships, then filter all operations by these properties. This approach provides strong isolation while maintaining query flexibility and backwards compatibility.

### Data Model Changes

#### Enhanced Node Structure
```cypher
// Node entities
CREATE (n:Node {
  uri: "http://example.com/entity1",
  user: "john_doe", 
  collection: "production_v1"
})

// Literal entities  
CREATE (n:Literal {
  value: "literal value",
  user: "john_doe",
  collection: "production_v1" 
})
```

#### Enhanced Relationship Structure
```cypher
// Relationships with user/collection properties
CREATE (src)-[:Rel {
  uri: "http://example.com/predicate1",
  user: "john_doe",
  collection: "production_v1"
}]->(dest)
```

#### Updated Indexes
```cypher
// Compound indexes for efficient filtering
CREATE INDEX node_user_collection_uri FOR (n:Node) ON (n.user, n.collection, n.uri);
CREATE INDEX literal_user_collection_value FOR (n:Literal) ON (n.user, n.collection, n.value);
CREATE INDEX rel_user_collection_uri FOR ()-[r:Rel]-() ON (r.user, r.collection, r.uri);

// Maintain existing indexes for backwards compatibility (optional)
CREATE INDEX Node_uri FOR (n:Node) ON (n.uri);
CREATE INDEX Literal_value FOR (n:Literal) ON (n.value);
CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri);
```

### Implementation Changes

#### Storage Service (`write.py`)

**Current Code:**
```python
def create_node(self, uri):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri})",
        uri=uri, database_=self.db,
    ).summary
```

**Updated Code:**
```python
def create_node(self, uri, user, collection):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
        uri=uri, user=user, collection=collection, database_=self.db,
    ).summary
```

**Enhanced store_triples Method:**
```python
async def store_triples(self, message):
    user = message.metadata.user
    collection = message.metadata.collection
    
    for t in message.triples:
        self.create_node(t.s.value, user, collection)
        
        if t.o.is_uri:
            self.create_node(t.o.value, user, collection)  
            self.relate_node(t.s.value, t.p.value, t.o.value, user, collection)
        else:
            self.create_literal(t.o.value, user, collection)
            self.relate_literal(t.s.value, t.p.value, t.o.value, user, collection)
```

#### Query Service (`service.py`) 

**Current Code:**
```python
records, summary, keys = self.io.execute_query(
    "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) "
    "RETURN dest.uri as dest",
    src=query.s.value, rel=query.p.value, database_=self.db,
)
```

**Updated Code:**
```python
records, summary, keys = self.io.execute_query(
    "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
    "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
    "(dest:Node {user: $user, collection: $collection}) "
    "RETURN dest.uri as dest",
    src=query.s.value, rel=query.p.value, 
    user=query.user, collection=query.collection,
    database_=self.db,
)
```

### Migration Strategy

#### Phase 1: Add Properties to New Data
1. Update storage service to add user/collection properties to new triples
2. Maintain backwards compatibility by not requiring properties in queries
3. Existing data remains accessible but not isolated

#### Phase 2: Migrate Existing Data  
```cypher
// Migrate existing nodes (requires default user/collection assignment)
MATCH (n:Node) WHERE n.user IS NULL
SET n.user = 'legacy_user', n.collection = 'default_collection';

MATCH (n:Literal) WHERE n.user IS NULL  
SET n.user = 'legacy_user', n.collection = 'default_collection';

MATCH ()-[r:Rel]->() WHERE r.user IS NULL
SET r.user = 'legacy_user', r.collection = 'default_collection';
```

#### Phase 3: Enforce Isolation
1. Update query service to require user/collection filtering
2. Add validation to reject queries without proper user/collection context
3. Remove legacy data access paths

### Security Considerations

#### Query Validation
```python
async def query_triples(self, query):
    # Validate user/collection parameters
    if not query.user or not query.collection:
        raise ValueError("User and collection must be specified")
    
    # All queries must include user/collection filters
    # ... rest of implementation
```

#### Preventing Parameter Injection
- Use parameterized queries exclusively
- Validate user/collection values against allowed patterns
- Consider sanitization for Neo4j property name requirements

#### Audit Trail
```python
logger.info(f"Query executed - User: {query.user}, Collection: {query.collection}, "
           f"Pattern: {query.s}/{query.p}/{query.o}")
```

## Alternative Approaches Considered

### Option 2: Label-Based Isolation

**Approach**: Use dynamic labels like `User_john_Collection_prod`

**Pros:**
- Strong isolation through label filtering
- Efficient query performance with label indexes
- Clear data separation

**Cons:**
- Neo4j has practical limits on number of labels (~1000s)
- Complex label name generation and sanitization
- Difficult to query across collections when needed

**Implementation Example:**
```cypher
CREATE (n:Node:User_john_Collection_prod {uri: "http://example.com/entity"})
MATCH (n:User_john_Collection_prod) WHERE n:Node RETURN n
```

### Option 3: Database-Per-User

**Approach**: Create separate Neo4j databases for each user or user/collection combination

**Pros:**
- Complete data isolation
- No risk of cross-contamination
- Independent scaling per user

**Cons:**
- Resource overhead (each database consumes memory)
- Complex database lifecycle management
- Neo4j Community Edition database limits
- Difficult cross-user analytics

### Option 4: Composite Key Strategy  

**Approach**: Prefix all URIs and values with user/collection information

**Pros:**
- Backwards compatible with existing queries
- Simple implementation
- No schema changes required

**Cons:**
- URI pollution affects data semantics
- Less efficient queries (string prefix matching)
- Breaks RDF/semantic web standards

**Implementation Example:**
```python
def make_composite_uri(uri, user, collection):
    return f"usr:{user}:col:{collection}:uri:{uri}"
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. [ ] Update storage service to accept and store user/collection properties
2. [ ] Add compound indexes for efficient querying
3. [ ] Implement backwards compatibility layer
4. [ ] Create unit tests for new functionality

### Phase 2: Query Updates (Week 2)  
1. [ ] Update all query patterns to include user/collection filters
2. [ ] Add query validation and security checks
3. [ ] Update integration tests
4. [ ] Performance testing with filtered queries

### Phase 3: Migration & Deployment (Week 3)
1. [ ] Create data migration scripts for existing Neo4j instances
2. [ ] Deployment documentation and runbooks
3. [ ] Monitoring and alerting for isolation violations
4. [ ] End-to-end testing with multiple users/collections

### Phase 4: Hardening (Week 4)
1. [ ] Remove legacy compatibility mode
2. [ ] Add comprehensive audit logging
3. [ ] Security review and penetration testing
4. [ ] Performance optimization

## Testing Strategy

### Unit Tests
```python
def test_user_collection_isolation():
    # Store triples for user1/collection1
    processor.store_triples(triples_user1_coll1)
    
    # Store triples for user2/collection2  
    processor.store_triples(triples_user2_coll2)
    
    # Query as user1 should only return user1's data
    results = processor.query_triples(query_user1_coll1)
    assert all_results_belong_to_user1_coll1(results)
    
    # Query as user2 should only return user2's data
    results = processor.query_triples(query_user2_coll2)
    assert all_results_belong_to_user2_coll2(results)
```

### Integration Tests
- Multi-user scenarios with overlapping data
- Cross-collection queries (should fail)  
- Migration testing with existing data
- Performance benchmarks with large datasets

### Security Tests
- Attempt to query other users' data
- SQL injection style attacks on user/collection parameters
- Verify complete isolation under various query patterns

## Performance Considerations

### Index Strategy
- Compound indexes on `(user, collection, uri)` for optimal filtering
- Consider partial indexes if some collections are much larger
- Monitor index usage and query performance

### Query Optimization
- Use EXPLAIN to verify index usage in filtered queries
- Consider query result caching for frequently accessed data
- Profile memory usage with large numbers of users/collections

### Scalability
- Each user/collection combination creates separate data islands
- Monitor database size and connection pool usage
- Consider horizontal scaling strategies if needed

## Security & Compliance

### Data Isolation Guarantees
- **Physical**: All user data stored with explicit user/collection properties
- **Logical**: All queries filtered by user/collection context
- **Access Control**: Service-level validation prevents unauthorized access

### Audit Requirements
- Log all data access with user/collection context
- Track migration activities and data movements
- Monitor for isolation violation attempts

### Compliance Considerations
- GDPR: Enhanced ability to locate and delete user-specific data
- SOC2: Clear data isolation and access controls
- HIPAA: Strong tenant isolation for healthcare data

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Query missing user/collection filter | High | Medium | Mandatory validation, comprehensive testing |
| Performance degradation | Medium | Low | Index optimization, query profiling |
| Migration data corruption | High | Low | Backup strategy, rollback procedures |
| Complex multi-collection queries | Medium | Medium | Document query patterns, provide examples |

## Success Criteria

1. **Security**: Zero cross-user data access in production
2. **Performance**: <10% query performance impact vs unfiltered queries  
3. **Migration**: 100% existing data successfully migrated with zero loss
4. **Usability**: All existing query patterns work with user/collection context
5. **Compliance**: Full audit trail of user/collection data access

## Conclusion

The property-based filtering approach provides the best balance of security, performance, and maintainability for adding user/collection isolation to Neo4j. It aligns with TrustGraph's existing multi-tenancy patterns while leveraging Neo4j's strengths in graph querying and indexing.

This solution ensures TrustGraph's Neo4j backend meets the same security standards as other storage backends, preventing data isolation vulnerabilities while maintaining the flexibility and power of graph queries.