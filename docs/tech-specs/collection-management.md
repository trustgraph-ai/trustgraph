# Collection Management Technical Specification

## Overview

This specification describes the collection management capabilities for TrustGraph, requiring explicit collection creation and providing direct control over the collection lifecycle. Collections must be explicitly created before use, ensuring proper synchronization between the librarian metadata and all storage backends. The feature supports four primary use cases:

1. **Collection Creation**: Explicitly create collections before storing data
2. **Collection Listing**: View all existing collections in the system
3. **Collection Metadata Management**: Update collection names, descriptions, and tags
4. **Collection Deletion**: Remove collections and their associated data across all storage types

## Goals

- **Explicit Collection Creation**: Require collections to be created before data can be stored
- **Storage Synchronization**: Ensure collections exist in all storage backends (vectors, objects, triples)
- **Collection Visibility**: Enable users to list and inspect all collections in their environment
- **Collection Cleanup**: Allow deletion of collections that are no longer needed
- **Collection Organization**: Support labels and tags for better collection tracking and discovery
- **Metadata Management**: Associate meaningful metadata with collections for operational clarity
- **Collection Discovery**: Make it easier to find specific collections through filtering and search
- **Operational Transparency**: Provide clear visibility into collection lifecycle and usage
- **Resource Management**: Enable cleanup of unused collections to optimize resource utilization
- **Data Integrity**: Prevent orphaned collections in storage without metadata tracking

## Background

Previously, collections in TrustGraph were implicitly created during data loading operations, leading to synchronization issues where collections could exist in storage backends without corresponding metadata in the librarian. This created management challenges and potential orphaned data.

The explicit collection creation model addresses these issues by:
- Requiring collections to be created before use via `tg-set-collection`
- Broadcasting collection creation to all storage backends
- Maintaining synchronized state between librarian metadata and storage
- Preventing writes to non-existent collections
- Providing clear collection lifecycle management

This specification defines the explicit collection management model. By requiring explicit collection creation, TrustGraph ensures:
- Collections are tracked in librarian metadata from creation
- All storage backends are aware of collections before receiving data
- No orphaned collections exist in storage
- Clear operational visibility and control over collection lifecycle
- Consistent error handling when operations reference non-existent collections

## Technical Design

### Architecture

The collection management system will be implemented within existing TrustGraph infrastructure:

1. **Librarian Service Integration**
   - Collection management operations will be added to the existing librarian service
   - No new service required - leverages existing authentication and access patterns
   - Handles collection listing, deletion, and metadata management

   Module: trustgraph-librarian

2. **Cassandra Collection Metadata Table**
   - New table in the existing librarian keyspace
   - Stores collection metadata with user-scoped access
   - Primary key: (user_id, collection_id) for proper multi-tenancy

   Module: trustgraph-librarian

3. **Collection Management CLI**
   - Command-line interface for collection operations
   - Provides list, delete, label, and tag management commands
   - Integrates with existing CLI framework

   Module: trustgraph-cli

### Data Models

#### Cassandra Collection Metadata Table

The collection metadata will be stored in a structured Cassandra table in the librarian keyspace:

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

Table structure:
- **user** + **collection**: Composite primary key ensuring user isolation
- **name**: Human-readable collection name
- **description**: Detailed description of collection purpose
- **tags**: Set of tags for categorization and filtering
- **created_at**: Collection creation timestamp
- **updated_at**: Last modification timestamp

This approach allows:
- Multi-tenant collection management with user isolation
- Efficient querying by user and collection
- Flexible tagging system for organization
- Lifecycle tracking for operational insights

#### Collection Lifecycle

Collections are explicitly created in the librarian before data operations can proceed:

1. **Collection Creation** (Two Paths):

   **Path A: User-Initiated Creation** via `tg-set-collection`:
   - User provides collection ID, name, description, and tags
   - Librarian creates metadata record in `collections` table
   - Librarian broadcasts "create-collection" to all storage backends
   - All storage processors create collection and confirm success
   - Collection is now ready for data operations

   **Path B: Automatic Creation on Document Submission**:
   - User submits document specifying a collection ID
   - Librarian checks if collection exists in metadata table
   - If not exists: Librarian creates metadata with defaults (name=collection_id, empty description/tags)
   - Librarian broadcasts "create-collection" to all storage backends
   - All storage processors create collection and confirm success
   - Document processing proceeds with collection now established

   Both paths ensure collection exists in librarian metadata AND all storage backends before data operations.

