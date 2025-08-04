# Structured Data Pulsar Schema Changes

## Overview

Based on the STRUCTURED_DATA.md specification, this document proposes the necessary Pulsar schema additions and modifications to support structured data capabilities in TrustGraph.

## Required Schema Changes

### 1. Core Schema Enhancements

#### Enhanced Field Definition
The existing `Field` class in `core/primitives.py` needs additional properties:

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # NEW FIELDS:
    required = Boolean()  # Whether field is required
    enum_values = Array(String())  # For enum type fields
    indexed = Boolean()  # Whether field should be indexed
```

### 2. New Knowledge Schemas

#### 2.1 Structured Data Submission
New file: `knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # Reference to schema in config
    data = Bytes()  # Raw data to ingest
    options = Map(String())  # Format-specific options
```

### 3. New Service Schemas

#### 3.1 NLP to Structured Query Service
New file: `services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # Optional context for query generation

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # Generated GraphQL query
    variables = Map(String())  # GraphQL variables if any
    detected_schemas = Array(String())  # Which schemas the query targets
    confidence = Double()
```

#### 3.2 Structured Query Service
New file: `services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # GraphQL query
    variables = Map(String())  # GraphQL variables
    operation_name = String()  # Optional operation name for multi-operation documents

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # JSON-encoded GraphQL response data
    errors = Array(String())  # GraphQL errors if any
```

#### 2.2 Object Extraction Output
New file: `knowledge/extraction.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # Which schema this object belongs to
    values = Map(String())  # Field name -> value
    confidence = Double()
    source_span = String()  # Text span where object was found
```

### 4. Enhanced Knowledge Schemas

#### 4.1 Object Embeddings Enhancement
Update `knowledge/embeddings.py` to support structured object embeddings better:

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # Primary key value
    field_embeddings = Map(Array(Double()))  # Per-field embeddings
```

## Integration Points

### Flow Integration

The schemas will be used by new flow modules:
- `trustgraph-flow/trustgraph/decoding/structured` - Uses StructuredDataSubmission
- `trustgraph-flow/trustgraph/query/nlp_query/cassandra` - Uses NLP query schemas
- `trustgraph-flow/trustgraph/query/objects/cassandra` - Uses structured query schemas
- `trustgraph-flow/trustgraph/extract/object/row/` - Consumes Chunk, produces ExtractedObject
- `trustgraph-flow/trustgraph/storage/objects/cassandra` - Uses Rows schema
- `trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - Uses object embedding schemas

## Implementation Notes

1. **Schema Versioning**: Consider adding a `version` field to RowSchema for future migration support
2. **Type System**: The `Field.type` should support all Cassandra native types
3. **Batch Operations**: Most services should support both single and batch operations
4. **Error Handling**: Consistent error reporting across all new services
5. **Backwards Compatibility**: Existing schemas remain unchanged except for minor Field enhancements

## Next Steps

1. Implement schema files in the new structure
2. Update existing services to recognize new schema types
3. Implement flow modules that use these schemas
4. Add gateway/rev-gateway endpoints for new services
5. Create unit tests for schema validation