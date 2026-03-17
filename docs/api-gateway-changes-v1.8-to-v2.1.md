# API Gateway Changes: v1.8 to v2.1

## Summary

The API gateway gained new WebSocket service dispatchers for embeddings
queries, a new REST streaming endpoint for document content, and underwent
a significant wire format change from `Value` to `Term`. The "objects"
service was renamed to "rows".

---

## New WebSocket Service Dispatchers

These are new request/response services available through the WebSocket
multiplexer at `/api/v1/socket` (flow-scoped):

| Service Key | Description |
|-------------|-------------|
| `document-embeddings` | Queries document chunks by text similarity. Request/response uses `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse` schemas. |
| `row-embeddings` | Queries structured data rows by text similarity on indexed fields. Request/response uses `RowEmbeddingsRequest`/`RowEmbeddingsResponse` schemas. |

These join the existing `graph-embeddings` dispatcher (which was already
present in v1.8 but may have been updated).

### Full list of WebSocket flow service dispatchers (v2.1)

Request/response services (via `/api/v1/flow/{flow}/service/{kind}` or
WebSocket mux):

- `agent`, `text-completion`, `prompt`, `mcp-tool`
- `graph-rag`, `document-rag`
- `embeddings`, `graph-embeddings`, `document-embeddings`
- `triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
- `row-embeddings`

---

## New REST Endpoint

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/document-stream` | Streams document content from the library as raw bytes. Query parameters: `user` (required), `document-id` (required), `chunk-size` (optional, default 1MB). Returns the document content in chunked transfer encoding, decoded from base64 internally. |

---

## Renamed Service: "objects" to "rows"

| v1.8 | v2.1 | Notes |
|------|------|-------|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | Schema changed from `ObjectsQueryRequest`/`ObjectsQueryResponse` to `RowsQueryRequest`/`RowsQueryResponse`. |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | Import dispatcher for structured data. |

The WebSocket service key changed from `"objects"` to `"rows"`, and the
import dispatcher key similarly changed from `"objects"` to `"rows"`.

---

## Wire Format Change: Value to Term

The serialization layer (`serialize.py`) was rewritten to use the new `Term`
type instead of the old `Value` type.

### Old format (v1.8 — `Value`)

```json
{"v": "http://example.org/entity", "e": true}
```

- `v`: the value (string)
- `e`: boolean flag indicating whether the value is a URI

### New format (v2.1 — `Term`)

IRIs:
```json
{"t": "i", "i": "http://example.org/entity"}
```

Literals:
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```

Quoted triples (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

- `t`: type discriminator — `"i"` (IRI), `"l"` (literal), `"r"` (quoted triple), `"b"` (blank node)
- Serialization now delegates to `TermTranslator` and `TripleTranslator` from `trustgraph.messaging.translators.primitives`

### Other serialization changes

| Field | v1.8 | v2.1 |
|-------|------|------|
| Metadata | `metadata.metadata` (subgraph) | `metadata.root` (simple value) |
| Graph embeddings entity | `entity.vectors` (plural) | `entity.vector` (singular) |
| Document embeddings chunk | `chunk.vectors` + `chunk.chunk` (text) | `chunk.vector` + `chunk.chunk_id` (ID reference) |

---

## Breaking Changes

- **`Value` to `Term` wire format**: All clients sending/receiving triples, embeddings, or entity contexts through the gateway must update to the new Term format.
- **`objects` to `rows` rename**: WebSocket service key and import key changed.
- **Metadata field change**: `metadata.metadata` (a serialized subgraph) replaced by `metadata.root` (a simple value).
- **Embeddings field changes**: `vectors` (plural) became `vector` (singular); document embeddings now reference `chunk_id` instead of inline `chunk` text.
- **New `/api/v1/document-stream` endpoint**: Additive, not breaking.
