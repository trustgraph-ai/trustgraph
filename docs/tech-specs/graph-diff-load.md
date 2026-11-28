---
layout: default
title: "Diff Load for Graph Versioning"
parent: "Tech Specs"
---

# Diff Load for Graph Versioning

## Overview

A storage operation that loads triples into a named graph by diffing
against the current live state, avoiding redundant version entries.
Two modes:

1. **Additive** — insert triples not already present; leave everything
   else alone.
2. **Sync** — insert new triples AND write delete markers for triples
   in the graph that aren't in the incoming set.  After sync, the
   graph at the new version exactly matches the input.

## Background

An unconditional load at version N inserts a new row for every triple,
even ones already live from earlier versions.  This wastes storage and
creates misleading version history ("everything changed at version 6"
when only two triples actually differ).

The append-only versioning model is a deliberate trade-off — cheap
rollback and history at the cost of not having built-in merge
semantics.  Diff load brings back smart-merge as an explicit
operation on top of the append-only storage.

## Technical Design

### Chunked Protocol

The client partitions triples by subject key (S) and sends chunks to
the server, each with an explicit key range.  This lets the server
process each chunk independently while ensuring the full key space is
covered (required for sync mode to emit correct deletes).

**Client side:**

1. Parse the input file (Turtle/N-Triples) into triples.
2. Sort by subject IRI.
3. Partition into chunks at subject boundaries (configurable chunk
   size).
4. For N chunks with subject boundaries S1..Sn, send N+1 ranges:
   - `[None, S1)` — empty chunk covering subjects before the data
   - `[S1, S2)`, `[S2, S3)`, ... — data chunks
   - `[Sn, None)` — final chunk covering subjects from Sn onwards
5. Boundary chunks may be empty (no incoming triples) but are
   essential for sync mode — they tell the server "nothing should
   exist in this range."

**Server side (`async_diff_load`):**

For each chunk, scoped to (collection, named_graph, [s_start, s_end)):

1. Scan `quads_by_entity` for all live triples in the S range
   (latest entry per quad with `is_deleted=false`, same resolution
   logic as purge).
2. Build a set of quad identities from the scan.
3. Build a set of quad identities from the incoming triples.
4. **In incoming but not in graph** → insert at new version.
5. **In both** → skip (no-op).
6. **In graph but not in incoming** → if sync mode, write a delete
   marker at new version; if additive, skip.

### Quad Identity

Two triples are "the same" when all of (s, p, o, otype, dtype, lang)
match.  This is the same identity used by the purge operation and is
consistent with RDF semantics where datatype and language tag are
significant.

### Method Signature

```python
async_diff_load(
    collection,       # str
    named_graph,      # str
    version,          # int — the new version being written
    triples,          # list of quad tuples for this chunk
    s_start,          # str | None — inclusive lower bound
    s_end,            # str | None — exclusive upper bound
    sync=False,       # if True, delete triples absent from input
)
```

### Wire Protocol

New operation on the triples service request/response topics:

```json
{
  "operation": "diff-load",
  "collection": "...",
  "named-graph": "...",
  "version": 6,
  "s-start": "http://example.org/A",
  "s-end": "http://example.org/M",
  "sync": true,
  "triples": [...]
}
```

`s-start` and `s-end` are `null` for unbounded.

### CLI

`tg-sync-triples` — analogous to `tg-write-triples` but with diff
semantics.

```
tg-sync-triples --file data.ttl \
    --collection default \
    --named-graph http://example.org/my-graph \
    --version 6 \
    --mode sync \
    --chunk-size 500
```

`--mode` defaults to `sync`.  `--chunk-size` is the number of
distinct subjects per chunk (default TBD).

## Performance Considerations

- Scanning the live state per chunk reuses the same Cassandra query
  patterns as purge — partition-aligned on (collection, s).
- Chunk size trades off network round-trips vs. memory for the
  in-memory set comparison.
- For very large graphs, the client can stream chunks without holding
  the full triple set in memory — only one chunk's worth at a time.

## Open Questions

- Optimal default chunk size (subjects per chunk).
- Whether `version` should be auto-bumped or caller-supplied (current
  design: caller-supplied, consistent with existing write operations).
- Whether to surface a dry-run mode that reports the diff without
  writing.
