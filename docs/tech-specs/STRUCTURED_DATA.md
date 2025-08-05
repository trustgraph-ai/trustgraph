# Structured Data Technical Specification

## Overview

This specification describes the integration of TrustGraph with structured data flows, enabling the system to work with data that can be represented as rows in tables or objects in object stores. The integration supports four primary use cases:

1. **Unstructured to Structured Extraction**: Read unstructured data sources, identify and extract object structures, and store them in a tabular format
2. **Structured Data Ingestion**: Load data that is already in structured formats directly into the structured store alongside extracted data
3. **Natural Language Querying**: Convert natural language questions into structured queries to extract matching data from the store
4. **Direct Structured Querying**: Execute structured queries directly against the data store for precise data retrieval

## Goals

- **Unified Data Access**: Provide a single interface for accessing both structured and unstructured data within TrustGraph
- **Seamless Integration**: Enable smooth interoperability between TrustGraph's graph-based knowledge representation and traditional structured data formats
- **Flexible Extraction**: Support automatic extraction of structured data from various unstructured sources (documents, text, etc.)
- **Query Versatility**: Allow users to query data using both natural language and structured query languages
- **Data Consistency**: Maintain data integrity and consistency across different data representations
- **Performance Optimization**: Ensure efficient storage and retrieval of structured data at scale
- **Schema Flexibility**: Support both schema-on-write and schema-on-read approaches to accommodate diverse data sources
- **Backwards Compatibility**: Preserve existing TrustGraph functionality while adding structured data capabilities

## Background

TrustGraph currently excels at processing unstructured data and building knowledge graphs from diverse sources. However, many enterprise use cases involve data that is inherently structured - customer records, transaction logs, inventory databases, and other tabular datasets. These structured datasets often need to be analyzed alongside unstructured content to provide comprehensive insights.

Current limitations include:
- No native support for ingesting pre-structured data formats (CSV, JSON arrays, database exports)
- Inability to preserve the inherent structure when extracting tabular data from documents
- Lack of efficient querying mechanisms for structured data patterns
- Missing bridge between SQL-like queries and TrustGraph's graph queries

This specification addresses these gaps by introducing a structured data layer that complements TrustGraph's existing capabilities. By supporting structured data natively, TrustGraph can:
- Serve as a unified platform for both structured and unstructured data analysis
- Enable hybrid queries that span both graph relationships and tabular data
- Provide familiar interfaces for users accustomed to working with structured data
- Unlock new use cases in data integration and business intelligence

## Technical Design

### Architecture

The structured data integration requires the following technical components:

1. **NLP-to-Structured-Query Service**
   - Converts natural language questions into structured queries
   - Supports multiple query language targets (initially SQL-like syntax)
   - Integrates with existing TrustGraph NLP capabilities
   
   Module: trustgraph-flow/trustgraph/query/nlp_query/cassandra

2. **Configuration Schema Support** ✅ **[COMPLETE]**
   - Extended configuration system to store structured data schemas
   - Support for defining table structures, field types, and relationships
   - Schema versioning and migration capabilities

3. **Object Extraction Module** ✅ **[COMPLETE]**
   - Enhanced knowledge extractor flow integration
   - Identifies and extracts structured objects from unstructured sources
   - Maintains provenance and confidence scores
   - Registers a config handler (example: trustgraph-flow/trustgraph/prompt/template/service.py) to receive config data and decode schema information
   - Receives objects and decodes them to ExtractedObject objects for delivery on the Pulsar queue
   - NOTE: There's existing code at `trustgraph-flow/trustgraph/extract/object/row/`. This was a previous attempt and will need to be majorly refactored as it doesn't conform to current APIs. Use it if it's useful, start from scratch if not.
   - Requires a command-line interface: `kg-extract-objects`

   Module: trustgraph-flow/trustgraph/extract/kg/objects/

