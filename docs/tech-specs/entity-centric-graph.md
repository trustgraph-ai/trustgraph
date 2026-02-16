# Entity-Centric Knowledge Graph Storage on Cassandra

## Overview

This document describes a storage model for RDF-style knowledge graphs on Apache Cassandra. The model uses an **entity-centric** approach where every entity knows every quad it participates in and the role it plays. This replaces a traditional multi-table SPO permutation approach with just two tables.

## Background and Motivation

### The Traditional Approach

A standard RDF quad store on Cassandra requires multiple denormalised tables to cover query patterns — typically 6 or more tables representing different permutations of Subject, Predicate, Object, and Dataset (SPOD). Each quad is written to every table, resulting in significant write amplification, operational overhead, and schema complexity.

Additionally, label resolution (fetching human-readable names for entities) requires separate round-trip queries, which is particularly costly in AI and GraphRAG use cases where labels are essential for LLM context.

### The Entity-Centric Insight

Every quad `(D, S, P, O)` involves up to 4 entities. By writing a row for each entity's participation in the quad, we guarantee that **any query with at least one known element will hit a partition key**. This covers all 16 query patterns with a single data table.

Key benefits:

- **2 tables** instead of 7+
- **4 writes per quad** instead of 6+
- **Label resolution for free** — an entity's labels are co-located with its relationships, naturally warming the application cache
- **All 16 query patterns** served by single-partition reads
- **Simpler operations** — one data table to tune, compact, and repair

## Schema

### Table 1: quads_by_entity

The primary data table. Every entity has a partition containing all quads it participates in. Named to reflect the query pattern (lookup by entity).

```sql
CREATE TABLE quads_by_entity (
    collection text,       -- Collection/tenant scope (always specified)
    entity     text,       -- The entity this row is about
    role       text,       -- 'S', 'P', 'O', 'G' — how this entity participates
    p          text,       -- Predicate of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    s          text,       -- Subject of the quad
    o          text,       -- Object of the quad
    d          text,       -- Dataset/graph of the quad
    dtype      text,       -- XSD datatype (when otype = 'L'), e.g. 'xsd:string'
    lang       text,       -- Language tag (when otype = 'L'), e.g. 'en', 'fr'
    PRIMARY KEY ((collection, entity), role, p, otype, s, o, d)
);
```

**Partition key**: `(collection, entity)` — scoped to collection, one partition per entity.

**Clustering column order rationale**:

1. **role** — most queries start with "where is this entity a subject/object"
2. **p** — next most common filter, "give me all `knows` relationships"
3. **otype** — enables filtering by URI-valued vs literal-valued relationships
4. **s, o, d** — remaining columns for uniqueness

### Table 2: quads_by_collection

Supports collection-level queries and deletion. Provides a manifest of all quads belonging to a collection. Named to reflect the query pattern (lookup by collection).

```sql
CREATE TABLE quads_by_collection (
    collection text,
    d          text,       -- Dataset/graph of the quad
    s          text,       -- Subject of the quad
    p          text,       -- Predicate of the quad
    o          text,       -- Object of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    dtype      text,       -- XSD datatype (when otype = 'L')
    lang       text,       -- Language tag (when otype = 'L')
    PRIMARY KEY (collection, d, s, p, o)
);
```

Clustered by dataset first, enabling deletion at either collection or dataset granularity.

## Write Path

For each incoming quad `(D, S, P, O)` within a collection `C`, write **4 rows** to `quads_by_entity` and **1 row** to `quads_by_collection`.

### Example

Given the quad in collection `tenant1`:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: https://example.org/knows
Object:   https://example.org/Bob
```

Write 4 rows to `quads_by_entity`:

| collection | entity | role | p | otype | s | o | d |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | G | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Alice | S | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/knows | P | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Bob | O | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |

Write 1 row to `quads_by_collection`:

| collection | d | s | p | o | otype | dtype | lang |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | https://example.org/Alice | https://example.org/knows | https://example.org/Bob | U | | |

### Literal Example

For a label triple:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: http://www.w3.org/2000/01/rdf-schema#label
Object:   "Alice Smith" (lang: en)
```

The `otype` is `'L'`, `dtype` is `'xsd:string'`, and `lang` is `'en'`. The literal value `"Alice Smith"` is stored in `o`. Only 3 rows are needed in `quads_by_entity` — no row is written for the literal as entity, since literals are not independently queryable entities.

## Query Patterns

### All 16 DSPO Patterns

In the table below, "Perfect prefix" means the query uses a contiguous prefix of the clustering columns. "Partition scan + filter" means Cassandra reads a slice of one partition and filters in memory — still efficient, just not a pure prefix match.

