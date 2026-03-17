# CLI Changes: v1.8 to v2.1

## Summary

The CLI (`trustgraph-cli`) has significant additions focused on three themes:
**explainability/provenance**, **embeddings access**, and **graph querying**.
Two legacy tools were removed, one was renamed, and several existing tools
gained new capabilities.

---

## New CLI Tools

### Explainability & Provenance

| Command | Description |
|---------|-------------|
| `tg-list-explain-traces` | Lists all explainability sessions (GraphRAG and Agent) in a collection, showing session IDs, type, question text, and timestamps. |
| `tg-show-explain-trace` | Displays the full explainability trace for a session. For GraphRAG: Question, Exploration, Focus, Synthesis stages. For Agent: Session, Iterations (thought/action/observation), Final Answer. Auto-detects trace type. Supports `--show-provenance` to trace edges back to source documents. |
| `tg-show-extraction-provenance` | Given a document ID, traverses the provenance chain: Document -> Pages -> Chunks -> Edges, using `prov:wasDerivedFrom` relationships. Supports `--show-content` and `--max-content` options. |

### Embeddings

| Command | Description |
|---------|-------------|
| `tg-invoke-embeddings` | Converts text to a vector embedding via the embeddings service. Accepts one or more text inputs, returns vectors as lists of floats. |
| `tg-invoke-graph-embeddings` | Queries graph entities by text similarity using vector embeddings. Returns matching entities with similarity scores. |
| `tg-invoke-document-embeddings` | Queries document chunks by text similarity using vector embeddings. Returns matching chunk IDs with similarity scores. |
| `tg-invoke-row-embeddings` | Queries structured data rows by text similarity on indexed fields. Returns matching rows with index values and scores. Requires `--schema-name` and supports `--index-name`. |

### Graph Querying

| Command | Description |
|---------|-------------|
| `tg-query-graph` | Pattern-based triple store query. Unlike `tg-show-graph` (which dumps everything), this allows selective queries by any combination of subject, predicate, object, and graph. Auto-detects value types: IRIs (`http://...`, `urn:...`, `<...>`), quoted triples (`<<s p o>>`), and literals. |
| `tg-get-document-content` | Retrieves document content from the library by document ID. Can output to file or stdout, handles both text and binary content. |

---

## Removed CLI Tools

| Command | Notes |
|---------|-------|
| `tg-load-pdf` | Removed. Document loading is now handled through the library/processing pipeline. |
| `tg-load-text` | Removed. Document loading is now handled through the library/processing pipeline. |

---

## Renamed CLI Tools

| Old Name | New Name | Notes |
|----------|----------|-------|
| `tg-invoke-objects-query` | `tg-invoke-rows-query` | Reflects the terminology rename from "objects" to "rows" for structured data. |

---

## Significant Changes to Existing Tools

### `tg-invoke-graph-rag`

- **Explainability support**: Now supports a 4-stage explainability pipeline (Question, Grounding/Exploration, Focus, Synthesis) with inline provenance event display.
- **Streaming**: Uses WebSocket streaming for real-time output.
- **Provenance tracing**: Can trace selected edges back to source documents via reification and `prov:wasDerivedFrom` chains.
- Grew from ~30 lines to ~760 lines to accommodate the full explainability pipeline.

### `tg-invoke-document-rag`

- **Explainability support**: Added `question_explainable()` mode that streams Document RAG responses with inline provenance events (Question, Grounding, Exploration, Synthesis stages).

### `tg-invoke-agent`

- **Explainability support**: Added `question_explainable()` mode showing provenance events inline during agent execution (Question, Analysis, Conclusion, AgentThought, AgentObservation, AgentAnswer).
- Verbose mode shows thought/observation streams with emoji prefixes.

### `tg-show-graph`

- **Streaming mode**: Now uses `triples_query_stream()` with configurable batch sizes for lower time-to-first-result and reduced memory overhead.
- **Named graph support**: New `--graph` filter option. Recognises named graphs:
  - Default graph (empty): Core knowledge facts
  - `urn:graph:source`: Extraction provenance
  - `urn:graph:retrieval`: Query-time explainability
- **Show graph column**: New `--show-graph` flag to display the named graph for each triple.
- **Configurable limits**: New `--limit` and `--batch-size` options.

### `tg-graph-to-turtle`

- **RDF-star support**: Now handles quoted triples (RDF-star reification).
- **Streaming mode**: Uses streaming for lower time-to-first-processing.
- **Wire format handling**: Updated to use the new term wire format (`{"t": "i", "i": uri}` for IRIs, `{"t": "l", "v": value}` for literals, `{"t": "r", "r": {...}}` for quoted triples).
- **Named graph support**: New `--graph` filter option.

### `tg-set-tool`

- **New tool type**: `row-embeddings-query` for semantic search on structured data indexes.
- **New options**: `--schema-name`, `--index-name`, `--limit` for configuring row embeddings query tools.

### `tg-show-tools`

- Displays the new `row-embeddings-query` tool type with its `schema-name`, `index-name`, and `limit` fields.

### `tg-load-knowledge`

- **Progress reporting**: Now counts and reports triples and entity contexts loaded per file and in total.
- **Term format update**: Entity contexts now use the new Term format (`{"t": "i", "i": uri}`) instead of the old Value format (`{"v": entity, "e": True}`).

---

## Breaking Changes

- **Terminology rename**: The `Value` schema was renamed to `Term` across the system (PR #622). This affects the wire format used by CLI tools that interact with the graph store. The new format uses `{"t": "i", "i": uri}` for IRIs and `{"t": "l", "v": value}` for literals, replacing the old `{"v": ..., "e": ...}` format.
- **`tg-invoke-objects-query` renamed** to `tg-invoke-rows-query`.
- **`tg-load-pdf` and `tg-load-text` removed**.