4. **Structured Store Writer Module** ✅ **[COMPLETE]**
   - Receives objects in ExtractedObject format from Pulsar queues
   - Initial implementation targeting Apache Cassandra as the structured data store
   - Handles dynamic table creation based on schemas encountered
   - Manages schema-to-Cassandra table mapping and data transformation
   - Provides batch and streaming write operations for performance optimization
   - No Pulsar outputs - this is a terminal service in the data flow

   **Schema Handling**:
   - Monitors incoming ExtractedObject messages for schema references
   - When a new schema is encountered for the first time, automatically creates the corresponding Cassandra table
   - Maintains a cache of known schemas to avoid redundant table creation attempts
   - Should consider whether to receive schema definitions directly or rely on schema names in ExtractedObject messages

   **Cassandra Table Mapping**:
   - Keyspace is named after the `user` field from ExtractedObject's Metadata
   - Table is named after the `schema_name` field from ExtractedObject
   - Collection from Metadata becomes part of the partition key to ensure:
     - Natural data distribution across Cassandra nodes
     - Efficient queries within a specific collection
     - Logical isolation between different data imports/sources
   - Primary key structure: `PRIMARY KEY ((collection, <schema_primary_key_fields>), <clustering_keys>)`
     - Collection is always the first component of the partition key
     - Schema-defined primary key fields follow as part of the composite partition key
     - This requires queries to specify the collection, ensuring predictable performance
   - Field definitions map to Cassandra columns with type conversions:
     - `string` → `text`
     - `integer` → `int` or `bigint` based on size hint
     - `float` → `float` or `double` based on precision needs
     - `boolean` → `boolean`
     - `timestamp` → `timestamp`
     - `enum` → `text` with application-level validation
   - Indexed fields create Cassandra secondary indexes (excluding fields already in the primary key)
   - Required fields are enforced at the application level (Cassandra doesn't support NOT NULL)

   **Object Storage**:
   - Extracts values from ExtractedObject.values map
   - Performs type conversion and validation before insertion
   - Handles missing optional fields gracefully
   - Maintains metadata about object provenance (source document, confidence scores)
   - Supports idempotent writes to handle message replay scenarios

   **Implementation Notes**:
   - Existing code at `trustgraph-flow/trustgraph/storage/objects/cassandra/` is outdated and doesn't comply with current APIs
   - Should reference `trustgraph-flow/trustgraph/storage/triples/cassandra` as an example of a working storage processor
   - Needs evaluation of existing code for any reusable components before deciding to refactor or rewrite

   Module: trustgraph-flow/trustgraph/storage/objects/cassandra

5. **Structured Query Service**
   - Accepts structured queries in defined formats
   - Executes queries against the structured store
   - Returns objects matching query criteria
   - Supports pagination and result filtering

   Module: trustgraph-flow/trustgraph/query/objects/cassandra

6. **Agent Tool Integration**
   - New tool class for agent frameworks
   - Enables agents to query structured data stores
   - Provides natural language and structured query interfaces
   - Integrates with existing agent decision-making processes

7. **Structured Data Ingestion Service**
   - Accepts structured data in multiple formats (JSON, CSV, XML)
   - Parses and validates incoming data against defined schemas
   - Converts data into normalized object streams
   - Emits objects to appropriate message queues for processing
   - Supports bulk uploads and streaming ingestion

   Module: trustgraph-flow/trustgraph/decoding/structured

8. **Object Embedding Service**
   - Generates vector embeddings for structured objects
   - Enables semantic search across structured data
   - Supports hybrid search combining structured queries with semantic similarity
   - Integrates with existing vector stores

   Module: trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant

### Data Models

#### Schema Storage Mechanism

Schemas are stored in TrustGraph's configuration system using the following structure:

- **Type**: `schema` (fixed value for all structured data schemas)
- **Key**: The unique name/identifier of the schema (e.g., `customer_records`, `transaction_log`)
- **Value**: JSON schema definition containing the structure

Example configuration entry:
```
Type: schema
Key: customer_records
Value: {
  "name": "customer_records",
  "description": "Customer information table",
  "fields": [
    {
      "name": "customer_id",
      "type": "string",
      "primary_key": true
    },
    {
      "name": "name",
      "type": "string",
      "required": true
    },
    {
      "name": "email",
      "type": "string",
      "required": true
    },
    {
      "name": "registration_date",
      "type": "timestamp"
    },
    {
      "name": "status",
      "type": "string",
      "enum": ["active", "inactive", "suspended"]
    }
  ],
  "indexes": ["email", "registration_date"]
}
```

This approach allows:
- Dynamic schema definition without code changes
- Easy schema updates and versioning
- Consistent integration with existing TrustGraph configuration management
- Support for multiple schemas within a single deployment

### APIs

New APIs:
  - Pulsar schemas for above types
  - Pulsar interfaces in new flows
  - Need a means to specify schema types in flows so that flows know which
    schema types to load
  - APIs added to gateway and rev-gateway

Modified APIs:
- Knowledge extraction endpoints - Add structured object output option
- Agent endpoints - Add structured data tool support

### Implementation Details

Following existing conventions - these are just new processing modules.
Everything is in the trustgraph-flow packages except for schema items
in trustgraph-base.

Need some UI work in the Workbench to be able to demo / pilot this
capability.

## Security Considerations

No extra considerations.

## Performance Considerations

Some questions around using Cassandra queries and indexes so that queries
don't slow down.

## Testing Strategy

Use existing test strategy, will build unit, contract and integration tests.

## Migration Plan

None.

## Timeline

Not specified.

## Open Questions

- Can this be made to work with other store types?  We're aiming to use
  interfaces which make modules which work with one store applicable to
  other stores.

## References

n/a.

