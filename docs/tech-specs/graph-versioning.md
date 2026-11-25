---
layout: default
title: "Tech Spec: Graph Versioning"
parent: "Tech Specs"
---

# Tech Spec: Graph Versioning

**Status:** Draft  
**Author:** Mark  
**Date:** 2026-11-24  

## Problem Statement

When a knowledge graph is re-ingested or updated, the previous state is
lost.  There is no way to:

- **View the graph at a previous point in time** — e.g. "what did the
  graph look like before last Tuesday's ingestion?"
- **Diff between versions** — what triples were added, removed or
  changed between two points in time?
- **Revert** — roll back to a known-good state after a bad ingestion
  or extraction run.

## Current State

Graph data is stored as quads in Cassandra.  Each quad has:

| Column | Purpose |
|--------|---------|
| `collection` | Partition scoping (workspace/collection) |
| `entity` | Entity identifier |
| `role` | Entity role (subject/object) |
| `p` | Predicate |
| `otype` | Object type (URI/literal) |
| `s` | Subject |
| `o` | Object |
| `d` | Named graph (dataset IRI) — renamed to `g` in the new schema |
| `dtype` | Datatype |
| `lang` | Language tag |

All columns are part of the primary key.  There is no temporal
dimension — writes are upserts, and deletions are immediate.

A related gap: named graphs (`d`/`g`) are not enumerated anywhere.
Discovering which named graphs exist requires a full table scan.
This is in the same problem space but may be addressed separately.

## Requirements

1. **Point-in-time view** — query the graph as it existed at version V.
2. **Diff** — given two versions, return added and removed triples.
3. **Revert** — restore the graph to a previous version.
4. **Low overhead on the write path** — versioning should not
   significantly slow ingestion.
5. **Storage-efficient** — avoid full copies of the graph per version.
6. **Zero-cost version creation** — creating a new version should not
   require any data copying or I/O.

## Design: Append-Only Version Log

### Core Idea

Add two columns to the entity table:

| Column | Type | Key role | Purpose |
|--------|------|----------|---------|
| `version` | `bigint` | Clustering column (DESC) | Version when this action occurred |
| `is_deleted` | `boolean` | Regular column | `false` = added/live, `true` = deleted |

The updated primary key:

```
PRIMARY KEY (
    (collection, entity),
    role, p, otype, s, o, g, dtype, lang, version
)
WITH CLUSTERING ORDER BY (
    role ASC, p ASC, otype ASC, s ASC, o ASC,
    g ASC, dtype ASC, lang ASC, version DESC
)
```

`version` is the final clustering column.  All versions of the same
quad sit contiguously on disk, sorted newest-first.  Every row is an
immutable fact: "at version V, this quad was added/deleted".  The same
quad can have multiple rows recording its full lifecycle.

### Write Path — Zero Reads

All writes are blind INSERTs stamped with the current version.  No
read-before-write, no existence checks.

**Insert quad**: blind insert with `version = current_version`,
`is_deleted = false`.

**Delete quad (explicit triples)**: blind insert with
`version = current_version`, `is_deleted = true`.  Zero reads.

**Delete quad (pattern)**: pattern-based deletion (`s`, `p`, `o`,
`g`) first queries matching live quads at the current version, then
blind-inserts `(V, true)` markers for each match.  Not zero-read,
but the read is a standard query and the writes are still
append-only.

Deletes are equally simple: blind insert `(V, true)`.  Idempotent
even if the quad doesn't exist or is already deleted.

Because `is_deleted` is a regular column (not part of the primary
key), multiple writes for the same quad at the same version collapse
into a single row — Cassandra's upsert overwrites `is_deleted` in
place.  There is exactly one row per quad per version, and the final
value of `is_deleted` reflects the last write.  No ambiguous states.

### Write Cases

| Case | State before write at V | Write | Result |
|------|-------------------------|-------|--------|
| (a) Previously deleted | Latest row: `(V_old, true)` | Insert `(V, false)` | New live row, deletion history preserved |
| (b) Already live in V | Row `(V, false)` exists | Insert `(V, false)` | Upsert, idempotent no-op |
| (c) Live in older version | Latest row: `(V_old, false)` | Insert `(V, false)` | Redundant row, harmless |
| (d) Non-existing | No rows | Insert `(V, false)` | First row for this quad |
| (e) Deleted then re-added in V | Row `(V, true)` exists | Insert `(V, false)` | Upsert flips `is_deleted` to `false` |
| (f) Added then deleted in V | Row `(V, false)` exists | Insert `(V, true)` | Upsert flips `is_deleted` to `true` |

