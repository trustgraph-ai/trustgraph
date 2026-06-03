---
layout: default
title: "Knowledge Core Completeness"
parent: "Tech Specs"
---

# Knowledge Core Completeness

## Overview

Knowledge cores are portable snapshots of extracted knowledge: triples, graph
embeddings, and document embeddings stored in Cassandra's `knowledge` keyspace.
They can be downloaded as files, transferred between TrustGraph instances, and
loaded back into vector and graph stores.

Recent additions to TrustGraph — explainability/provenance and named graphs —
were not carried through to the knowledge core system. This means that
exporting and re-importing a core loses provenance links, graph assignments,
and source material, breaking the explainability chain.

This specification addresses three gaps:

1. **Named graphs not stored** — The `g` (graph name) field on triples is
   silently dropped when writing to the core store and comes back as `None`
   on read.
2. **Provenance triples not captured** — Provenance triples (PROV-O) are
   generated during extraction and flow to graph stores, but never enter
   the knowledge core store. It is unclear whether they arrive at the store
   in the correct form.
3. **Source material not included** — Documents, text pages, and chunks in
   the librarian's bucket store are not part of the core. After loading a
   core on a different instance, provenance links to source material point
   at nothing.

## Goals

- **Self-contained cores**: A downloaded knowledge core file contains
  everything needed to reconstruct the full knowledge graph including
  provenance and source attribution on a fresh instance.
- **Named graph preservation**: Round-tripping a core preserves graph
  assignments on all triples.
- **Backward compatibility**: Existing core files (without graph names or
  source material) can still be uploaded and loaded. New fields are optional
  on import.
- **No change to core identity**: A core is still identified by its document
  ID. The additional data is associated with the same core ID.
- **Minimal file format changes**: Extend the existing msgpack record format
  with new record types rather than restructuring existing ones.

## Background

### Current Lifecycle

```
Extraction pipeline
    │
    ├─ triples ──────────────────► knowledge core store (Cassandra)
    ├─ graph embeddings ─────────► knowledge core store (Cassandra)
    ├─ document embeddings ──────► knowledge core store (Cassandra)
    ├─ provenance triples ───────► graph store (only)
    └─ source documents ─────────► librarian bucket store (only)

Download:  Cassandra ──► knowledge manager ──► API gateway ──► client file
Upload:    client file ──► API gateway ──► knowledge manager ──► Cassandra
Load:      Cassandra ──► knowledge manager ──► Pulsar topics ──► graph/vector stores
```

### Current Core File Format (msgpack)

A core file is a sequence of concatenated msgpack records. Each record is a
2-element tuple: `(type_tag, payload)`.

| Type tag | Payload | Description |
|----------|---------|-------------|
| `"t"` | `{"m": {id, root, collection}, "t": [triple_dicts]}` | Triple batch |
| `"ge"` | `{"m": {id, root, collection}, "e": [{entity, vector}]}` | Graph embedding batch |

### What's Missing

#### Named Graphs

The `Triple` dataclass has a `g: str | None` field (graph name IRI), used to
separate provenance graphs (`urn:graph:source`, `urn:graph:retrieval`) from
the default graph. However:

- **Cassandra schema** (`knowledge.triples` table): stores a 6-tuple per
  triple `(s_val, s_is_uri, p_val, p_is_uri, o_val, o_is_uri)` — no graph
  field.
- **`add_triples()`** (`tables/knowledge.py:231`): destructures only `s`,
  `p`, `o` — `g` is discarded.
- **`get_triples()`** (`tables/knowledge.py:396`): reconstructs `Triple`
  with `g` defaulting to `None`.
- **Core file format**: triple dicts do not include a graph field.

#### Provenance Triples

Provenance triples are generated in the extraction pipeline
(`trustgraph-base/trustgraph/provenance/triples.py`) and published to graph
store topics. They use named graphs (`urn:graph:source`,
`urn:graph:retrieval`) and PROV-O vocabulary.

The knowledge core store processor (`storage/knowledge/store.py`) listens on
`triples-input` and `graph-embeddings-input`. Whether provenance triples
arrive on the same `triples-input` topic or a separate one needs
verification. Even if they do arrive, the graph name would be lost (per
above).

#### Source Material

The librarian stores the full document hierarchy in a separate system:

- **Blob store** (S3/MinIO): original documents, text pages, chunks —
  keyed by object UUID under `doc/{object_id}`.
- **Cassandra `library` keyspace**: document metadata including `id`,
  `kind` (MIME type), `title`, `parent_id`, `document_type`
  (`source`/`extracted`), `object_id` (blob reference).

Provenance triples link extracted facts back to chunk/page/document IDs.
Those IDs resolve through the librarian. When a core is loaded on a
different instance, the librarian has no matching documents, so the entire
provenance chain is broken.

