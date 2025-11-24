# Vector Store Lifecycle Management

## Overview

This document describes how TrustGraph manages vector store collections across different backend implementations (Qdrant, Pinecone, Milvus). The design addresses the challenge of supporting embeddings with different dimensions without hardcoding dimension values.

## Problem Statement

Vector stores require the embedding dimension to be specified when creating collections/indexes. However:
- Different embedding models produce different dimensions (e.g., 384, 768, 1536)
- The dimension is not known until the first embedding is generated
- A single TrustGraph collection may receive embeddings from multiple models
- Hardcoding a dimension (e.g., 384) causes failures with other embedding sizes

## Design Principles

1. **Lazy Creation**: Collections are created on-demand during first write, not during collection management operations
2. **Dimension-Based Naming**: Collection names include the embedding dimension as a suffix
3. **Graceful Degradation**: Queries against non-existent collections return empty results, not errors
4. **Multi-Dimension Support**: A single logical collection can have multiple physical collections (one per dimension)

## Architecture

### Collection Naming Convention

Vector store collections use dimension suffixes to support multiple embedding sizes:

**Document Embeddings:**
- Qdrant: `d_{user}_{collection}_{dimension}`
- Pinecone: `d-{user}-{collection}-{dimension}`
- Milvus: `doc_{user}_{collection}_{dimension}`

**Graph Embeddings:**
- Qdrant: `t_{user}_{collection}_{dimension}`
- Pinecone: `t-{user}-{collection}-{dimension}`
- Milvus: `entity_{user}_{collection}_{dimension}`

Examples:
- `d_alice_papers_384` - Alice's papers collection with 384-dimensional embeddings
- `d_alice_papers_768` - Same logical collection with 768-dimensional embeddings
- `t_bob_knowledge_1536` - Bob's knowledge graph with 1536-dimensional embeddings

### Lifecycle Phases

#### 1. Collection Creation Request

**Request Flow:**
```
User/System → Librarian → Storage Management Topic → Vector Stores
```

**Behavior:**
- The librarian broadcasts `create-collection` requests to all storage backends
- Vector store processors acknowledge the request but **do not create physical collections**
- Response is returned immediately with success
- Actual collection creation is deferred until first write

**Rationale:**
- Dimension is unknown at creation time
- Avoids creating collections with wrong dimensions
- Simplifies collection management logic

#### 2. Write Operations (Lazy Creation)

**Write Flow:**
```
Data → Storage Processor → Check Collection → Create if Needed → Insert
```

**Behavior:**
1. Extract embedding dimension from the vector: `dim = len(vector)`
2. Construct collection name with dimension suffix
3. Check if collection exists with that specific dimension
4. If not exists:
   - Create collection with correct dimension
   - Log: `"Lazily creating collection {name} with dimension {dim}"`
5. Insert the embedding into the dimension-specific collection

**Example Scenario:**
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

#### 3. Query Operations

**Query Flow:**
```
Query Vector → Determine Dimension → Check Collection → Search or Return Empty
```

**Behavior:**
1. Extract dimension from query vector: `dim = len(vector)`
2. Construct collection name with dimension suffix
3. Check if collection exists
4. If exists:
   - Perform similarity search
   - Return results
5. If not exists:
   - Log: `"Collection {name} does not exist, returning empty results"`
   - Return empty list (no error raised)

**Multiple Dimensions in Same Query:**
- If query contains vectors of different dimensions
- Each dimension queries its corresponding collection
- Results are aggregated
- Missing collections are skipped (not treated as errors)

**Rationale:**
- Querying an empty collection is a valid use case
- Returning empty results is semantically correct
- Avoids errors during system startup or before data ingestion

#### 4. Collection Deletion

**Delete Flow:**
```
Delete Request → List All Collections → Filter by Prefix → Delete All Matches
```

**Behavior:**
1. Construct prefix pattern: `d_{user}_{collection}_` (note trailing underscore)
2. List all collections in the vector store
3. Filter collections matching the prefix
4. Delete all matching collections
5. Log each deletion: `"Deleted collection {name}"`
6. Summary log: `"Deleted {count} collection(s) for {user}/{collection}"`

**Example:**
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

**Rationale:**
- Ensures complete cleanup of all dimension variants
- Pattern matching prevents accidental deletion of unrelated collections
- Atomic operation from user perspective (all dimensions deleted together)