### Query Path

Queries read full entity partitions.  For each quad, determine state
at target version T:

1. Find rows for this quad where `version <= T`.
2. The first such row (highest version, due to DESC ordering) gives
   the state:
   - No matching row → quad does not exist at T.
   - `is_deleted = true` → quad is deleted at T.
   - `is_deleted = false` → quad is live at T.

For current-version queries (the common case), the first row per
quad is always the answer.

The `version` field on query requests is a string.  If it parses as
an integer, it's used directly.  Otherwise it's resolved as a
symbolic name against the cached version log.  This applies to both
the triples service and SPARQL (`?version=baseline`).

**Version filtering requires a specific graph.**  Querying all graphs
(`g=None`) with an explicit version is rejected.  Version numbers and
symbolic names are per-graph — version 3 of one graph and version 3
of another are unrelated timelines, and the same symbolic name may
resolve to different version numbers in different graphs.  Applying a
single version across all graphs is confusing and unlikely to produce
the intended result.

A collection-level "version package" — a recorded snapshot of
`{named_graph: version}` across all graphs at a point in time — would
be the right way to address whole-collection point-in-time queries.
The use case isn't well enough understood yet to design this, but the
per-graph version infrastructure supports it when the time comes.

### Version Scope

Versions are scoped **per collection per named graph**
(`collection` + `g` column).  Each named graph within a collection
has its own independent version counter.

This is the natural unit: ingestion targets a named graph, so
versioning, diffing and reverting are per-graph operations.

A collection-level snapshot is a recorded mapping of
`{named_graph: version}` at a point in time, enabling whole-collection
point-in-time views and reverts when needed.

In practice a collection will have at most ~100 named graphs.  Most
queries are already scoped to a single named graph, so the version
filter is a single integer comparison.  Whole-collection queries look
up the version map (cached in memory, rarely changes) and filter each
quad against the version for its `g` value.

### Version Tables

Two tables manage version metadata:

```
graph_versions (
    collection      text,
    named_graph     text,
    current_version bigint,
    PRIMARY KEY ((collection), named_graph)
)
```

Current state for each named graph.  One partition per collection,
one row per named graph.  Also serves as the named graph registry
(solves the enumeration gap).  Cached in memory by query services.

```
graph_version_log (
    collection      text,
    named_graph     text,
    version         bigint,
    created_at      timestamp,
    names           set<text>,
    description     text,
    PRIMARY KEY ((collection, named_graph), version)
) WITH CLUSTERING ORDER BY (version DESC)
```

Version history.  The `names` set allows multiple symbolic labels
per version (e.g. "before-q4-reingestion", "baseline") so versions
can be referenced by name rather than number.

| Operation | Table | Action |
|-----------|-------|--------|
| Get current version | `graph_versions` | Read `current_version` for collection + named_graph |
| Get version map | `graph_versions` | Full partition read for collection (cached) |
| Enumerate named graphs | `graph_versions` | Same partition read |
| Bump version | Both | Increment `current_version`, append row to log |
| Label a version | `graph_version_log` | Add name to `names` set on existing row |
| Resolve symbolic name | `graph_version_log` | Scan partition in memory (small) and match against `names` |
| List history | `graph_version_log` | Partition read, newest first |

Creating a new version = one lightweight write to each table.
Zero I/O against the graph data.

### Bootstrapping

When a `(collection, named_graph)` combination is encountered for the
first time — on either write or read — it is auto-registered:
create an entry in `graph_versions` with `current_version = 1` and
append a row to `graph_version_log`.

Auto-initialising on retrieval (not just writes) avoids edge cases
such as trying to label or query a named graph that hasn't been
registered yet.  Any operation that references a named graph
triggers bootstrapping if the entry doesn't exist.

### Operations

**Point-in-time view** — query with version filter set to V instead
of current version.

**Diff between versions V1 and V2** (where V1 < V2):
- Added: quads whose latest row at V2 is `is_deleted = false` and
  whose latest row at V1 is `is_deleted = true` or non-existent.
- Removed: quads whose latest row at V1 is `is_deleted = false` and
  whose latest row at V2 is `is_deleted = true`.

**Revert to version V** — bump to a new version V' and write:
- For quads live at V but not at current: insert `(V', false)`.
- For quads live at current but not at V: insert `(V', true)`.

Revert is non-destructive — it appends new rows at V', preserving
the full history of what happened between V and V'.