2. **Storage Validation**: Write operations validate collection exists:
   - Storage processors check collection state before accepting writes
   - Writes to non-existent collections return error
   - This prevents direct writes bypassing the librarian's collection creation logic

3. **Query Behavior**: Query operations handle non-existent collections gracefully:
   - Queries to non-existent collections return empty results
   - No error thrown for query operations
   - Allows exploration without requiring collection to exist

4. **Metadata Updates**: Users can update collection metadata after creation:
   - Update name, description, and tags via `tg-set-collection`
   - Updates apply to librarian metadata only
   - Storage backends maintain collection but metadata updates don't propagate

5. **Explicit Deletion**: Users delete collections via `tg-delete-collection`:
   - Librarian broadcasts "delete-collection" to all storage backends
   - Waits for confirmation from all storage processors
   - Deletes librarian metadata record only after storage cleanup complete
   - Ensures no orphaned data remains in storage

**Key Principle**: The librarian is the single point of control for collection creation. Whether initiated by user command or document submission, the librarian ensures proper metadata tracking and storage backend synchronization before allowing data operations.

Operations required:
- **Create Collection**: User operation via `tg-set-collection` OR automatic on document submission
- **Update Collection Metadata**: User operation to modify name, description, and tags
- **Delete Collection**: User operation to remove collection and its data across all stores
- **List Collections**: User operation to view collections with filtering by tags

#### Multi-Store Collection Management

Collections exist across multiple storage backends in TrustGraph:
- **Vector Stores** (Qdrant, Milvus, Pinecone): Store embeddings and vector data
- **Object Stores** (Cassandra): Store documents and file data
- **Triple Stores** (Cassandra, Neo4j, Memgraph, FalkorDB): Store graph/RDF data

Each store type implements:
- **Collection State Tracking**: Maintain knowledge of which collections exist
- **Collection Creation**: Accept and process "create-collection" operations
- **Collection Validation**: Check collection exists before accepting writes
- **Collection Deletion**: Remove all data for specified collection

The librarian service coordinates collection operations across all store types, ensuring:
- Collections created in all backends before use
- All backends confirm creation before returning success
- Synchronized collection lifecycle across storage types
- Consistent error handling when collections don't exist

#### Collection State Tracking by Storage Type

Each storage backend tracks collection state differently based on its capabilities:

**Cassandra Triple Store:**
- Uses existing `triples_collection` table
- Creates system marker triple when collection created
- Query: `SELECT collection FROM triples_collection WHERE collection = ? LIMIT 1`
- Efficient single-partition check for collection existence

**Qdrant/Milvus/Pinecone Vector Stores:**
- Native collection APIs provide existence checking
- Collections created with proper vector configuration
- `collection_exists()` method uses storage API
- Collection creation validates dimension requirements

**Neo4j/Memgraph/FalkorDB Graph Stores:**
- Use `:CollectionMetadata` nodes to track collections
- Node properties: `{user, collection, created_at}`
- Query: `MATCH (c:CollectionMetadata {user: $user, collection: $collection})`
- Separate from data nodes for clean separation
- Enables efficient collection listing and validation

**Cassandra Object Store:**
- Uses collection metadata table or marker rows
- Similar pattern to triple store
- Validates collection before document writes

### APIs

Collection Management APIs (Librarian):
- **Create/Update Collection**: Create new collection or update existing metadata via `tg-set-collection`
- **List Collections**: Retrieve collections for a user with optional tag filtering
- **Delete Collection**: Remove collection and associated data, cascading to all store types

Storage Management APIs (All Storage Processors):
- **Create Collection**: Handle "create-collection" operation, establish collection in storage
- **Delete Collection**: Handle "delete-collection" operation, remove all collection data
- **Collection Exists Check**: Internal validation before accepting write operations

Data Operation APIs (Modified Behavior):
- **Write APIs**: Validate collection exists before accepting data, return error if not
- **Query APIs**: Return empty results for non-existent collections without error

### Implementation Details

The implementation will follow existing TrustGraph patterns for service integration and CLI command structure.

#### Collection Deletion Cascade

When a user initiates collection deletion through the librarian service:

1. **Metadata Validation**: Verify collection exists and user has permission to delete
2. **Store Cascade**: Librarian coordinates deletion across all store writers:
   - Vector store writer: Remove embeddings and vector indexes for the user and collection
   - Object store writer: Remove documents and files for the user and collection
   - Triple store writer: Remove graph data and triples for the user and collection
3. **Metadata Cleanup**: Remove collection metadata record from Cassandra
4. **Error Handling**: If any store deletion fails, maintain consistency through rollback or retry mechanisms

#### Collection Management Interface

All store writers implement a standardized collection management interface with a common schema:

**Message Schema (`StorageManagementRequest`):**
```json
{
  "operation": "create-collection" | "delete-collection",
  "user": "user123",
  "collection": "documents-2024"
}
```

**Queue Architecture:**
- **Vector Store Management Queue** (`vector-storage-management`): Vector/embedding stores
- **Object Store Management Queue** (`object-storage-management`): Object/document stores
- **Triple Store Management Queue** (`triples-storage-management`): Graph/RDF stores
- **Storage Response Queue** (`storage-management-response`): All responses sent here

Each store writer implements:
- **Collection Management Handler**: Processes `StorageManagementRequest` messages
- **Create Collection Operation**: Establishes collection in storage backend
- **Delete Collection Operation**: Removes all data associated with collection
- **Collection State Tracking**: Maintains knowledge of which collections exist
- **Message Processing**: Consumes from dedicated management queue
- **Status Reporting**: Returns success/failure via `StorageManagementResponse`
- **Idempotent Operations**: Safe to call create/delete multiple times

**Supported Operations:**
- `create-collection`: Create collection in storage backend
- `delete-collection`: Remove all collection data from storage backend

#### Cassandra Triple Store Refactor

As part of this implementation, the Cassandra triple store will be refactored from a table-per-collection model to a unified table model:

**Current Architecture:**
- Keyspace per user, separate table per collection
- Schema: `(s, p, o)` with `PRIMARY KEY (s, p, o)`
- Table names: user collections become separate Cassandra tables

**New Architecture:**
- Keyspace per user, single "triples" table for all collections
- Schema: `(collection, s, p, o)` with `PRIMARY KEY (collection, s, p, o)`
- Collection isolation through collection partitioning

**Changes Required:**

1. **TrustGraph Class Refactor** (`trustgraph/direct/cassandra.py`):
   - Remove `table` parameter from constructor, use fixed "triples" table
   - Add `collection` parameter to all methods
   - Update schema to include collection as first column
   - **Index Updates**: New indexes will be created to support all 8 query patterns:
     - Index on `(s)` for subject-based queries
     - Index on `(p)` for predicate-based queries
     - Index on `(o)` for object-based queries
     - Note: Cassandra doesn't support multi-column secondary indexes, so these are single-column indexes

   - **Query Pattern Performance**:
     - ✅ `get_all()` - partition scan on `collection`
     - ✅ `get_s(s)` - uses primary key efficiently (`collection, s`)
     - ✅ `get_p(p)` - uses `idx_p` with `collection` filtering
     - ✅ `get_o(o)` - uses `idx_o` with `collection` filtering
     - ✅ `get_sp(s, p)` - uses primary key efficiently (`collection, s, p`)
     - ⚠️ `get_po(p, o)` - requires `ALLOW FILTERING` (uses either `idx_p` or `idx_o` plus filtering)
     - ✅ `get_os(o, s)` - uses `idx_o` with additional filtering on `s`
     - ✅ `get_spo(s, p, o)` - uses full primary key efficiently

   - **Note on ALLOW FILTERING**: The `get_po` query pattern requires `ALLOW FILTERING` as it needs both predicate and object constraints without a suitable compound index. This is acceptable as this query pattern is less common than subject-based queries in typical triple store usage

2. **Storage Writer Updates** (`trustgraph/storage/triples/cassandra/write.py`):
   - Maintain single TrustGraph connection per user instead of per (user, collection)
   - Pass collection to insert operations
   - Improved resource utilization with fewer connections

3. **Query Service Updates** (`trustgraph/query/triples/cassandra/service.py`):
   - Single TrustGraph connection per user
   - Pass collection to all query operations
   - Maintain same query logic with collection parameter

