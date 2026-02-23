# Structured Data Technical Specification (Part 2)

## Overview

This specification addresses issues and gaps identified during the initial implementation of TrustGraph's structured data integration, as described in `structured-data.md`.

## Problem Statements

### 1. Naming Inconsistency: "Object" vs "Row"

The current implementation uses "object" terminology throughout (e.g., `ExtractedObject`, object extraction, object embeddings). This naming is too generic and causes confusion:

- "Object" is an overloaded term in software (Python objects, JSON objects, etc.)
- The data being handled is fundamentally tabular - rows in tables with defined schemas
- "Row" more accurately describes the data model and aligns with database terminology

This inconsistency appears in module names, class names, message types, and documentation.

### 2. Row Store Query Limitations

The current row store implementation has significant query limitations:

**Natural Language Mismatch**: Queries struggle with real-world data variations. For example:
- A street database containing `"CHESTNUT ST"` is difficult to find when asking about `"Chestnut Street"`
- Abbreviations, case differences, and formatting variations break exact-match queries
- Users expect semantic understanding, but the store provides literal matching

**Schema Evolution Issues**: Changing schemas causes problems:
- Existing data may not conform to updated schemas
- Table structure changes can break queries and data integrity
- No clear migration path for schema updates

### 3. Row Embeddings Required

Related to problem 2, the system needs vector embeddings for row data to enable:

- Semantic search across structured data (finding "Chestnut Street" when data contains "CHESTNUT ST")
- Similarity matching for fuzzy queries
- Hybrid search combining structured filters with semantic similarity
- Better natural language query support

The embedding service was specified but not implemented.

### 4. Row Data Ingestion Incomplete

The structured data ingestion pipeline is not fully operational:

- Diagnostic prompts exist to classify input formats (CSV, JSON, etc.)
- The ingestion service that uses these prompts is not plumbed into the system
- No end-to-end path for loading pre-structured data into the row store

## Goals

- **Schema Flexibility**: Enable schema evolution without breaking existing data or requiring migrations
- **Consistent Naming**: Standardize on "row" terminology throughout the codebase
- **Semantic Queryability**: Support fuzzy/semantic matching via row embeddings
- **Complete Ingestion Pipeline**: Provide end-to-end path for loading structured data

## Technical Design

### Unified Row Storage Schema

The previous implementation created a separate Cassandra table for each schema. This caused problems when schemas evolved, as table structure changes required migrations.

The new design uses a single unified table for all row data:

```sql
CREATE TABLE rows (
    collection text,
    schema_name text,
    index_name text,
    index_value frozen<list<text>>,
    data map<text, text>,
    source text,
    PRIMARY KEY ((collection, schema_name, index_name), index_value)
)
```

#### Column Definitions

| Column | Type | Description |
|--------|------|-------------|
| `collection` | `text` | Data collection/import identifier (from metadata) |
| `schema_name` | `text` | Name of the schema this row conforms to |
| `index_name` | `text` | Name of the indexed field(s), comma-joined for composites |
| `index_value` | `frozen<list<text>>` | Index value(s) as a list |
| `data` | `map<text, text>` | Row data as key-value pairs |
| `source` | `text` | Optional URI linking to provenance information in the knowledge graph. Empty string or NULL indicates no source. |

#### Index Handling

Each row is stored multiple times - once per indexed field defined in the schema. The primary key fields are treated as an index with no special marker, providing future flexibility.

**Single-field index example:**
- Schema defines `email` as indexed
- `index_name = "email"`
- `index_value = ['foo@bar.com']`

**Composite index example:**
- Schema defines composite index on `region` and `status`
- `index_name = "region,status"` (field names sorted and comma-joined)
- `index_value = ['US', 'active']` (values in same order as field names)

**Primary key example:**
- Schema defines `customer_id` as primary key
- `index_name = "customer_id"`
- `index_value = ['CUST001']`

#### Query Patterns

All queries follow the same pattern regardless of which index is used:

```sql
SELECT * FROM rows
WHERE collection = 'import_2024'
  AND schema_name = 'customers'
  AND index_name = 'email'
  AND index_value = ['foo@bar.com']
```

#### Design Trade-offs

**Advantages:**
- Schema changes don't require table structure changes
- Row data is opaque to Cassandra - field additions/removals are transparent
- Consistent query pattern for all access methods
- No Cassandra secondary indexes (which can be slow at scale)
- Native Cassandra types throughout (`map`, `frozen<list>`)

**Trade-offs:**
- Write amplification: each row insert = N inserts (one per indexed field)
- Storage overhead from duplicated row data
- Type information stored in schema config, conversion at application layer

#### Consistency Model

The design accepts certain simplifications:

1. **No row updates**: The system is append-only. This eliminates consistency concerns about updating multiple copies of the same row.

2. **Schema change tolerance**: When schemas change (e.g., indexes added/removed), existing rows retain their original indexing. Old rows won't be discoverable via new indexes. Users can delete and recreate a schema to ensure consistency if needed.

### Partition Tracking and Deletion

#### The Problem

With the partition key `(collection, schema_name, index_name)`, efficient deletion requires knowing all partition keys to delete. Deleting by just `collection` or `collection + schema_name` requires knowing all the `index_name` values that have data.

#### Partition Tracking Table

A secondary lookup table tracks which partitions exist:

```sql
CREATE TABLE row_partitions (
    collection text,
    schema_name text,
    index_name text,
    PRIMARY KEY ((collection), schema_name, index_name)
)
```

This enables efficient discovery of partitions for deletion operations.

#### Row Writer Behavior

The row writer maintains an in-memory cache of registered `(collection, schema_name)` pairs. When processing a row:

1. Check if `(collection, schema_name)` is in the cache
2. If not cached (first row for this pair):
   - Look up the schema config to get all index names
   - Insert entries into `row_partitions` for each `(collection, schema_name, index_name)`
   - Add the pair to the cache
3. Proceed with writing the row data

The row writer also monitors schema config change events. When a schema changes, relevant cache entries are cleared so the next row triggers re-registration with the updated index names.

This approach ensures:
- Lookup table writes happen once per `(collection, schema_name)` pair, not per row
- The lookup table reflects the indexes that were active when data was written
- Schema changes mid-import are picked up correctly

#### Deletion Operations

**Delete collection:**
```sql
-- 1. Discover all partitions
SELECT schema_name, index_name FROM row_partitions WHERE collection = 'X';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = '...' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table
DELETE FROM row_partitions WHERE collection = 'X';
```

**Delete collection + schema:**
```sql
-- 1. Discover partitions for this schema
SELECT index_name FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = 'Y' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table entries
DELETE FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';
```

### Row Embeddings

Row embeddings enable semantic/fuzzy matching on indexed values, solving the natural language mismatch problem (e.g., finding "CHESTNUT ST" when querying for "Chestnut Street").

#### Design Overview

Each indexed value is embedded and stored in a vector store (Qdrant). At query time, the query is embedded, similar vectors are found, and the associated metadata is used to look up the actual rows in Cassandra.

#### Qdrant Collection Structure

One Qdrant collection per `(user, collection, schema_name, dimension)` tuple:

- **Collection naming:** `rows_{user}_{collection}_{schema_name}_{dimension}`
- Names are sanitized (non-alphanumeric characters replaced with `_`, lowercased, numeric prefixes get `r_` prefix)
- **Rationale:** Enables clean deletion of a `(user, collection, schema_name)` instance by dropping matching Qdrant collections; dimension suffix allows different embedding models to coexist

#### What Gets Embedded

The text representation of index values:

| Index Type | Example `index_value` | Text to Embed |
|------------|----------------------|---------------|
| Single-field | `['foo@bar.com']` | `"foo@bar.com"` |
| Composite | `['US', 'active']` | `"US active"` (space-joined) |

#### Point Structure

Each Qdrant point contains:

