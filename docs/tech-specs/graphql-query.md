# GraphQL Query Technical Specification

## Overview

This specification describes the implementation of a GraphQL query interface for TrustGraph's structured data storage in Apache Cassandra. Building upon the structured data capabilities outlined in the structured-data.md specification, this document details how GraphQL queries will be executed against Cassandra tables containing extracted and ingested structured objects.

The GraphQL query service will provide a flexible, type-safe interface for querying structured data stored in Cassandra. It will dynamically adapt to schema changes, support complex queries including relationships between objects, and integrate seamlessly with TrustGraph's existing message-based architecture.

## Goals

- **Dynamic Schema Support**: Automatically adapt to schema changes in configuration without service restarts
- **GraphQL Standards Compliance**: Provide a standard GraphQL interface compatible with existing GraphQL tooling and clients
- **Efficient Cassandra Queries**: Translate GraphQL queries into efficient Cassandra CQL queries respecting partition keys and indexes
- **Relationship Resolution**: Support GraphQL field resolvers for relationships between different object types
- **Type Safety**: Ensure type-safe query execution and response generation based on schema definitions
- **Scalable Performance**: Handle concurrent queries efficiently with proper connection pooling and query optimization
- **Request/Response Integration**: Maintain compatibility with TrustGraph's Pulsar-based request/response pattern
- **Error Handling**: Provide comprehensive error reporting for schema mismatches, query errors, and data validation issues

## Background

The structured data storage implementation (trustgraph-flow/trustgraph/storage/objects/cassandra/) writes objects to Cassandra tables based on schema definitions stored in TrustGraph's configuration system. These tables use a composite partition key structure with collection and schema-defined primary keys, enabling efficient queries within collections.

Current limitations that this specification addresses:
- No query interface for the structured data stored in Cassandra
- Inability to leverage GraphQL's powerful query capabilities for structured data
- Missing support for relationship traversal between related objects
- Lack of a standardized query language for structured data access

The GraphQL query service will bridge these gaps by:
- Providing a standard GraphQL interface for querying Cassandra tables
- Dynamically generating GraphQL schemas from TrustGraph configuration
- Efficiently translating GraphQL queries to Cassandra CQL
- Supporting relationship resolution through field resolvers

## Technical Design

### Architecture

The GraphQL query service will be implemented as a new TrustGraph flow processor following established patterns:

**Module Location**: `trustgraph-flow/trustgraph/query/objects/cassandra/`

**Key Components**:

1. **GraphQL Query Service Processor**
   - Extends base FlowProcessor class
   - Implements request/response pattern similar to existing query services
   - Monitors configuration for schema updates
   - Maintains GraphQL schema synchronized with configuration

2. **Dynamic Schema Generator**
   - Converts TrustGraph RowSchema definitions to GraphQL types
   - Creates GraphQL object types with proper field definitions
   - Generates root Query type with collection-based resolvers
   - Updates GraphQL schema when configuration changes

3. **Query Executor**
   - Parses incoming GraphQL queries using Strawberry library
   - Validates queries against current schema
   - Executes queries and returns structured responses
   - Handles errors gracefully with detailed error messages

4. **Cassandra Query Translator**
   - Converts GraphQL selections to CQL queries
   - Optimizes queries based on available indexes and partition keys
   - Handles filtering, pagination, and sorting
   - Manages connection pooling and session lifecycle

5. **Relationship Resolver**
   - Implements field resolvers for object relationships
   - Performs efficient batch loading to avoid N+1 queries
   - Caches resolved relationships within request context
   - Supports both forward and reverse relationship traversal

### Configuration Schema Monitoring

The service will register a configuration handler to receive schema updates:

```python
self.register_config_handler(self.on_schema_config)
```

When schemas change:
1. Parse new schema definitions from configuration
2. Regenerate GraphQL types and resolvers
3. Update the executable schema
4. Clear any schema-dependent caches

### GraphQL Schema Generation

For each RowSchema in configuration, generate:

1. **GraphQL Object Type**:
   - Map field types (string → String, integer → Int, float → Float, boolean → Boolean)
   - Mark required fields as non-nullable in GraphQL
   - Add field descriptions from schema

