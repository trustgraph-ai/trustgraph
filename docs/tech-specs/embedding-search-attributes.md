---
layout: default
title: "Embedding Search Attributes Technical Specification"
parent: "Tech Specs"
---

# Embedding Search Attributes Technical Specification

## Overview

This specification describes adding optional search attributes to graph
and document embeddings stored in Qdrant. The primary use case is
filtering vector similarity searches by RDF type, so that queries can
combine cosine similarity with property matching.

## Problem Statement

Graph embeddings currently store an IRI and its vector embedding in
Qdrant. Similarity searches return the nearest vectors across all
embeddings regardless of what kind of entity the IRI represents.

This means a search for "renewable energy" might return a mix of
people, organisations, concepts, and documents — all semantically
close in vector space, but representing fundamentally different types
of thing. The caller has no way to restrict results to a specific RDF
type (or any other property) at query time. Filtering after the fact
is wasteful and pushes type-awareness into every consumer of the
search API.

Qdrant supports payload-based filtering natively, meaning metadata
attached to points can be used as filter predicates alongside vector
similarity. Qdrant payloads are schema-free — any JSON key-value pair
can be attached to a point and used in filter queries without
predeclaring fields or creating indexes. The opportunity is to thread
optional attributes through from embedding creation to storage, and
expose them as filters at query time.

## Constraints

- **API and message compatibility**: existing REST API contracts and
  Pulsar message schemas must remain compatible. Callers that do not
  use attributes should work without modification.
- **Store-level breaking changes are acceptable**: changes to what
  gets stored in Qdrant (payload structure, point layout) do not need
  to be backwards compatible.
- **Attributes are optional everywhere**: on APIs, on Pulsar messages,
  and on stored items. Nothing requires attributes to be present.
- **Query behaviour without attributes**: a query that does not specify
  attributes matches on vector similarity only, exactly as today.
- **Query behaviour with attributes**: a query that specifies attributes
  filters on those attributes. If no stored items carry the requested
  attributes, the query returns no results.

## Goals

- **Filterable embeddings**: enable optional metadata attributes on
  graph, document, and row embeddings, stored as Qdrant payloads and
  usable as filter predicates alongside vector similarity search.
- **RDF type filtering**: the primary use case is attaching an RDF type
  to an embedding so that queries can restrict results to entities of a
  specific type.
- **Generic attributes**: the mechanism should support arbitrary
  key-value attributes, not just RDF type, to allow future filtering
  use cases without further schema changes.
- **API compatibility**: existing REST API contracts and Pulsar message
  schemas must remain compatible. Callers that do not use attributes
  should work without modification.
- **Consistent approach**: all three embedding types (graph, document,
  row) should use the same attributes mechanism, providing a uniform
  interface for storing and querying with metadata.
- **Row embeddings refactor**: replace the current ad-hoc payload
  fields and per-schema collection partitioning in row embeddings with
  the generic attributes mechanism.

## Technical Design

### Attributes model

Well-known metadata fields (`chunk_id`, `document_id`, `index_name`,
etc.) remain as named fields on message schemas. This preserves
schema-level contracts: producers must populate them, consumers can
rely on them, and typos are caught at the schema layer.

An additional `attributes` dictionary carries optional, extensible
metadata for future use cases beyond the named fields. Attribute keys
use kebab-case by convention. Values are either a single string or a
list of strings.

Example attributes:

```json
{
  "source": "dbpedia",
  "language": "en"
}
```

On write, the Qdrant point payload is built by merging the named
fields and the attributes dict together. On query, the attributes
dict is used to build Qdrant filter predicates.

Entities with multiple RDF types are stored as a single embedding
point with a list-valued `rdf_type` field. Qdrant supports filtering
against individual elements within array payload values, so a filter
for `http://schema.org/Person` will match a point whose `rdf_type`
list contains that value.

### Provenance fields

