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

### Table 1: entity_quads

The primary data table. Every entity has a partition containing all quads it participates in.

```sql
CREATE TABLE entity_quads (
    collection    text,          -- Collection/tenant scope (always specified)
    entity        text,          -- The entity this row is about
    role          text,          -- 'S', 'P', 'O', 'G' — how this entity participates
    quad_p        text,          -- Predicate of the quad
    o_type        text,          -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    quad_s        text,          -- Subject of the quad
    quad_o        text,          -- Object of the quad
    quad_d        text,          -- Dataset/graph of the quad
    o_datatype    text,          -- XSD datatype (when o_type = 'L'), e.g. 'xsd:string'
    o_lang        text,          -- Language tag (when o_type = 'L'), e.g. 'en', 'fr'
    PRIMARY KEY ((collection, entity), role, quad_p, o_type, quad_s, quad_o, quad_d)
);
```

**Partition key**: `(collection, entity)` — scoped to collection, one partition per entity.

**Clustering column order rationale**:

1. **role** — most queries start with "where is this entity a subject/object"
2. **quad_p** — next most common filter, "give me all `knows` relationships"
3. **o_type** — enables filtering by URI-valued vs literal-valued relationships
4. **quad_s, quad_o, quad_d** — remaining columns for uniqueness

### Table 2: collection_manifest

Supports collection-level deletion. Provides a manifest of all quads belonging to a collection.

```sql
CREATE TABLE collection_manifest (
    collection    text,
    quad_d        text,
    quad_s        text,
    quad_p        text,
    quad_o        text,
    PRIMARY KEY (collection, quad_d, quad_s, quad_p, quad_o)
);
```

Clustered by dataset first, enabling deletion at either collection or dataset granularity.

## Write Path

For each incoming quad `(D, S, P, O)` within a collection `C`, write **4 rows** to `entity_quads` and **1 row** to `collection_manifest`.

### Example

Given the quad in collection `tenant1`:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: https://example.org/knows
Object:   https://example.org/Bob
```

Write 4 rows to `entity_quads`:

| collection | entity | role | quad_p | o_type | quad_s | quad_o | quad_d |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | G | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Alice | S | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/knows | P | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Bob | O | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |

Write 1 row to `collection_manifest`:

| collection | quad_d | quad_s | quad_p | quad_o |
|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | https://example.org/Alice | https://example.org/knows | https://example.org/Bob |

### Literal Example

For a label triple:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: http://www.w3.org/2000/01/rdf-schema#label
Object:   "Alice Smith" (lang: en)
```

The `o_type` is `'L'`, `o_datatype` is `'xsd:string'`, and `o_lang` is `'en'`. The literal value `"Alice Smith"` is stored in `quad_o`. Only 3 rows are needed in `entity_quads` — no row is written for the literal as entity, since literals are not independently queryable entities.

## Query Patterns

### All 16 DSPO Patterns

In the table below, "Perfect prefix" means the query uses a contiguous prefix of the clustering columns. "Partition scan + filter" means Cassandra reads a slice of one partition and filters in memory — still efficient, just not a pure prefix match.

| # | Known | Lookup entity | Clustering prefix | Efficiency |
|---|---|---|---|---|
| 1 | D,S,P,O | entity=S, role='S', quad_p=P | Full match | Perfect prefix |
| 2 | D,S,P,? | entity=S, role='S', quad_p=P | Filter on D | Partition scan + filter |
| 3 | D,S,?,O | entity=S, role='S' | Filter on D, O | Partition scan + filter |
| 4 | D,?,P,O | entity=O, role='O', quad_p=P | Filter on D | Partition scan + filter |
| 5 | ?,S,P,O | entity=S, role='S', quad_p=P | Filter on O | Partition scan + filter |
| 6 | D,S,?,? | entity=S, role='S' | Filter on D | Partition scan + filter |
| 7 | D,?,P,? | entity=P, role='P' | Filter on D | Partition scan + filter |
| 8 | D,?,?,O | entity=O, role='O' | Filter on D | Partition scan + filter |
| 9 | ?,S,P,? | entity=S, role='S', quad_p=P | — | **Perfect prefix** |
| 10 | ?,S,?,O | entity=S, role='S' | Filter on O | Partition scan + filter |
| 11 | ?,?,P,O | entity=O, role='O', quad_p=P | — | **Perfect prefix** |
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
SELECT * FROM entity_quads
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice';
```

**All outgoing relationships for an entity:**

```sql
SELECT * FROM entity_quads
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S';
```

**Specific predicate for an entity:**

```sql
SELECT * FROM entity_quads
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND quad_p = 'https://example.org/knows';
```

**Label for an entity (specific language):**

```sql
SELECT * FROM entity_quads
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND quad_p = 'http://www.w3.org/2000/01/rdf-schema#label'
AND o_type = 'L';
```

Then filter by `o_lang = 'en'` application-side if needed.

**Only URI-valued relationships (entity-to-entity links):**

```sql
SELECT * FROM entity_quads
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND quad_p = 'https://example.org/knows' AND o_type = 'U';
```

**Reverse lookup — what points to this entity:**

```sql
SELECT * FROM entity_quads
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

1. Read `collection_manifest` for the target collection
2. For each quad, delete the corresponding 4 rows from `entity_quads`
3. Delete the rows from `collection_manifest`

The manifest provides the index needed to locate all rows without a full table scan.

## Migration Path from Multi-Table Model

The entity-centric model can coexist with the existing multi-table model during migration:

1. Deploy `entity_quads` and `collection_manifest` tables alongside existing tables
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
| Object type filtering | Not available | Native (via o_type clustering) |