```json
{
  "id": "<uuid>",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "index_name": "street_name",
    "index_value": ["CHESTNUT ST"],
    "text": "CHESTNUT ST"
  }
}
```

| Payload Field | Description |
|---------------|-------------|
| `index_name` | The indexed field(s) this embedding represents |
| `index_value` | The original list of values (for Cassandra lookup) |
| `text` | The text that was embedded (for debugging/display) |

Note: `user`, `collection`, and `schema_name` are implicit from the Qdrant collection name.

#### Query Flow

1. User queries for "Chestnut Street" within user U, collection X, schema Y
2. Embed the query text
3. Determine Qdrant collection name(s) matching prefix `rows_U_X_Y_`
4. Search matching Qdrant collection(s) for nearest vectors
5. Get matching points with payloads containing `index_name` and `index_value`
6. Query Cassandra:
   ```sql
   SELECT * FROM rows
   WHERE collection = 'X'
     AND schema_name = 'Y'
     AND index_name = '<from payload>'
     AND index_value = <from payload>
   ```
7. Return matched rows

#### Optional: Filtering by Index Name

Queries can optionally filter by `index_name` in Qdrant to search only specific fields:

- **"Find any field matching 'Chestnut'"** → search all vectors in the collection
- **"Find street_name matching 'Chestnut'"** → filter where `payload.index_name = 'street_name'`

#### Architecture

Row embeddings follow the **two-stage pattern** used by GraphRAG (graph-embeddings, document-embeddings):

- **Stage 1: Embedding computation** (`trustgraph-flow/trustgraph/embeddings/row_embeddings/`) - Consumes `ExtractedObject`, computes embeddings via the embeddings service, outputs `RowEmbeddings`
- **Stage 2: Embedding storage** (`trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/`) - Consumes `RowEmbeddings`, writes vectors to Qdrant

The Cassandra row writer is a separate parallel consumer:

- **Cassandra row writer** (`trustgraph-flow/trustgraph/storage/rows/cassandra`) - Consumes `ExtractedObject`, writes rows to Cassandra

All three services consume from the same flow, keeping them decoupled. This allows:
- Independent scaling of Cassandra writes vs embedding generation vs vector storage
- Embedding services can be disabled if not needed
- Failures in one service don't affect the others
- Consistent architecture with GraphRAG pipelines

#### Write Path

**Stage 1 (row-embeddings processor):** When receiving an `ExtractedObject`:

1. Look up the schema to find indexed fields
2. For each indexed field:
   - Build the text representation of the index value
   - Compute embedding via the embeddings service
3. Output a `RowEmbeddings` message containing all computed vectors

**Stage 2 (row-embeddings-write-qdrant):** When receiving a `RowEmbeddings`:

1. For each embedding in the message:
   - Determine Qdrant collection from `(user, collection, schema_name, dimension)`
   - Create collection if needed (lazy creation on first write)
   - Upsert point with vector and payload

#### Message Types

```python
@dataclass
class RowIndexEmbedding:
    index_name: str              # The indexed field name(s)
    index_value: list[str]       # The field value(s)
    text: str                    # Text that was embedded
    vectors: list[list[float]]   # Computed embedding vectors

@dataclass
class RowEmbeddings:
    metadata: Metadata
    schema_name: str
    embeddings: list[RowIndexEmbedding]
```

#### Deletion Integration

Qdrant collections are discovered by prefix matching on the collection name pattern:

**Delete `(user, collection)`:**
1. List all Qdrant collections matching prefix `rows_{user}_{collection}_`
2. Delete each matching collection
3. Delete Cassandra rows partitions (as documented above)
4. Clean up `row_partitions` entries

**Delete `(user, collection, schema_name)`:**
1. List all Qdrant collections matching prefix `rows_{user}_{collection}_{schema_name}_`
2. Delete each matching collection (handles multiple dimensions)
3. Delete Cassandra rows partitions
4. Clean up `row_partitions`

#### Module Locations