### Key Source Files

| Component | File | Purpose |
|-----------|------|---------|
| Core Cassandra schema | `trustgraph-flow/trustgraph/tables/knowledge.py` | Table definitions, read/write |
| Core manager | `trustgraph-flow/trustgraph/cores/knowledge.py` | API operations, load-to-store |
| Core store processor | `trustgraph-flow/trustgraph/storage/knowledge/store.py` | Extraction → Cassandra |
| CLI download | `trustgraph-cli/trustgraph/cli/get_kg_core.py` | Core → msgpack file |
| CLI upload | `trustgraph-cli/trustgraph/cli/put_kg_core.py` | Msgpack file → core |
| CLI load | `trustgraph-cli/trustgraph/cli/load_kg_core.py` | Core → graph/vector stores |
| API client | `trustgraph-base/trustgraph/api/knowledge.py` | Client-side knowledge API |
| Triple schema | `trustgraph-base/trustgraph/schema/core/primitives.py` | Triple dataclass with `g` field |
| Provenance generation | `trustgraph-base/trustgraph/provenance/triples.py` | PROV-O triple creation |
| Librarian | `trustgraph-flow/trustgraph/librarian/librarian.py` | Document storage service |
| Library tables | `trustgraph-flow/trustgraph/tables/library.py` | Document metadata in Cassandra |
| Blob store | `trustgraph-flow/trustgraph/librarian/blob_store.py` | S3/MinIO object storage |

## Technical Design

### Change 1: Named Graph Field in Core Storage

#### Cassandra Schema

Extend the `triples` tuple from 6 to 7 elements, adding the graph name:

```
triples list<tuple<
    text, boolean,       -- s_val, s_is_uri
    text, boolean,       -- p_val, p_is_uri
    text, boolean,       -- o_val, o_is_uri
    text                 -- graph name (empty string = default graph)
>>
```

**Migration**: The schema change uses `ALTER TABLE` or is handled by
creating a new table version. Existing rows with 6-element tuples must be
handled gracefully on read — if the tuple has 6 elements, treat graph as
default.

#### Write Path (`add_triples`)

Change `tables/knowledge.py:add_triples()` to include `triple.g`:

```python
triples = [
    (
        *term_to_tuple(v.s), *term_to_tuple(v.p), *term_to_tuple(v.o),
        v.g or ""
    )
    for v in m.triples
]
```

#### Read Path (`get_triples`)

Change `tables/knowledge.py:get_triples()` to restore the graph name:

```python
Triple(
    s = tuple_to_term(elt[0], elt[1]),
    p = tuple_to_term(elt[2], elt[3]),
    o = tuple_to_term(elt[4], elt[5]),
    g = elt[6] if len(elt) > 6 and elt[6] else None,
)
```

The `len(elt) > 6` guard provides backward compatibility with existing
6-element rows.

#### Core File Format

Extend triple dicts in the `"t"` record to include the graph name:

```python
# In get_kg_core.py write_triple — each triple dict gains "g" key
{"s": ..., "p": ..., "o": ..., "g": "urn:graph:source"}
```

On read (`put_kg_core.py`), treat missing `"g"` key as default graph for
backward compatibility with old core files.

### Change 2: Provenance Triples in Cores

#### Investigation Required

Before implementation, verify:

1. Whether provenance triples arrive on the `triples-input` topic that the
   knowledge core store processor already listens on.
2. If not, which topic they use, and whether the store processor should
   subscribe to it.

#### If provenance triples already arrive at the store

The only change needed is Change 1 (named graphs) — the provenance triples
are already being stored, just without their graph name. Once graph names
are preserved, provenance triples will round-trip correctly.

#### If provenance triples do NOT arrive at the store

Two options:

**Option A — Route provenance to the existing store topic**: Configure the
flow so provenance triples are published to the same `triples-input` topic.
This is the simpler approach and keeps the store processor unchanged.

**Option B — Add a subscription**: Add a new `ConsumerSpec` in the store
processor for the provenance topic. This keeps provenance routing
independent but adds complexity.

Recommendation: Option A, unless there is a reason provenance triples are
intentionally kept off the core store topic.

### Change 3: Source Material in Cores

This is the largest change. The goal is that when a core is loaded on a
fresh instance, provenance links to source material resolve.

#### Architecture

Source material is **not stored in the knowledge core tables**. It lives in
the librarian (Cassandra `library` keyspace + S3/MinIO blob store) and is
fetched on demand via the librarian's existing service API.

The knowledge manager acts as a **client of the librarian service** — it
calls the librarian's request/response API over pub/sub to retrieve document
metadata and content. It does not access the library's Cassandra tables or
blob store directly.

#### Transport