## Behavioral Characteristics

### Normal Operations

**Collection Creation:**
- ✓ Returns success immediately
- ✓ No physical storage allocated
- ✓ Fast operation (no backend I/O)

**First Write:**
- ✓ Creates collection with correct dimension
- ✓ Slightly slower due to collection creation overhead
- ✓ Subsequent writes to same dimension are fast

**Queries Before Any Writes:**
- ✓ Returns empty results
- ✓ No errors or exceptions
- ✓ System remains stable

**Mixed Dimension Writes:**
- ✓ Automatically creates separate collections per dimension
- ✓ Each dimension isolated in its own collection
- ✓ No dimension conflicts or schema errors

**Collection Deletion:**
- ✓ Removes all dimension variants
- ✓ Complete cleanup
- ✓ No orphaned collections

### Edge Cases

**Multiple Embedding Models:**
```
Scenario: User switches from model A (384-dim) to model B (768-dim)
Behavior:
- Both dimensions coexist in separate collections
- Old data (384-dim) remains queryable with 384-dim vectors
- New data (768-dim) queryable with 768-dim vectors
- Cross-dimension queries return results only for matching dimension
```

**Concurrent First Writes:**
```
Scenario: Multiple processes write to same collection simultaneously
Behavior:
- Each process checks for existence before creating
- Most vector stores handle concurrent creation gracefully
- If race condition occurs, second create is typically idempotent
- Final state: Collection exists and both writes succeed
```

**Dimension Migration:**
```
Scenario: User wants to migrate from 384-dim to 768-dim embeddings
Behavior:
- No automatic migration
- Old collection (384-dim) persists
- New collection (768-dim) created on first new write
- Both dimensions remain accessible
- Manual deletion of old dimension collections possible
```

**Empty Collection Queries:**
```
Scenario: Query a collection that has never received data
Behavior:
- Collection doesn't exist (never created)
- Query returns empty list
- No error state
- System logs: "Collection does not exist, returning empty results"
```

## Implementation Notes

### Storage Backend Specifics

**Qdrant:**
- Uses `collection_exists()` for existence checks
- Uses `get_collections()` for listing during deletion
- Collection creation requires `VectorParams(size=dim, distance=Distance.COSINE)`

**Pinecone:**
- Uses `has_index()` for existence checks
- Uses `list_indexes()` for listing during deletion
- Index creation requires waiting for "ready" status
- Serverless spec configured with cloud/region

**Milvus:**
- Direct classes (`DocVectors`, `EntityVectors`) manage lifecycle
- Internal cache `self.collections[(dim, user, collection)]` for performance
- Collection names sanitized (alphanumeric + underscore only)
- Supports schema with auto-incrementing IDs

### Performance Considerations

**First Write Latency:**
- Additional overhead due to collection creation
- Qdrant: ~100-500ms
- Pinecone: ~10-30 seconds (serverless provisioning)
- Milvus: ~500-2000ms (includes indexing)

**Query Performance:**
- Existence check adds minimal overhead (~1-10ms)
- No performance impact once collection exists
- Each dimension collection is independently optimized

**Storage Overhead:**
- Minimal metadata per collection
- Main overhead is per-dimension storage
- Trade-off: Storage space vs. dimension flexibility

## Future Considerations

**Automatic Dimension Consolidation:**
- Could add background process to identify and merge unused dimension variants
- Would require re-embedding or dimension reduction

**Dimension Discovery:**
- Could expose API to list all dimensions in use for a collection
- Useful for administration and monitoring

**Default Dimension Preference:**
- Could track "primary" dimension per collection
- Use for queries when dimension context is unavailable

**Storage Quotas:**
- May need per-collection dimension limits
- Prevent proliferation of dimension variants

## Migration Notes

**From Pre-Dimension-Suffix System:**
- Old collections: `d_{user}_{collection}` (no dimension suffix)
- New collections: `d_{user}_{collection}_{dim}` (with dimension suffix)
- No automatic migration - old collections remain accessible
- Consider manual migration script if needed
- Can run both naming schemes simultaneously

## References

- Collection Management: `docs/tech-specs/collection-management.md`
- Storage Schema: `trustgraph-base/trustgraph/schema/services/storage.py`
- Librarian Service: `trustgraph-flow/trustgraph/librarian/service.py`