All embedding messages carry a `Metadata` object which includes
`id` (the chunk identifier) and `root` (the original source document
identifier, e.g. a PDF). The write services store these as `doc_id`
and `chunk_id` in the Qdrant payload, sourced from `metadata.root`
and `metadata.id` respectively. No new fields are needed on the
message schemas for this — the data is already available.

### Attribute sources

The following extraction stages populate new fields on embeddings:

- **Ontology extraction** (graph embeddings):
  `rdf_type` (named field, list, since RDF entities can have multiple
  types)

- All other stages: no additional fields or attributes expected
  initially

### Pulsar message schemas

#### Graph embeddings

The `EntityContext` message (input to the graph embeddings processor)
gains an optional `attributes` field. Named fields are unchanged:

```
EntityContext:
    entity: Term
    context: str
    chunk_id: str                            # unchanged
    rdf_type: list[str]                      # new, default empty
    attributes: dict[str, str | list[str]]   # new, default empty
```

This changes the interface between the extraction services (schema-free
knowledge extraction, ontology extraction) and the graph embeddings
processor. The ontology extraction service populates `rdf_type`.

The `EntityEmbeddings` message mirrors this:

```
EntityEmbeddings:
    entity: Term
    vector: list[float]
    chunk_id: str                            # unchanged
    rdf_type: list[str]                      # new, default empty
    attributes: dict[str, str | list[str]]   # new, default empty
```

The graph embeddings processor passes attributes through from
`EntityContext` to `EntityEmbeddings` unchanged.

#### Document embeddings

The `Chunk` message (input to the document embeddings processor)
gains an optional `attributes` field. Named fields are unchanged:

```
Chunk:
    metadata: Metadata
    chunk: bytes
    document_id: str                         # unchanged
    attributes: dict[str, str | list[str]]   # new, default empty
```

The `ChunkEmbeddings` message mirrors this:

```
ChunkEmbeddings:
    chunk_id: str                            # unchanged
    vector: list[float]
    attributes: dict[str, str | list[str]]   # new, default empty
```

The document embeddings processor passes attributes through from
`Chunk` to `ChunkEmbeddings` unchanged.

#### Row embeddings

The `RowIndexEmbedding` message gains an optional `attributes` field.
Named fields are unchanged:

```
RowIndexEmbedding:
    index_name: str                          # unchanged
    index_value: list[str]                   # unchanged
    text: str                                # unchanged
    vector: list[float]
    attributes: dict[str, str | list[str]]   # new, default empty
```

The `RowEmbeddings` batching message is unchanged:

```
RowEmbeddings:
    metadata: Metadata
    schema_name: str                         # unchanged
    embeddings: list[RowIndexEmbedding]
```

#### Compatibility

These are all additive changes. Existing producers that do not
populate `attributes` will produce messages with an empty dict,
which downstream consumers handle as "no attributes".

### Query request schemas

`GraphEmbeddingsRequest`, `DocumentEmbeddingsRequest`, and
`RowEmbeddingsRequest` gain an optional `attributes` field for
filtering:

```
GraphEmbeddingsRequest:
    vector: list[float]
    limit: int
    collection: str
    rdf_type: str                             # new, default empty, single IRI
    attributes: dict[str, str | list[str]]   # new, default empty

DocumentEmbeddingsRequest:
    vector: list[float]
    limit: int
    collection: str
    attributes: dict[str, str | list[str]]   # new, default empty

RowEmbeddingsRequest:
    vector: list[float]
    limit: int
    collection: str
    schema_name: str                         # unchanged
    index_name: str | None                   # unchanged
    attributes: dict[str, str | list[str]]   # new, default empty
```

When `rdf_type` and `attributes` are both empty, the query behaves
as today — pure vector similarity. When populated, all filter
conditions are AND'd together:

- `rdf_type` matches any stored point whose `rdf_type` list contains
  the specified IRI.
- Each attribute key-value pair becomes a Qdrant `FieldCondition`
  match predicate.
- Multiple attributes are AND'd — all must match.

### Query response schemas