The librarian's pub/sub API already handles chunking of large documents.
This chunking is designed to be websocket-friendly, so library content
flowing through the API gateway to external clients does not require
re-chunking. The API gateway remains a transport layer.

```
Download:
  Knowledge manager ──pub/sub──► Librarian (fetch metadata + content)
  Knowledge manager ──pub/sub──► API gateway ──websocket──► Client

Upload:
  Client ──websocket──► API gateway ──pub/sub──► Knowledge manager
  Knowledge manager ──pub/sub──► Librarian (store metadata + content)
```

#### What to Include

The provenance chain links facts → chunks → pages → documents. For the
chain to resolve, the core must include:

1. **Document metadata** — the library record for each document in the
   hierarchy (id, kind, title, parent_id, document_type, etc.)
2. **Document content** — the blob data for each document (original file,
   extracted text pages, text chunks)

Including the full hierarchy is necessary because:
- A user viewing provenance needs to traverse fact → chunk → page → document
- The chunk text is needed to show what text a fact was extracted from
- The page text provides broader context
- The original document is needed for full source attribution

#### Size Implications

Source material will significantly increase core file sizes. A rough model:

| Component | Typical size per document |
|-----------|-------------------------|
| Triples + embeddings (current) | 1-10 MB |
| Chunk text (all chunks) | ~same as original document |
| Page text (all pages) | ~same as original document |
| Original document (PDF, etc.) | Varies widely (KB to hundreds of MB) |

For a 10 MB PDF, the core could grow from ~5 MB to ~25 MB (original +
derived text + existing data). For large document sets, cores could become
very large.

**Decision needed**: Whether to include original documents or just derived
text (pages + chunks). Including only derived text still allows provenance
display but loses the ability to serve the original file.

#### New Core File Record Types

Add new msgpack record types for library content:

| Type tag | Payload | Description |
|----------|---------|-------------|
| `"lm"` | `{"id", "kind", "title", "parent_id", "document_type", "comments", "tags", "metadata"}` | Library document metadata |
| `"lb"` | `{"id", "data"}` | Library document blob content (chunked by pub/sub layer) |

These are emitted after the existing `"t"` and `"ge"` records during
download and processed during upload.

#### Download Path

Extend `KnowledgeManager.get_kg_core()` to:

1. Stream triples and graph embeddings from the core store (existing
   behavior).
2. Use the librarian service API to retrieve documents associated with
   this core ID:
   a. Fetch the root document metadata and content.
   b. Use `list-children` to discover child documents (pages, chunks).
   c. Recursively fetch metadata and content for each child.
3. Stream each document as `"lm"` (metadata) and `"lb"` (content) records.

The knowledge manager gains the librarian service as a pub/sub dependency.
Large document content is chunked by the librarian's existing pub/sub
transport — the knowledge manager receives and forwards these chunks without
buffering the full blob in memory.

#### Upload Path

Extend `KnowledgeManager.put_kg_core()` to handle the new record types:

1. For `"lm"` records: call the librarian service API to create/update
   the document metadata.
2. For `"lb"` records: call the librarian service API to store the
   document content.

Parent-child relationships are preserved because `parent_id` is stored in
the metadata. Documents should be processed in hierarchy order (parent
before child) to satisfy any ordering constraints.

#### Load Path

The load path (`_load_kg_core`) publishes triples and embeddings to Pulsar
topics for ingestion into graph/vector stores. Source material does not need
to flow through the load path — it is already in the librarian after the
upload step and can be accessed directly by services that need it.

No changes to the load path for source material.

#### CLI Changes

**`tg-get-kg-core`**: Add handling for `"lm"` and `"lb"` record types in
the file writer.

**`tg-put-kg-core`**: Add handling for `"lm"` and `"lb"` record types in
the file reader. Send library records to the knowledge manager alongside
triple/embedding records.

#### Associating Documents with Cores

The core ID is `metadata.root`, which is the root document ID from the
librarian. This provides a natural join: the core's root document and all
its children (pages, chunks) are the source material for that core.

The librarian's `list-children` API provides the child documents. A
recursive traversal from the root document collects the full hierarchy.

### API Changes

#### KnowledgeResponse Schema

Add optional fields to `KnowledgeResponse` for library data:

```python
@dataclass
class KnowledgeResponse:
    error: Error | None = None
    ids: list | None = None
    eos: bool = False
    triples: Triples | None = None
    graph_embeddings: GraphEmbeddings | None = None
    document_embeddings: DocumentEmbeddings | None = None
    library_metadata: LibraryMetadata | None = None    # new
    library_blob: LibraryBlob | None = None            # new
```

#### New Schema Types

```python
@dataclass
class LibraryMetadata:
    id: str
    kind: str | None = None
    title: str | None = None
    parent_id: str | None = None
    document_type: str | None = None
    comments: str | None = None
    tags: list[str] | None = None
    metadata: list[Triple] | None = None

@dataclass
class LibraryBlob:
    id: str
    data: bytes
```

