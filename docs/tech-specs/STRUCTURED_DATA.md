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

2. **Configuration Schema Support**
   - Extended configuration system to store structured data schemas
   - Support for defining table structures, field types, and relationships
   - Schema versioning and migration capabilities

3. **Object Extraction Module**
   - Enhanced knowledge extractor flow integration
   - Builds on existing prototype in `trustgraph-flow/trustgraph/extract/objects`
   - Identifies and extracts structured objects from unstructured sources
   - Maintains provenance and confidence scores

4. **Structured Store Writer Module**
   - Handles object persistence to structured data stores
   - Initial implementation targeting Apache Cassandra
   - Supports batch and streaming write operations
   - Manages schema mapping and data transformation

5. **Structured Query Service**
   - Accepts structured queries in defined formats
   - Executes queries against the structured store
   - Returns objects matching query criteria
   - Supports pagination and result filtering

6. **Agent Tool Integration**
   - New tool class for agent frameworks
   - Enables agents to query structured data stores
   - Provides natural language and structured query interfaces
   - Integrates with existing agent decision-making processes

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

[API endpoints and interfaces]

### Implementation Details

[Key implementation considerations]

## Security Considerations

[Security requirements and considerations]

## Performance Considerations

[Performance requirements and optimization strategies]

## Testing Strategy

[Testing approach and requirements]

## Migration Plan

[If applicable, migration strategy from existing system]

## Timeline

[Implementation timeline and milestones]

## Open Questions

[Any unresolved questions or decisions to be made]

## References

[Related documents and resources]