2. **Root Query Fields**:
   - Collection query (e.g., `customers`, `transactions`)
   - Filtering arguments based on indexed fields
   - Pagination support (limit, offset)
   - Sorting options for sortable fields

3. **Relationship Fields**:
   - Identify foreign key relationships from schema
   - Create field resolvers for related objects
   - Support both single object and list relationships

### Query Execution Flow

1. **Request Reception**:
   - Receive ObjectsQueryRequest from Pulsar
   - Extract GraphQL query string and variables
   - Identify user and collection context

2. **Query Validation**:
   - Parse GraphQL query using Strawberry
   - Validate against current schema
   - Check field selections and argument types

3. **CQL Generation**:
   - Analyze GraphQL selections
   - Build CQL query with proper WHERE clauses
   - Include collection in partition key
   - Apply filters based on GraphQL arguments

4. **Query Execution**:
   - Execute CQL query against Cassandra
   - Map results to GraphQL response structure
   - Resolve any relationship fields
   - Format response according to GraphQL spec

5. **Response Delivery**:
   - Create ObjectsQueryResponse with results
   - Include any execution errors
   - Send response via Pulsar with correlation ID

### Data Models

> **Note**: An existing StructuredQueryRequest/Response schema exists in `trustgraph-base/trustgraph/schema/services/structured_query.py`. However, it lacks critical fields (user, collection) and uses suboptimal types. The schemas below represent the recommended evolution, which should either replace the existing schemas or be created as new ObjectsQueryRequest/Response types.

#### Request Schema (ObjectsQueryRequest)

```python
from pulsar.schema import Record, String, Map, Array

class ObjectsQueryRequest(Record):
    user = String()              # Cassandra keyspace (follows pattern from TriplesQueryRequest)
    collection = String()        # Data collection identifier (required for partition key)
    query = String()             # GraphQL query string
    variables = Map(String())    # GraphQL variables (consider enhancing to support all JSON types)
    operation_name = String()    # Operation to execute for multi-operation documents
```

**Rationale for changes from existing StructuredQueryRequest:**
- Added `user` and `collection` fields to match other query services pattern
- These fields are essential for identifying the Cassandra keyspace and collection
- Variables remain as Map(String()) for now but should ideally support all JSON types

#### Response Schema (ObjectsQueryResponse)

```python
from pulsar.schema import Record, String, Array
from ..core.primitives import Error

class GraphQLError(Record):
    message = String()
    path = Array(String())       # Path to the field that caused the error
    extensions = Map(String())   # Additional error metadata

class ObjectsQueryResponse(Record):
    error = Error()              # System-level error (connection, timeout, etc.)
    data = String()              # JSON-encoded GraphQL response data
    errors = Array(GraphQLError) # GraphQL field-level errors
    extensions = Map(String())   # Query metadata (execution time, etc.)
```

**Rationale for changes from existing StructuredQueryResponse:**
- Distinguishes between system errors (`error`) and GraphQL errors (`errors`)
- Uses structured GraphQLError objects instead of string array
- Adds `extensions` field for GraphQL spec compliance
- Keeps data as JSON string for compatibility, though native types would be preferable

### Cassandra Query Optimization

The service will optimize Cassandra queries by:

1. **Respecting Partition Keys**:
   - Always include collection in queries
   - Use schema-defined primary keys efficiently
   - Avoid full table scans

2. **Leveraging Indexes**:
   - Use secondary indexes for filtering
   - Combine multiple filters when possible
   - Warn when queries may be inefficient

3. **Batch Loading**:
   - Collect relationship queries
   - Execute in batches to reduce round trips
   - Cache results within request context

4. **Connection Management**:
   - Maintain persistent Cassandra sessions
   - Use connection pooling
   - Handle reconnection on failures

### Example GraphQL Queries

#### Simple Collection Query
```graphql
{
  customers(status: "active") {
    customer_id
    name
    email
    registration_date
  }
}
```

#### Query with Relationships
```graphql
{
  orders(order_date_gt: "2024-01-01") {
    order_id
    total_amount
    customer {
      name
      email
    }
    items {
      product_name
      quantity
      price
    }
  }
}
```

#### Paginated Query
```graphql
{
  products(limit: 20, offset: 40) {
    product_id
    name
    price
    category
  }
}
```

### Implementation Dependencies