**Benefits:**
- **Simplified Collection Deletion**: Delete using `collection` partition key across all 4 tables
- **Resource Efficiency**: Fewer database connections and table objects
- **Cross-Collection Operations**: Easier to implement operations spanning multiple collections
- **Consistent Architecture**: Aligns with unified collection metadata approach
- **Collection Validation**: Easy to check collection existence via `triples_collection` table

Collection operations will be atomic where possible and provide appropriate error handling and validation.

## Security Considerations

Collection management operations require appropriate authorization to prevent unauthorized access or deletion of collections. Access control will align with existing TrustGraph security models.

## Performance Considerations

Collection listing operations may need pagination for environments with large numbers of collections. Metadata queries should be optimized for common filtering patterns.

## Testing Strategy

Comprehensive testing will cover:
- Collection creation workflow end-to-end
- Storage backend synchronization
- Write validation for non-existent collections
- Query handling of non-existent collections
- Collection deletion cascade across all stores
- Error handling and recovery scenarios
- Unit tests for each storage backend
- Integration tests for cross-store operations

## Implementation Status

### ✅ Completed Components

1. **Librarian Collection Management Service** (`trustgraph-flow/trustgraph/librarian/collection_manager.py`)
   - Collection metadata CRUD operations (list, update, delete)
   - Cassandra collection metadata table integration via `LibraryTableStore`
   - Collection deletion cascade coordination across all storage types
   - Async request/response handling with proper error management

2. **Collection Metadata Schema** (`trustgraph-base/trustgraph/schema/services/collection.py`)
   - `CollectionManagementRequest` and `CollectionManagementResponse` schemas
   - `CollectionMetadata` schema for collection records
   - Collection request/response queue topic definitions

3. **Storage Management Schema** (`trustgraph-base/trustgraph/schema/services/storage.py`)
   - `StorageManagementRequest` and `StorageManagementResponse` schemas
   - Storage management queue topics defined
   - Message format for storage-level collection operations

4. **Cassandra 4-Table Schema** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py`)
   - Compound partition keys for query performance
   - `triples_collection` table for SPO queries and deletion tracking
   - Collection deletion implemented with read-then-delete pattern

### 🔄 In Progress Components

1. **Collection Creation Broadcast** (`trustgraph-flow/trustgraph/librarian/collection_manager.py`)
   - Update `update_collection()` to send "create-collection" to storage backends
   - Wait for confirmations from all storage processors
   - Handle creation failures appropriately

2. **Document Submission Handler** (`trustgraph-flow/trustgraph/librarian/service.py` or similar)
   - Check if collection exists when document submitted
   - If not exists: Create collection with defaults before processing document
   - Trigger same "create-collection" broadcast as `tg-set-collection`
   - Ensure collection established before document flows to storage processors

### ❌ Pending Components

1. **Collection State Tracking** - Need to implement in each storage backend:
   - **Cassandra Triples**: Use `triples_collection` table with marker triples
   - **Neo4j/Memgraph/FalkorDB**: Create `:CollectionMetadata` nodes
   - **Qdrant/Milvus/Pinecone**: Use native collection APIs
   - **Cassandra Objects**: Add collection metadata tracking

2. **Storage Management Handlers** - Need "create-collection" support in 12 files:
   - `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
   - `trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`
   - `trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
   - `trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
   - `trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
   - `trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
   - `trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
   - `trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
   - `trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
   - `trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
   - `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
   - Plus any other storage implementations

3. **Write Operation Validation** - Add collection existence checks to all `store_*` methods

4. **Query Operation Handling** - Update queries to return empty for non-existent collections

### Next Implementation Steps

**Phase 1: Core Infrastructure (2-3 days)**
1. Add collection state tracking methods to all storage backends
2. Implement `collection_exists()` and `create_collection()` methods

**Phase 2: Storage Handlers (1 week)**
3. Add "create-collection" handlers to all storage processors
4. Add write validation to reject non-existent collections
5. Update query handling for non-existent collections

**Phase 3: Collection Manager (2-3 days)**
6. Update collection_manager to broadcast creates
7. Implement response tracking and error handling

**Phase 4: Testing (3-5 days)**
8. End-to-end testing of explicit creation workflow
9. Test all storage backends
10. Validate error handling and edge cases

