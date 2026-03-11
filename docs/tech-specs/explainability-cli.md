# Explainability CLI Technical Specification

## Status

Draft

## Overview

This specification describes CLI tools for debugging and exploring explainability data in TrustGraph. These tools enable users to trace how answers were derived and debug the provenance chain from edges back to source documents.

Three CLI tools:

1. **`tg-show-document-hierarchy`** - Show document → page → chunk → edge hierarchy
2. **`tg-list-explain-traces`** - List all GraphRAG sessions with questions
3. **`tg-show-explain-trace`** - Show full explainability trace for a session

## Goals

- **Debugging**: Enable developers to inspect document processing results
- **Auditability**: Trace any extracted fact back to its source document
- **Transparency**: Show exactly how GraphRAG derived an answer
- **Usability**: Simple CLI interface with sensible defaults

## Background

TrustGraph has two provenance systems:

1. **Extraction-time provenance** (see `extraction-time-provenance.md`): Records document → page → chunk → edge relationships during ingestion. Stored in `urn:graph:source` named graph using `prov:wasDerivedFrom`.

2. **Query-time explainability** (see `query-time-explainability.md`): Records question → exploration → focus → synthesis chain during GraphRAG queries. Stored in `urn:graph:retrieval` named graph.

Current limitations:
- No easy way to visualize document hierarchy after processing
- Must manually query triples to see explainability data
- No consolidated view of a GraphRAG session

## Technical Design

### Tool 1: tg-show-document-hierarchy

**Purpose**: Given a document ID, traverse and display all derived entities.

**Usage**:
```bash
tg-show-document-hierarchy "urn:trustgraph:doc:abc123"
tg-show-document-hierarchy --show-content --max-content 500 "urn:trustgraph:doc:abc123"
```

**Arguments**:
| Arg | Description |
|-----|-------------|
| `document_id` | Document URI (positional) |
| `-u/--api-url` | Gateway URL (default: `$TRUSTGRAPH_URL`) |
| `-t/--token` | Auth token (default: `$TRUSTGRAPH_TOKEN`) |
| `-U/--user` | User ID (default: `trustgraph`) |
| `-C/--collection` | Collection (default: `default`) |
| `--show-content` | Include blob/document content |
| `--max-content` | Max chars per blob (default: 200) |
| `--format` | Output: `tree` (default), `json` |

**Implementation**:
1. Query triples: `?child prov:wasDerivedFrom <document_id>` in `urn:graph:source`
2. Recursively query children of each result
3. Build tree structure: Document → Pages → Chunks
4. If `--show-content`, fetch content from librarian API
5. Display as indented tree or JSON

**Output Example**:
```
Document: urn:trustgraph:doc:abc123
  Title: "Sample PDF"
  Type: application/pdf

  └── Page 1: urn:trustgraph:doc:abc123/p1
      ├── Chunk 0: urn:trustgraph:doc:abc123/p1/c0
      │   Content: "The quick brown fox..." [truncated]
      └── Chunk 1: urn:trustgraph:doc:abc123/p1/c1
          Content: "Machine learning is..." [truncated]
```

### Tool 2: tg-list-explain-traces

**Purpose**: List all GraphRAG sessions (questions) in a collection.

**Usage**:
```bash
tg-list-explain-traces
tg-list-explain-traces --limit 20 --format json
```

**Arguments**:
| Arg | Description |
|-----|-------------|
| `-u/--api-url` | Gateway URL |
| `-t/--token` | Auth token |
| `-U/--user` | User ID |
| `-C/--collection` | Collection |
| `--limit` | Max results (default: 50) |
| `--format` | Output: `table` (default), `json` |

**Implementation**:
1. Query: `?session tg:query ?text` in `urn:graph:retrieval`
2. Query timestamps: `?session prov:startedAtTime ?time`
3. Display as table

**Output Example**:
```
Session ID                                    | Question                        | Time
----------------------------------------------|--------------------------------|---------------------
urn:trustgraph:question:abc123                | What was the War on Terror?    | 2024-01-15 10:30:00
urn:trustgraph:question:def456                | Who founded OpenAI?            | 2024-01-15 09:15:00
```

### Tool 3: tg-show-explain-trace

**Purpose**: Show full explainability cascade for a GraphRAG session.

**Usage**:
```bash
tg-show-explain-trace "urn:trustgraph:question:abc123"
tg-show-explain-trace --max-answer 1000 --show-provenance "urn:trustgraph:question:abc123"
```

**Arguments**:
| Arg | Description |
|-----|-------------|
| `question_id` | Question URI (positional) |
| `-u/--api-url` | Gateway URL |
| `-t/--token` | Auth token |
| `-U/--user` | User ID |
| `-C/--collection` | Collection |
| `--max-answer` | Max chars for answer (default: 500) |
| `--show-provenance` | Trace edges to source documents |
| `--format` | Output: `text` (default), `json` |

**Implementation**:
1. Get question text from `tg:query` predicate
2. Find exploration: `?exp prov:wasGeneratedBy <question_id>`
3. Find focus: `?focus prov:wasDerivedFrom <exploration_id>`
4. Get selected edges: `<focus_id> tg:selectedEdge ?edge`
5. For each edge, get `tg:edge` (quoted triple) and `tg:reasoning`
6. Find synthesis: `?synth prov:wasDerivedFrom <focus_id>`
7. Get answer from `tg:document` via librarian
8. If `--show-provenance`, trace edges to source documents

**Output Example**:
```
=== GraphRAG Session: urn:trustgraph:question:abc123 ===

Question: What was the War on Terror?
Time: 2024-01-15 10:30:00

--- Exploration ---
Retrieved 50 edges from knowledge graph

--- Focus (Edge Selection) ---
Selected 12 edges:

  1. (War on Terror, definition, "A military campaign...")
     Reasoning: Directly defines the subject of the query
     Source: chunk → page 2 → "Beyond the Vigilant State"

  2. (Guantanamo Bay, part_of, War on Terror)
     Reasoning: Shows key component of the campaign

--- Synthesis ---
Answer:
  The War on Terror was a military campaign initiated...
  [truncated at 500 chars]
```

## Files to Create

| File | Purpose |
|------|---------|
| `trustgraph-cli/trustgraph/cli/show_document_hierarchy.py` | Tool 1 |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | Tool 2 |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | Tool 3 |

## Files to Modify

| File | Change |
|------|--------|
| `trustgraph-cli/setup.py` | Add console_scripts entries |

## Implementation Notes

1. **Binary content safety**: Try UTF-8 decode; if fails, show `[Binary: {size} bytes]`
2. **Truncation**: Respect `--max-content`/`--max-answer` with `[truncated]` indicator
3. **Quoted triples**: Parse RDF-star format from `tg:edge` predicate
4. **Patterns**: Follow existing CLI patterns from `query_graph.py`

## Security Considerations

- All queries respect user/collection boundaries
- Token authentication supported via `--token` or `$TRUSTGRAPH_TOKEN`

## Testing Strategy

Manual verification with sample data:
```bash
# Load a test document
tg-load-pdf -f test.pdf -c test-collection

# Verify hierarchy
tg-show-document-hierarchy "urn:trustgraph:doc:test"

# Run a GraphRAG query with explainability
tg-invoke-graph-rag --explainable -q "Test question"

# List and inspect traces
tg-list-explain-traces
tg-show-explain-trace "urn:trustgraph:question:xxx"
```

## References

- Query-time explainability: `docs/tech-specs/query-time-explainability.md`
- Extraction-time provenance: `docs/tech-specs/extraction-time-provenance.md`
- Existing CLI example: `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py`