`EntityMatch`, `ChunkMatch`, and `RowIndexMatch` gain an `attributes`
field so that callers receive stored attributes alongside results.
Named fields are unchanged:

```
EntityMatch:
    entity: Term
    score: float
    rdf_type: list[str]                      # new, default empty
    attributes: dict[str, str | list[str]]   # new, default empty

ChunkMatch:
    chunk_id: str                            # unchanged
    score: float
    attributes: dict[str, str | list[str]]   # new, default empty

RowIndexMatch:
    index_name: str                          # unchanged
    index_value: list[str]                   # unchanged
    text: str                                # unchanged
    score: float
    attributes: dict[str, str | list[str]]   # new, default empty
```

### REST API

The graph embeddings query endpoint gains optional `rdf_type` and
`attributes` properties. The document and row embeddings query
endpoints gain `attributes` only:

```yaml
# Graph embeddings query request (new fields)
rdf_type:
  type: string
  description: Optional RDF type IRI to filter results
  example: "http://schema.org/Person"
attributes:
  type: object
  description: Optional key-value attributes to filter results
  additionalProperties:
    oneOf:
      - type: string
      - type: array
        items:
          type: string
  example:
    source: "dbpedia"
```

Callers that omit these fields get the current behaviour unchanged.

The response schemas gain an `attributes` field on each match item,
alongside the existing fields:

```yaml
# Added to entity match items (alongside entity, score)
# and chunk match items (alongside chunk_id, score)
attributes:
  type: object
  description: Stored attributes for this result
  additionalProperties:
    oneOf:
      - type: string
      - type: array
        items:
          type: string
```

### Qdrant storage

On write, named fields and attributes are merged into the Qdrant
point payload. For example, a graph embedding point payload becomes:

```json
{
  "entity": "http://example.org/JohnSmith",
  "doc_id": "urn:trustgraph:doc:abc123",
  "chunk_id": "urn:trustgraph:chunk:007",
  "rdf_type": ["http://schema.org/Person", "http://schema.org/Author"],
  "source": "dbpedia"
}
```

Here `entity` and `rdf_type` come from named message fields;
`doc_id` and `chunk_id` come from `metadata.root` and `metadata.id`;
`source` comes from the attributes dict.

On query, each attribute key-value pair maps to a Qdrant `Filter`
with `FieldCondition` / `MatchValue` predicates, following the same
pattern used by row embeddings for `index_name` filtering. For
list-valued query attributes, each value in the list becomes a
separate match condition.

On response, the query service splits the payload back into named
fields and attributes based on known field names.

For row embeddings, the current approach of partitioning into separate
Qdrant collections per schema is replaced. Instead, `schema_name` and
`index_name` are stored as payload fields and filtered at query time,
consistent with how other named fields are handled. All row embeddings
for a given workspace/collection/dimension share a single collection.
Separate collections are only needed for different vector dimensions.

Qdrant payloads are schema-free and do not require predeclaring fields
or creating indexes. Any payload field can be used in a filter query
immediately. Payload indexes can be added later as a performance
optimisation for frequently filtered keys.

### Python API and CLI

The Python API client libraries (`GraphEmbeddingsClient`,
`DocumentEmbeddingsClient`, `RowEmbeddingsQueryClient`) and the CLI
must be updated to support the `attributes` parameter on queries.

### TypeScript client libraries (out of repo)

The TypeScript client libraries in the UX repository must be updated
to support attributes on query requests and responses.

### Attribute key conventions

Attribute keys use kebab-case (e.g. `rdf-type`).

Since named fields and attributes are merged into a single Qdrant
payload, attribute keys must not collide with named field keys
(`entity`, `doc_id`, `chunk_id`, `rdf_type`, `index_name`,
`index_value`, `text`, `schema_name`). The write path should reject attributes that use
reserved names.

## Performance Considerations

Payload indexes can be created on frequently filtered payload keys
(e.g. `rdf_type`) to improve query performance. Without an index,
Qdrant performs a payload scan which is functional but slower on large
collections.