| Stage | Module | Entry Point |
|-------|--------|-------------|
| Stage 1 | `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | `row-embeddings` |
| Stage 2 | `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | `row-embeddings-write-qdrant` |

### Row Embeddings Query API

The row embeddings query is a **separate API** from the GraphQL row query service:

| API | Purpose | Backend |
|-----|---------|---------|
| Row Query (GraphQL) | Exact matching on indexed fields | Cassandra |
| Row Embeddings Query | Fuzzy/semantic matching | Qdrant |

This separation keeps concerns clean:
- GraphQL service focuses on exact, structured queries
- Embeddings API handles semantic similarity
- User workflow: fuzzy search via embeddings to find candidates, then exact query to get full row data

#### Request/Response Schema

```python
@dataclass
class RowEmbeddingsRequest:
    vectors: list[list[float]]    # Query vectors (pre-computed embeddings)
    user: str = ""
    collection: str = ""
    schema_name: str = ""
    index_name: str = ""          # Optional: filter to specific index
    limit: int = 10               # Max results per vector

@dataclass
class RowIndexMatch:
    index_name: str = ""          # The matched index field(s)
    index_value: list[str] = []   # The matched value(s)
    text: str = ""                # Original text that was embedded
    score: float = 0.0            # Similarity score

@dataclass
class RowEmbeddingsResponse:
    error: Error | None = None
    matches: list[RowIndexMatch] = []
```

#### Query Processor

Module: `trustgraph-flow/trustgraph/query/row_embeddings/qdrant`

Entry point: `row-embeddings-query-qdrant`

The processor:
1. Receives `RowEmbeddingsRequest` with query vectors
2. Finds the appropriate Qdrant collection by prefix matching
3. Searches for nearest vectors with optional `index_name` filter
4. Returns `RowEmbeddingsResponse` with matching index information

#### API Gateway Integration

The gateway exposes row embeddings queries via the standard request/response pattern:

| Component | Location |
|-----------|----------|
| Dispatcher | `trustgraph-flow/trustgraph/gateway/dispatch/row_embeddings_query.py` |
| Registration | Add `"row-embeddings"` to `request_response_dispatchers` in `manager.py` |

Flow interface name: `row-embeddings`

Interface definition in flow blueprint:
```json
{
  "interfaces": {
    "row-embeddings": {
      "request": "non-persistent://tg/request/row-embeddings:{id}",
      "response": "non-persistent://tg/response/row-embeddings:{id}"
    }
  }
}
```

#### Python SDK Support

The SDK provides methods for row embeddings queries:

```python
# Flow-scoped query (preferred)
api = Api(url)
flow = api.flow().id("default")

# Query with text (SDK computes embeddings)
matches = flow.row_embeddings_query(
    text="Chestnut Street",
    collection="my_collection",
    schema_name="addresses",
    index_name="street_name",  # Optional filter
    limit=10
)

# Query with pre-computed vectors
matches = flow.row_embeddings_query(
    vectors=[[0.1, 0.2, ...]],
    collection="my_collection",
    schema_name="addresses"
)

# Each match contains:
for match in matches:
    print(match.index_name)   # e.g., "street_name"
    print(match.index_value)  # e.g., ["CHESTNUT ST"]
    print(match.text)         # e.g., "CHESTNUT ST"
    print(match.score)        # e.g., 0.95
```

#### CLI Utility

Command: `tg-invoke-row-embeddings`

```bash
# Query by text (computes embedding automatically)
tg-invoke-row-embeddings \
  --text "Chestnut Street" \
  --collection my_collection \
  --schema addresses \
  --index street_name \
  --limit 10

# Query by vector file
tg-invoke-row-embeddings \
  --vectors vectors.json \
  --collection my_collection \
  --schema addresses

# Output formats
tg-invoke-row-embeddings --text "..." --format json
tg-invoke-row-embeddings --text "..." --format table
```

#### Typical Usage Pattern

The row embeddings query is typically used as part of a fuzzy-to-exact lookup flow:

```python
# Step 1: Fuzzy search via embeddings
matches = flow.row_embeddings_query(
    text="chestnut street",
    collection="geo",
    schema_name="streets"
)

# Step 2: Exact lookup via GraphQL for full row data
for match in matches:
    query = f'''
    query {{
        streets(where: {{ {match.index_name}: {{ eq: "{match.index_value[0]}" }} }}) {{
            street_name
            city
            zip_code
        }}
    }}
    '''
    rows = flow.rows_query(query, collection="geo")
```

This two-step pattern enables:
- Finding "CHESTNUT ST" when user searches for "Chestnut Street"
- Retrieving complete row data with all fields
- Combining semantic similarity with structured data access

### Row Data Ingestion

Deferred to a subsequent phase. Will be designed alongside other ingestion changes.

## Implementation Impact

### Current State Analysis

The existing implementation has two main components:

| Component | Location | Lines | Description |
|-----------|----------|-------|-------------|
| Query Service | `trustgraph-flow/trustgraph/query/objects/cassandra/service.py` | ~740 | Monolithic: GraphQL schema generation, filter parsing, Cassandra queries, request handling |
| Writer | `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py` | ~540 | Per-schema table creation, secondary indexes, insert/delete |

**Current Query Pattern:**
```sql
SELECT * FROM {keyspace}.o_{schema_name}
WHERE collection = 'X' AND email = 'foo@bar.com'
ALLOW FILTERING
```

**New Query Pattern:**
```sql
SELECT * FROM {keyspace}.rows
WHERE collection = 'X' AND schema_name = 'customers'
  AND index_name = 'email' AND index_value = ['foo@bar.com']
```

### Key Changes

1. **Query semantics simplify**: The new schema only supports exact matches on `index_value`. The current GraphQL filters (`gt`, `lt`, `contains`, etc.) either:
   - Become post-filtering on returned data (if still needed)
   - Are removed in favor of using the embeddings API for fuzzy matching

2. **GraphQL code is tightly coupled**: The current `service.py` bundles Strawberry type generation, filter parsing, and Cassandra-specific queries. Adding another row store backend would duplicate ~400 lines of GraphQL code.

### Proposed Refactor

The refactor has two parts:

#### 1. Break Out GraphQL Code

Extract reusable GraphQL components into a shared module:

```
trustgraph-flow/trustgraph/query/graphql/
├── __init__.py
├── types.py        # Filter types (IntFilter, StringFilter, FloatFilter)
├── schema.py       # Dynamic schema generation from RowSchema
└── filters.py      # Filter parsing utilities
```

This enables:
- Reuse across different row store backends
- Cleaner separation of concerns
- Easier testing of GraphQL logic independently

#### 2. Implement New Table Schema

Refactor the Cassandra-specific code to use the unified table:

**Writer** (`trustgraph-flow/trustgraph/storage/rows/cassandra/`):
- Single `rows` table instead of per-schema tables
- Write N copies per row (one per index)
- Register to `row_partitions` table
- Simpler table creation (one-time setup)

**Query Service** (`trustgraph-flow/trustgraph/query/rows/cassandra/`):
- Query the unified `rows` table
- Use extracted GraphQL module for schema generation
- Simplified filter handling (exact match only at DB level)

### Module Renames

As part of the "object" → "row" naming cleanup:

| Current | New |
|---------|-----|
| `storage/objects/cassandra/` | `storage/rows/cassandra/` |
| `query/objects/cassandra/` | `query/rows/cassandra/` |
| `embeddings/object_embeddings/` | `embeddings/row_embeddings/` |

### New Modules

| Module | Purpose |
|--------|---------|
| `trustgraph-flow/trustgraph/query/graphql/` | Shared GraphQL utilities |
| `trustgraph-flow/trustgraph/query/row_embeddings/qdrant/` | Row embeddings query API |
| `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | Row embeddings computation (Stage 1) |
| `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | Row embeddings storage (Stage 2) |

## References

- [Structured Data Technical Specification](structured-data.md)