#### Socket API

The existing streaming protocol for `get-kg-core` / `put-kg-core` carries
these new fields naturally — responses already stream multiple record types.

### Dependencies Between Changes

```
Change 1 (named graphs)  ◄── Change 2 depends on this
         │
         └── Change 2 (provenance triples)
                      │
                      └── Change 3 (source material) is independent
```

Change 1 is a prerequisite for Change 2 (provenance triples use named
graphs). Change 3 is independent and can be implemented in parallel.

## Security Considerations

- **Workspace isolation**: Core download/upload must respect workspace
  boundaries. Source material from the librarian must only be included if
  it belongs to the same workspace as the core. This is already enforced
  by the existing workspace-scoped queries.
- **Large blob transfer**: Streaming large documents through the API
  is handled by the librarian's existing pub/sub chunking, which is
  designed to be websocket-friendly. No additional chunking layer is
  needed.
- **Cross-instance trust**: When uploading a core from an external source,
  the library content should be treated as untrusted input. Document
  metadata and blob content should be validated before insertion.

## Performance Considerations

- **Core file size**: Including source material will significantly increase
  core file sizes. Consider adding a flag to download/upload commands to
  optionally exclude source material for use cases where only the knowledge
  graph is needed.
- **Streaming**: All paths already use streaming (paged Cassandra queries,
  msgpack record-at-a-time). Library content should follow the same pattern.
- **Cassandra schema migration**: Changing the tuple width in the `triples`
  table requires careful handling. Cassandra frozen tuples cannot be altered
  in place — a migration strategy is needed (see Migration Plan).

## Testing Strategy

- **Unit tests**: Triple round-trip with graph name (write → read →
  verify `g` field preserved). Backward compatibility with 6-element tuples.
- **Integration tests**: Full lifecycle — extract with provenance → download
  core → upload to fresh instance → load → verify provenance chain resolves.
- **File format tests**: Read old-format core files (no graph name, no
  library records) and verify they load without error.
- **Library inclusion tests**: Download core with source material → upload →
  verify documents accessible through librarian.

## Migration Plan

### Cassandra Schema

The `triples` table stores tuples in a `list<tuple<...>>` column. Cassandra
does not support altering the type of an existing column. Options:

**Option A — New table**: Create a `triples_v2` table with the 7-element
tuple. Migrate data from `triples` to `triples_v2`. The read path checks
both tables during a transition period, then the old table is dropped.

**Option B — Dual read**: Keep the existing table. The read path handles
both 6-element and 7-element tuples by checking length. New writes use
7-element tuples. This works if Cassandra accepts variable-length tuples in
a list — **needs verification**.

**Option C — Separate graph column**: Instead of extending the tuple, add a
parallel `graphs list<text>` column where `graphs[i]` corresponds to
`triples[i]`. This avoids tuple migration entirely but requires keeping the
two lists in sync.

Recommendation: Verify Option B first (simplest). Fall back to Option A if
Cassandra rejects mixed tuple lengths.

### Core File Format

Backward compatible by design:
- Old files lack `"g"` in triple dicts and have no `"lm"`/`"lb"` records →
  handled by defaults.
- New files read by old code → old code ignores unknown record types (the
  existing `read_message` raises on unknown types, so this needs a small
  fix to skip unknown types gracefully).

## Open Questions

1. **Provenance topic routing**: Do provenance triples currently arrive at
   the `triples-input` topic consumed by the knowledge core store? If not,
   what topic are they on?

2. **Include original documents?**: Should cores include the original
   uploaded document (e.g. PDF), or only derived text (pages + chunks)?
   Including originals makes cores fully self-contained but potentially
   very large. Excluding them preserves provenance text display but loses
   the ability to serve the original file.

3. **Optional source material**: Should there be a flag on download/upload
   to include or exclude source material? This would let users choose
   between compact cores (knowledge only) and complete cores (knowledge +
   sources).

4. **Cassandra tuple migration**: Can Cassandra handle mixed-length tuples
   in a `list<tuple<...>>` column, or is a table migration required?

5. **Document embedding cores**: DE cores are managed alongside KG cores.
   Do they need the same treatment (source material inclusion)?  The
   document embeddings reference chunk IDs — the same provenance chain
   applies.

6. **Core versioning**: Should the core file include a version marker so
   readers can distinguish old-format from new-format files without
   trial-and-error parsing?

## References

- Extraction-time provenance: `docs/tech-specs/extraction-time-provenance.md`
- Query-time explainability: `docs/tech-specs/query-time-explainability.md`
- Agent explainability: `docs/tech-specs/agent-explainability.md`
- Data ownership model: `docs/tech-specs/data-ownership-model.md`
