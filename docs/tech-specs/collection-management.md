# Collection Management Technical Specification

## Overview

This specification describes the collection management capabilities for TrustGraph, enabling users to have explicit control over collections that are currently implicitly created during data loading and querying operations. The feature supports four primary use cases:

1. **Collection Listing**: View all existing collections in the system
2. **Collection Deletion**: Remove unwanted collections and their associated data
3. **Collection Labeling**: Associate descriptive labels with collections for better organization
4. **Collection Tagging**: Apply tags to collections for categorization and easier discovery

## Goals

- **Explicit Collection Control**: Provide users with direct management capabilities over collections beyond implicit creation
- **Collection Visibility**: Enable users to list and inspect all collections in their environment
- **Collection Cleanup**: Allow deletion of collections that are no longer needed
- **Collection Organization**: Support labels and tags for better collection tracking and discovery
- **Metadata Management**: Associate meaningful metadata with collections for operational clarity
- **Collection Discovery**: Make it easier to find specific collections through filtering and search
- **Operational Transparency**: Provide clear visibility into collection lifecycle and usage
- **Resource Management**: Enable cleanup of unused collections to optimize resource utilization

## Background

Currently, collections in TrustGraph are implicitly created during data loading operations and query execution. While this provides convenience for users, it lacks the explicit control needed for production environments and long-term data management.

Current limitations include:
- No way to list existing collections
- No mechanism to delete unwanted collections
- No ability to associate metadata with collections for tracking purposes
- Difficulty in organizing and discovering collections over time

This specification addresses these gaps by introducing explicit collection management operations. By providing collection management APIs and commands, TrustGraph can:
- Give users full control over their collection lifecycle
- Enable better organization through labels and tags
- Support collection cleanup for resource optimization
- Improve operational visibility and management

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
    collection_id text,
    name text,
    description text,
    tags set<text>,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (user, collection_id)
);
```

Table structure:
- **user** + **collection_id**: Composite primary key ensuring user isolation
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

Collections follow a lazy-creation pattern that aligns with existing TrustGraph behavior:

1. **Lazy Creation**: Collections are automatically created when first referenced during data loading or query operations. No explicit create operation is needed.

2. **Implicit Registration**: When a collection is used (data loading, querying), the system checks if a metadata record exists. If not, a new record is created with default values:
   - `name`: defaults to collection_id
   - `description`: empty
   - `tags`: empty set
   - `created_at`: current timestamp

3. **Explicit Updates**: Users can update collection metadata (name, description, tags) through management operations after lazy creation.

4. **Explicit Deletion**: Users can delete collections, which removes both the metadata record and the underlying collection data across all store types.

5. **Multi-Store Deletion**: Collection deletion cascades across all storage backends (vector stores, object stores, triple stores) as each implements lazy creation and must support collection deletion.

Operations required:
- **Collection Use Notification**: Internal operation triggered during data loading/querying to ensure metadata record exists
- **Update Collection Metadata**: User operation to modify name, description, and tags
- **Delete Collection**: User operation to remove collection and its data across all stores
- **List Collections**: User operation to view collections with filtering by tags

#### Multi-Store Collection Management

Collections exist across multiple storage backends in TrustGraph:
- **Vector Stores**: Store embeddings and vector data for collections
- **Object Stores**: Store documents and file data for collections
- **Triple Stores**: Store graph/RDF data for collections

Each store type implements:
- **Lazy Creation**: Collections are created implicitly when data is first stored
- **Collection Deletion**: Store-specific deletion operations to remove collection data

The librarian service coordinates collection operations across all store types, ensuring consistent collection lifecycle management.

### APIs

New APIs:
- **List Collections**: Retrieve collections for a user with optional tag filtering
- **Update Collection Metadata**: Modify collection name, description, and tags
- **Delete Collection**: Remove collection and associated data with confirmation, cascading to all store types
- **Collection Use Notification** (Internal): Ensure metadata record exists when collection is referenced

Store Writer APIs (Enhanced):
- **Vector Store Collection Deletion**: Remove vector data for specified user and collection
- **Object Store Collection Deletion**: Remove object/document data for specified user and collection
- **Triple Store Collection Deletion**: Remove graph/RDF data for specified user and collection

Modified APIs:
- **Data Loading APIs**: Enhanced to trigger collection use notification for lazy metadata creation
- **Query APIs**: Enhanced to trigger collection use notification and optionally include metadata in responses

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

All store writers will implement a standardized collection management interface with a common schema across store types:

**Message Schema:**
```json
{
  "operation": "delete-collection",
  "user": "user123",
  "collection_id": "documents-2024",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Queue Architecture:**
- **Object Store Collection Management Queue**: Handles collection operations for object/document stores
- **Vector Store Collection Management Queue**: Handles collection operations for vector/embedding stores
- **Triple Store Collection Management Queue**: Handles collection operations for graph/RDF stores

Each store writer implements:
- **Collection Management Handler**: Separate from standard data storage handlers
- **Delete Collection Operation**: Removes all data associated with the specified collection
- **Message Processing**: Consumes from dedicated collection management queue
- **Status Reporting**: Returns success/failure status for coordination
- **Idempotent Operations**: Handles cases where collection doesn't exist (no-op)

**Initial Implementation:**
Only `delete-collection` operation will be implemented initially. The interface supports future operations like `archive-collection`, `migrate-collection`, etc.

Collection operations will be atomic where possible and provide appropriate error handling and validation.

## Security Considerations

Collection management operations require appropriate authorization to prevent unauthorized access or deletion of collections. Access control will align with existing TrustGraph security models.

## Performance Considerations

Collection listing operations may need pagination for environments with large numbers of collections. Metadata queries should be optimized for common filtering patterns.

## Testing Strategy

Comprehensive testing will cover collection lifecycle operations, metadata management, and CLI command functionality with both unit and integration tests.

## Migration Plan

Existing collections will need to be registered in the new metadata system. A migration process will identify and catalog implicit collections.

## Timeline

[To be determined based on development priorities]

## Open Questions

- Should collection deletion be soft or hard delete by default?
- What metadata fields should be required vs optional?

