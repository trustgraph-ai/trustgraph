# Structured Data: Index Split and Composite Keys

## Problem

The schema `"indexes"` field serves two purposes:

- **Cassandra row storage**: creates denormalised copies for exact-match retrieval
- **Vector embeddings**: sends field values to the embeddings service for semantic search

These are different capabilities with different costs. Embedding integer IDs is wasted compute; conversely, a field may benefit from semantic search without needing a Cassandra retrieval copy.

Additionally, the current Cassandra `rows` table uses `index_value` as the sole clustering column. Two rows sharing the same value for an indexed field (e.g. two stars named "Sirius") silently overwrite each other.

## Changes

### 1. Split index configuration

Replace `"indexes"` with:

- `"query-indexes"` -- fields for Cassandra exact-match lookup
- `"vector-indexes"` -- fields for vector embedding and semantic search

A field can appear in both lists.

### 2. Composite clustering key

Add `row_id` (the value of the schema's primary key field) as a second clustering column:

```
Before:
  PRIMARY KEY ((collection, schema_name, index_name), index_value)

After:
  PRIMARY KEY ((collection, schema_name, index_name), index_value, row_id)
```

This allows multiple rows to share the same index value. Queries by `index_value` alone still work -- Cassandra allows omitting trailing clustering columns.

### 3. Schema config example

```json
{
  "name": "stars",
  "fields": [
    {"name": "id", "type": "integer", "primary_key": true},
    {"name": "proper", "type": "string"},
    {"name": "spect", "type": "string"},
    {"name": "con", "type": "string"}
  ],
  "query-indexes": ["id", "proper", "con"],
  "vector-indexes": ["proper", "spect", "con"]
}
```

## Future considerations

1. **Composite primary keys**: The primary key could span multiple columns
   (e.g. `"primary_key": ["region", "id"]`). The data model already
   supports this -- `row_id` in Cassandra is `frozen<list<text>>` and
   `index_value` is already a list. The schema config and writer would
   need to resolve multiple fields into the `row_id` value.

2. **Composite query indexes**: Each query index entry could cover multiple
   columns (e.g. `"query-indexes": [["last_name", "first_name"], "email"]`).
   This would allow exact-match lookup on field combinations. The Cassandra
   storage already uses `index_value` as a `frozen<list<text>>`, so the
   data model supports it -- the config parsing and index value construction
   would need updating.

### Affected components

- `storage/rows/cassandra/write.py` -- table schema, reads `query-indexes`, writes `row_id`
- `embeddings/row_embeddings/embeddings.py` -- reads `vector-indexes`
- `query/row_embeddings/qdrant/service.py` -- no change (consumes embeddings output)
- Row query service -- must handle multiple rows per index value