Diff and revert must locate which quads changed between two versions.
This requires scanning all entity partitions for the named graph.
For small/medium collections this is acceptable.  For large
collections, a lightweight change-tracking table keyed by
`((collection, named_graph), version)` recording affected entity
keys could avoid full scans.

### Storage

Rows accumulate over time.  A background purge process can collapse
history older than a retention threshold by keeping only the latest
row per quad before the cutoff.

Purge rule: if the latest row before the cutoff has
`is_deleted = true` and no newer rows exist, the row can be deleted
entirely (the quad doesn't exist at or after the cutoff).  If the
latest row before the cutoff has `is_deleted = false`, it must be
kept (or rewritten at the cutoff version) so point-in-time queries
after the cutoff still resolve the quad as live.

### Redundant Writes

Re-ingesting an unchanged quad in a new version creates a redundant
row (`(V, false)` on top of `(V_old, false)`).  This is harmless
but grows storage.  Two mitigation strategies:

- **Delta ingestion**: the ingestion pipeline sends only
  additions and deletions, avoiding redundant writes entirely.
- **Smart client**: before writing, the client reads the current
  state of affected entities and only emits writes where the desired
  state differs from the latest row.  Keeps the storage layer
  append-only while eliminating ~99% of redundant rows on
  full re-ingestion.

## Triples Service Operations

The existing triples query service expands to become the central graph
management API.  A new `operation` field on the request selects the
operation.  Empty/missing = query, for backwards compatibility.

| Operation | Description |
|-----------|-------------|
| *(empty)* | Query triples by pattern (existing behaviour) |
| `write` | Insert triples with `version = current, is_deleted = false` |
| `delete` | Insert deletion markers with `version = current, is_deleted = true` |
| `version-bump` | Increment version for a named graph, return new version |
| `version-list` | List version history for a named graph |
| `version-label` | Set symbolic name on a version |
| `version-map` | Return current version for all named graphs in collection |
| `diff` | Return added/removed triples between two versions |
| `revert` | Restore a named graph to a previous version |
| `purge` | Remove history older than threshold (not implemented initially) |

Request fields vary by operation.  Common fields (`collection`,
`user_context`) apply to all.  Operation-specific fields:

| Field | Used by |
|-------|---------|
| `s`, `p`, `o`, `g`, `limit`, `version` (optional) | query |
| `triples` | write |
| `triples` or `s`, `p`, `o`, `g` | delete (explicit triples or pattern) |
| `named_graph` | version-bump, version-list, version-label, diff, revert |
| `version` | version-label, revert |
| `name` | version-label |
| `v1`, `v2` | diff |

## Triples Write Service

The existing triples write service (flow pipeline consumer) remains
separate from the request/response triples service above.  It needs
one change:

- **Stamp `version`** on every quad written, using the current
  version for the quad's named graph, with `is_deleted = false`.

All writes are blind inserts — no reads, no existence checks.  The
write service stays a simple flow consumer.  Deletion of quads is
handled through the triples service operations above.

## Decisions

- **Version creation is explicit only.**  Versions are created by
  calling `version-bump`.  Ingestion does not automatically create
  versions.  The current version stays current until the user bumps
  it.
- **Version filter is off by default.**  Queries return the current
  state (latest row per quad, `is_deleted = false`).  An optional
  `version` field on the query request enables point-in-time
  filtering when needed.
- **Purge is deferred.**  The `purge` operation is defined in the
  API but returns "not implemented" initially.  Purge mechanics
  (retention thresholds, the cutoff rules described in Storage) are
  specced for a later phase.
- **SPARQL versioning via IRI suffix.**  A named graph IRI with a
  `?version=14` suffix queries that graph at version 14.  No suffix =
  current version.  This uses SPARQL's existing `GRAPH <iri>` syntax
  with no new parameters, and allows different named graphs in the
  same query to be at different versions.  The SPARQL engine strips
  the version suffix from the IRI before resolving the named graph.
  This convention is handled entirely within the SPARQL layer — the
  triples service has its own explicit `version` field on query
  requests and does not parse IRIs.

## Graph Field Semantics

There are two distinct graph-related fields on query requests.  They
serve different purposes and have different type constraints.

### API layer

**`g` (query filter)** — `str | None`.  Follows the same convention as
`s`, `p`, `o`: `None` means "not specified, don't filter on this field."

| Value | Meaning |
|-------|---------|
| `None` | All graphs (wildcard) — same as `s=None` meaning "any subject" |
| `""` | The default graph (a specific graph with an empty-string IRI) |
| `"urn:..."` | A specific named graph |

**`named_graph` (operation target)** — `str`, never `None`.  Identifies
which graph a write, version-bump, diff, revert or delete targets.
`""` is the default graph; a non-empty string is a specific named graph.
Wildcard makes no sense for an operation target — you can't bump "all
graphs" — so `None` is not a valid value and should be rejected.

The two fields never overlap in purpose.  `g` is always a read filter.
`named_graph` is always an operation target.  The only interaction is in
`handle_delete` and `handle_write`, where `named_graph` is the fallback
value for a triple's graph when the triple doesn't carry its own `g`.

### CLI layer

The CLI sits on top of the API and translates user intent into API
semantics.  The `None` vs `""` distinction is meaningful at the API
level but confusing on the command line, where passing an empty string
as an argument is awkward and error-prone.

**Query/retrieval CLIs** (`tg-show-graph`, `tg-query-graph`,
`tg-graph-to-turtle`):

- No `-g` flag → default graph (`g=""` at the API).  Most users
  running a query without flags expect to see the default graph.
- `-g urn:graph:cat` → specific graph (`g="urn:graph:cat"`).
- `--all-graphs` → wildcard (`g=None` at the API).

**Versioning/write CLIs** (`tg-bump-graph-version`,
`tg-delete-triples`, `tg-write-triples`, etc.):

- `-g` defaults to `""` (the default graph) and maps to `named_graph`.
- `-g urn:graph:cat` targets a specific graph.
- No wildcard option — operations always target a specific graph.

The rationale: in RDF the default graph is the graph with an
empty-string name, but exposing `""` as a command-line argument is
confusing.  The CLI avoids the problem by making "default graph" the
default behaviour and providing `--all-graphs` as an explicit opt-in
for the wildcard.

## CLI Commands

New commands:

| Command | Operation | Description |
|---------|-----------|-------------|
| `tg-list-named-graphs` | version-map | List named graphs and their current versions |
| `tg-bump-graph-version` | version-bump | Create a new version for a named graph |
| `tg-list-graph-versions` | version-list | Show version history for a named graph |
| `tg-label-graph-version` | version-label | Set a symbolic name on a version |
| `tg-diff-graph` | diff | Show added/removed triples between two versions |
| `tg-revert-graph` | revert | Restore a named graph to a previous version |
| `tg-delete-triples` | delete | Delete triples by explicit list or pattern |
| `tg-write-triples` | write | Write triples to a named graph |
| `tg-purge-graph-history` | purge | Purge old versions (not implemented initially) |

Updated commands:

| Command | Change |
|---------|--------|
| `tg-query-graph` | Add optional `--version` flag for point-in-time queries |
| `tg-show-graph` | Add optional `--version` flag |
| `tg-graph-to-turtle` | Add optional `--version` flag |

## Migration

This is a breaking change, shipping in TrustGraph 3.0.  The entity
table schema changes (new clustering column `version`, new regular
column `is_deleted`, rename `d` to `g`).  No migration path from
the existing schema is planned — existing graphs will need to be
re-ingested.

## Implementation Stages

**Stage 1 — Schema and version tables.**  New Cassandra schema for the
entity table (`version` clustering column, `is_deleted` regular column,
`d` renamed to `g`).  Create the `graph_versions` and
`graph_version_log` tables.  Bootstrapping logic for new
collection/named-graph combinations.

**Stage 2 — Write path.**  Stamp `version` and `is_deleted = false` on
all writes in the triples write service.  Version-aware
`version-bump` operation.  At this point ingestion works with
versioning but queries ignore it.

**Stage 3 — Query path.**  Version-filtered reads in the triples
query service (optional `version` field, default = current).
`version-map` and `version-list` operations.  `--version` flag on
existing CLI query commands.

**Stage 4 — Version management.**  `version-label`, `diff`, `revert`
operations and their CLI commands.  Delete operations (explicit
triples and pattern-based).

**Stage 5 — SPARQL versioning.**  Parse `?version=` suffix on named
graph IRIs in the SPARQL layer, pass version to the triples service.
Symbolic name resolution.

**Stage 6 (deferred) — Purge.**  Background purge process, retention
thresholds, the cutoff rules described in Storage.

## Open Questions

- Other tables (collection table, embeddings tables, etc.) may need
  versioning in future.  Working decision: this spec applies to the
  entity triplestore only.