- **Strawberry GraphQL**: For GraphQL schema definition and query execution
- **Cassandra Driver**: For database connectivity (already used in storage module)
- **TrustGraph Base**: For FlowProcessor and schema definitions
- **Configuration System**: For schema monitoring and updates

### Command-Line Interface

The service will provide a CLI command: `kg-query-objects-graphql-cassandra`

Arguments:
- `--cassandra-host`: Cassandra cluster contact point
- `--cassandra-username`: Authentication username
- `--cassandra-password`: Authentication password
- `--config-type`: Configuration type for schemas (default: "schema")
- Standard FlowProcessor arguments (Pulsar configuration, etc.)

## API Integration

### Pulsar Topics

**Input Topic**: `objects-graphql-query-request`
- Schema: ObjectsQueryRequest
- Receives GraphQL queries from gateway services

**Output Topic**: `objects-graphql-query-response`
- Schema: ObjectsQueryResponse
- Returns query results and errors

### Gateway Integration

The gateway and reverse-gateway will need endpoints to:
1. Accept GraphQL queries from clients
2. Forward to the query service via Pulsar
3. Return responses to clients
4. Support GraphQL introspection queries

### Agent Tool Integration

A new agent tool class will enable:
- Natural language to GraphQL query generation
- Direct GraphQL query execution
- Result interpretation and formatting
- Integration with agent decision flows

## Security Considerations

- **Query Depth Limiting**: Prevent deeply nested queries that could cause performance issues
- **Query Complexity Analysis**: Limit query complexity to prevent resource exhaustion
- **Field-Level Permissions**: Future support for field-level access control based on user roles
- **Input Sanitization**: Validate and sanitize all query inputs to prevent injection attacks
- **Rate Limiting**: Implement query rate limiting per user/collection

## Performance Considerations

- **Query Planning**: Analyze queries before execution to optimize CQL generation
- **Result Caching**: Consider caching frequently accessed data at the field resolver level
- **Connection Pooling**: Maintain efficient connection pools to Cassandra
- **Batch Operations**: Combine multiple queries when possible to reduce latency
- **Monitoring**: Track query performance metrics for optimization

## Testing Strategy

### Unit Tests
- Schema generation from RowSchema definitions
- GraphQL query parsing and validation
- CQL query generation logic
- Field resolver implementations

### Contract Tests
- Pulsar message contract compliance
- GraphQL schema validity
- Response format verification
- Error structure validation

### Integration Tests
- End-to-end query execution against test Cassandra instance
- Schema update handling
- Relationship resolution
- Pagination and filtering
- Error scenarios

### Performance Tests
- Query throughput under load
- Response time for various query complexities
- Memory usage with large result sets
- Connection pool efficiency

## Migration Plan

No migration required as this is a new capability. The service will:
1. Read existing schemas from configuration
2. Connect to existing Cassandra tables created by the storage module
3. Start accepting queries immediately upon deployment

## Timeline

- Week 1-2: Core service implementation and schema generation
- Week 3: Query execution and CQL translation
- Week 4: Relationship resolution and optimization
- Week 5: Testing and performance tuning
- Week 6: Gateway integration and documentation

## Open Questions

1. **Schema Evolution**: How should the service handle queries during schema transitions?
   - Option: Queue queries during schema updates
   - Option: Support multiple schema versions simultaneously

2. **Caching Strategy**: Should query results be cached?
   - Consider: Time-based expiration
   - Consider: Event-based invalidation

3. **Federation Support**: Should the service support GraphQL federation for combining with other data sources?
   - Would enable unified queries across structured and graph data

4. **Subscription Support**: Should the service support GraphQL subscriptions for real-time updates?
   - Would require WebSocket support in gateway

5. **Custom Scalars**: Should custom scalar types be supported for domain-specific data types?
   - Examples: DateTime, UUID, JSON fields

## References

- Structured Data Technical Specification: `docs/tech-specs/structured-data.md`
- Strawberry GraphQL Documentation: https://strawberry.rocks/
- GraphQL Specification: https://spec.graphql.org/
- Apache Cassandra CQL Reference: https://cassandra.apache.org/doc/stable/cassandra/cql/
- TrustGraph Flow Processor Documentation: Internal documentation