| # | Known | Lookup entity | Clustering prefix | Efficiency |
|---|---|---|---|---|
| 1 | D,S,P,O | entity=S, role='S', p=P | Full match | Perfect prefix |
| 2 | D,S,P,? | entity=S, role='S', p=P | Filter on D | Partition scan + filter |
| 3 | D,S,?,O | entity=S, role='S' | Filter on D, O | Partition scan + filter |
| 4 | D,?,P,O | entity=O, role='O', p=P | Filter on D | Partition scan + filter |
| 5 | ?,S,P,O | entity=S, role='S', p=P | Filter on O | Partition scan + filter |
| 6 | D,S,?,? | entity=S, role='S' | Filter on D | Partition scan + filter |
| 7 | D,?,P,? | entity=P, role='P' | Filter on D | Partition scan + filter |
| 8 | D,?,?,O | entity=O, role='O' | Filter on D | Partition scan + filter |
| 9 | ?,S,P,? | entity=S, role='S', p=P | — | **Perfect prefix** |
| 10 | ?,S,?,O | entity=S, role='S' | Filter on O | Partition scan + filter |
| 11 | ?,?,P,O | entity=O, role='O', p=P | — | **Perfect prefix** |
| 12 | D,?,?,? | entity=D, role='G' | — | **Perfect prefix** |
| 13 | ?,S,?,? | entity=S, role='S' | — | **Perfect prefix** |
| 14 | ?,?,P,? | entity=P, role='P' | — | **Perfect prefix** |
| 15 | ?,?,?,O | entity=O, role='O' | — | **Perfect prefix** |
| 16 | ?,?,?,? | — | Full scan | Exploration only |

**Key result**: 7 of the 15 non-trivial patterns are perfect clustering prefix hits. The remaining 8 are single-partition reads with in-partition filtering. Every query with at least one known element hits a partition key.

Pattern 16 (?,?,?,?) does not occur in practice since collection is always specified, reducing it to pattern 12.

### Common Query Examples

**Everything about an entity:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice';
```

**All outgoing relationships for an entity:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S';
```

**Specific predicate for an entity:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows';
```

**Label for an entity (specific language):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'http://www.w3.org/2000/01/rdf-schema#label'
AND otype = 'L';
```

Then filter by `lang = 'en'` application-side if needed.

**Only URI-valued relationships (entity-to-entity links):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows' AND otype = 'U';
```

**Reverse lookup — what points to this entity:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Bob'
AND role = 'O';
```

## Label Resolution and Cache Warming

One of the most significant advantages of the entity-centric model is that **label resolution becomes a free side effect**.

In the traditional multi-table model, fetching labels requires separate round-trip queries: retrieve triples, identify entity URIs in the results, then fetch `rdfs:label` for each. This N+1 pattern is expensive.

In the entity-centric model, querying an entity returns **all** its quads — including its labels, types, and other properties. When the application caches query results, labels are pre-warmed before anything asks for them.

Two usage regimes confirm this works well in practice:

- **Human-facing queries**: naturally small result sets, labels essential. Entity reads pre-warm the cache.
- **AI/bulk queries**: large result sets with hard limits. Labels either unnecessary or needed only for a curated subset of entities already in cache.

The theoretical concern of resolving labels for huge result sets (e.g. 30,000 entities) is mitigated by the practical observation that no human or AI consumer usefully processes that many labels. Application-level query limits ensure cache pressure remains manageable.

## Wide Partitions and Reification

Reification (RDF-star style statements about statements) creates hub entities — e.g. a source document that supports thousands of extracted facts. This can produce wide partitions.

Mitigating factors:

- **Application-level query limits**: all GraphRAG and human-facing queries enforce hard limits, so wide partitions are never fully scanned on the hot read path
- **Cassandra handles partial reads efficiently**: a clustering column scan with an early stop is fast even on large partitions
- **Collection deletion** (the only operation that might traverse full partitions) is an accepted background process

## Collection Deletion

Triggered by API call, runs in the background (eventually consistent).

1. Read `quads_by_collection` for the target collection to get all quads
2. Extract unique entities from the quads (s, p, o, d values)
3. For each unique entity, delete the partition from `quads_by_entity`
4. Delete the rows from `quads_by_collection`

The `quads_by_collection` table provides the index needed to locate all entity partitions without a full table scan. Partition-level deletes are efficient since `(collection, entity)` is the partition key.

## Migration Path from Multi-Table Model

The entity-centric model can coexist with the existing multi-table model during migration:

1. Deploy `quads_by_entity` and `quads_by_collection` tables alongside existing tables
2. Dual-write new quads to both old and new tables
3. Backfill existing data into the new tables
4. Migrate read paths one query pattern at a time
5. Decommission old tables once all reads are migrated

## Summary

| Aspect | Traditional (6-table) | Entity-centric (2-table) |
|---|---|---|
| Tables | 7+ | 2 |
| Writes per quad | 6+ | 5 (4 data + 1 manifest) |
| Label resolution | Separate round trips | Free via cache warming |
| Query patterns | 16 across 6 tables | 16 on 1 table |
| Schema complexity | High | Low |
| Operational overhead | 6 tables to tune/repair | 1 data table |
| Reification support | Additional complexity | Natural fit |
| Object type filtering | Not available | Native (via otype clustering) |

