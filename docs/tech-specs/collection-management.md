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
    user_id text,
    collection_id text,
    name text,
    description text,
    tags set<text>,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (user_id, collection_id)
);
```

Table structure:
- **user_id** + **collection_id**: Composite primary key ensuring user isolation
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

### APIs

New APIs:
- Collection listing with optional filtering by labels/tags
- Collection deletion with confirmation mechanisms
- Collection metadata management (labels and tags)

Modified APIs:
- Collection creation APIs - Enhanced to accept initial labels and tags
- Query APIs - Enhanced to include collection metadata in responses

### Implementation Details

The implementation will follow existing TrustGraph patterns for service integration and CLI command structure.

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

