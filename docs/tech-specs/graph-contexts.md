# Graph Contexts Technical Specification

## Overview

This specification describes changes to TrustGraph's core graph primitives to
align with RDF 1.2 and support full RDF Dataset semantics. This is a breaking
change for the 2.x release series.

### Versioning

- **2.0**: Early adopter release. Core features available, may not be fully
  production-ready.
- **2.1 / 2.2**: Production release. Stability and completeness validated.

Flexibility on maturity is intentional - early adopters can access new
capabilities before all features are production-hardened.

## Goals

The primary goals for this work are to enable metadata about facts/statements:

- **Temporal information**: Associate facts with time metadata
  - When a fact was believed to be true
  - When a fact became true
  - When a fact was discovered to be false

- **Provenance/Sources**: Track which sources support a fact
  - "This fact was supported by source X"
  - Link facts back to their origin documents

- **Veracity/Trust**: Record assertions about truth
  - "Person P asserted this was true"
  - "Person Q claims this is false"
  - Enable trust scoring and conflict detection

**Hypothesis**: Reification (RDF-star / quoted triples) is the key mechanism
to achieve these outcomes, as all require making statements about statements.

## Background

To express "the fact (Alice knows Bob) was discovered on 2024-01-15" or
"source X supports the claim (Y causes Z)", you need to reference an edge
as a thing you can make statements about. Standard triples don't support this.

### Current Limitations

The current `Value` class in `trustgraph-base/trustgraph/schema/core/primitives.py`
can represent:
- URI nodes (`is_uri=True`)
- Literal values (`is_uri=False`)

The `type` field exists but is not used to represent XSD datatypes.

## Technical Design

### RDF Features to Support

#### Core Features (Related to Reification Goals)

These features are directly related to the temporal, provenance, and veracity
goals:

1. **RDF 1.2 Quoted Triples (RDF-star)**
   - Edges that point at other edges
   - A Triple can appear as the subject or object of another Triple
   - Enables statements about statements (reification)
   - Core mechanism for annotating individual facts

2. **RDF Dataset / Named Graphs**
   - Support for multiple named graphs within a dataset
   - Each graph identified by an IRI
   - Moves from triples (s, p, o) to quads (s, p, o, g)
   - Includes a default graph plus zero or more named graphs
   - The graph IRI can be a subject in statements, e.g.:
     ```
     <graph-source-A> <discoveredOn> "2024-01-15"
     <graph-source-A> <hasVeracity> "high"
     ```
   - Note: Named graphs are a separate feature from reification. They have
     uses beyond statement annotation (partitioning, access control, dataset
     organization) and should be treated as a distinct capability.

3. **Blank Nodes** (Limited Support)
   - Anonymous nodes without a global URI
   - Supported for compatibility when loading external RDF data
   - **Limited status**: No guarantees about stable identity after loading
   - Find them via wildcard queries (match by connections, not by ID)
   - Not a first-class feature - don't rely on precise blank node handling

#### Opportunistic Fixes (2.0 Breaking Change)

These features are not directly related to the reification goals but are
valuable improvements to include while making breaking changes:

4. **Literal Datatypes**
   - Properly use the `type` field for XSD datatypes
   - Examples: xsd:string, xsd:integer, xsd:dateTime, etc.
   - Fixes current limitation: cannot represent dates or integers properly

5. **Language Tags**
   - Support for language attributes on string literals (@en, @fr, etc.)
   - Note: A literal has either a language tag OR a datatype, not both
     (except for rdf:langString)
   - Important for AI/multilingual use cases

### Data Models

#### Term (rename from Value)

The `Value` class will be renamed to `Term` to better reflect RDF terminology.
This rename serves two purposes:
1. Aligns naming with RDF concepts (a "Term" can be an IRI, literal, blank
   node, or quoted triple - not just a "value")
2. Forces code review at the breaking change interface - any code still
   referencing `Value` is visibly broken and needs updating

A Term can represent:

- **IRI/URI** - A named node/resource
- **Blank Node** - An anonymous node with local scope
- **Literal** - A data value with either:
  - A datatype (XSD type), OR
  - A language tag
- **Quoted Triple** - A triple used as a term (RDF 1.2)

##### Chosen Approach: Single Class with Type Discriminator

Serialization requirements drive the structure - a type discriminator is needed
in the wire format regardless of the Python representation. A single class with
a type field is the natural fit and aligns with the current `Value` pattern.

Single-character type codes provide compact serialization:

```python
from dataclasses import dataclass

# Term type constants
IRI = "i"      # IRI/URI node
BLANK = "b"    # Blank node
LITERAL = "l"  # Literal value
TRIPLE = "t"   # Quoted triple (RDF-star)

@dataclass
class Term:
    type: str = ""  # One of: IRI, BLANK, LITERAL, TRIPLE

    # For IRI terms (type == IRI)
    iri: str = ""

    # For blank nodes (type == BLANK)
    id: str = ""

    # For literals (type == LITERAL)
    value: str = ""
    datatype: str = ""   # XSD datatype URI (mutually exclusive with language)
    language: str = ""   # Language tag (mutually exclusive with datatype)

    # For quoted triples (type == TRIPLE)
    triple: "Triple | None" = None
```

Usage examples:

```python
# IRI term
node = Term(type=IRI, iri="http://example.org/Alice")

# Literal with datatype
age = Term(type=LITERAL, value="42", datatype="xsd:integer")

# Literal with language tag
label = Term(type=LITERAL, value="Hello", language="en")

# Blank node
anon = Term(type=BLANK, id="_:b1")

# Quoted triple (statement about a statement)
inner = Triple(
    s=Term(type=IRI, iri="http://example.org/Alice"),
    p=Term(type=IRI, iri="http://example.org/knows"),
    o=Term(type=IRI, iri="http://example.org/Bob"),
)
reified = Term(type=TRIPLE, triple=inner)
```

##### Alternatives Considered

**Option B: Union of specialized classes** (`Term = IRI | BlankNode | Literal | QuotedTriple`)
- Rejected: Serialization would still need a type discriminator, adding complexity

**Option C: Base class with subclasses**
- Rejected: Same serialization issue, plus dataclass inheritance quirks

#### Triple / Quad

The `Triple` class gains an optional graph field to become a quad:

```python
@dataclass
class Triple:
    s: Term | None = None    # Subject
    p: Term | None = None    # Predicate
    o: Term | None = None    # Object
    g: str | None = None     # Graph name (IRI), None = default graph
```

Design decisions:
- **Field name**: `g` for consistency with `s`, `p`, `o`
- **Optional**: `None` means the default graph (unnamed)
- **Type**: Plain string (IRI) rather than Term
  - Graph names are always IRIs
  - Blank nodes as graph names ruled out (too confusing)
  - No need for the full Term machinery

Note: The class name stays `Triple` even though it's technically a quad now.
This avoids churn and "triple" is still the common terminology for the s/p/o
portion. The graph context is metadata about where the triple lives.

### Candidate Query Patterns

The current query engine accepts combinations of S, P, O terms. With quoted
triples, a triple itself becomes a valid term in those positions. Below are
candidate query patterns that support the original goals.

#### Graph Parameter Semantics

Following SPARQL conventions for backward compatibility:

- **`g` omitted / None**: Query the default graph only
- **`g` = specific IRI**: Query that named graph only
- **`g` = wildcard / `*`**: Query across all graphs (equivalent to SPARQL
  `GRAPH ?g { ... }`)

This keeps simple queries simple and makes named graph queries opt-in.

Cross-graph queries (g=wildcard) are fully supported. The Cassandra schema
includes dedicated tables (SPOG, POSG, OSPG) where g is a clustering column
rather than a partition key, enabling efficient queries across all graphs.

#### Temporal Queries

**Find all facts discovered after a given date:**
```
S: ?                                    # any quoted triple
P: <discoveredOn>
O: > "2024-01-15"^^xsd:date             # date comparison
```

**Find when a specific fact was believed true:**
```
S: << <Alice> <knows> <Bob> >>          # quoted triple as subject
P: <believedTrueFrom>
O: ?                                    # returns the date
```

**Find facts that became false:**
```
S: ?                                    # any quoted triple
P: <discoveredFalseOn>
O: ?                                    # has any value (exists)
```

#### Provenance Queries

**Find all facts supported by a specific source:**
```
S: ?                                    # any quoted triple
P: <supportedBy>
O: <source:document-123>
```

**Find which sources support a specific fact:**
```
S: << <DrugA> <treats> <DiseaseB> >>    # quoted triple as subject
P: <supportedBy>
O: ?                                    # returns source IRIs
```

#### Veracity Queries

**Find assertions a person marked as true:**
```
S: ?                                    # any quoted triple
P: <assertedTrueBy>
O: <person:Alice>
```

**Find conflicting assertions (same fact, different veracity):**
```
# First query: facts asserted true
S: ?
P: <assertedTrueBy>
O: ?

# Second query: facts asserted false
S: ?
P: <assertedFalseBy>
O: ?

# Application logic: find intersection of subjects
```

**Find facts with trust score below threshold:**
```
S: ?                                    # any quoted triple
P: <trustScore>
O: < 0.5                                # numeric comparison
```

### Architecture

Significant changes required across multiple components:

#### This Repository (trustgraph)

- **Schema primitives** (`trustgraph-base/trustgraph/schema/core/primitives.py`)
  - Value → Term rename
  - New Term structure with type discriminator
  - Triple gains `g` field for graph context

- **Message translators** (`trustgraph-base/trustgraph/messaging/translators/`)
  - Update for new Term/Triple structures
  - Serialization/deserialization for new fields

- **Gateway components**
  - Handle new Term and quad structures

- **Knowledge cores**
  - Core changes to support quads and reification

- **Knowledge manager**
  - Schema changes propagate here

- **Storage layers**
  - Cassandra: Schema redesign (see Implementation Details)
  - Other backends: Deferred to later phases

- **Command-line utilities**
  - Update for new data structures

- **REST API documentation**
  - OpenAPI spec updates

#### External Repositories

- **Python API** (this repo)
  - Client library updates for new structures

- **TypeScript APIs** (separate repo)
  - Client library updates

- **Workbench** (separate repo)
  - Significant state management changes

### APIs

#### REST API

- Documented in OpenAPI spec
- Will need updates for new Term/Triple structures
- New endpoints may be needed for graph context operations

#### Python API (this repo)

- Client library changes to match new primitives
- Breaking changes to Term (was Value) and Triple

#### TypeScript API (separate repo)

- Parallel changes to Python API
- Separate release coordination

#### Workbench (separate repo)

- Significant state management changes
- UI updates for graph context features

### Implementation Details

#### Phased Storage Implementation

Multiple graph store backends exist (Cassandra, Neo4j, etc.). Implementation
will proceed in phases:

1. **Phase 1: Cassandra**
   - Start with the home-grown Cassandra store
   - Full control over the storage layer enables rapid iteration
   - Schema will be redesigned from scratch for quads + reification
   - Validate the data model and query patterns against real use cases

#### Cassandra Schema Design

Cassandra requires multiple tables to support different query access patterns
(each table efficiently queries by its partition key + clustering columns).

##### Query Patterns

With quads (g, s, p, o), each position can be specified or wildcard, giving
16 possible query patterns:

| # | g | s | p | o | Description |
|---|---|---|---|---|-------------|
| 1 | ? | ? | ? | ? | All quads |
| 2 | ? | ? | ? | o | By object |
| 3 | ? | ? | p | ? | By predicate |
| 4 | ? | ? | p | o | By predicate + object |
| 5 | ? | s | ? | ? | By subject |
| 6 | ? | s | ? | o | By subject + object |
| 7 | ? | s | p | ? | By subject + predicate |
| 8 | ? | s | p | o | Full triple (which graphs?) |
| 9 | g | ? | ? | ? | By graph |
| 10 | g | ? | ? | o | By graph + object |
| 11 | g | ? | p | ? | By graph + predicate |
| 12 | g | ? | p | o | By graph + predicate + object |
| 13 | g | s | ? | ? | By graph + subject |
| 14 | g | s | ? | o | By graph + subject + object |
| 15 | g | s | p | ? | By graph + subject + predicate |
| 16 | g | s | p | o | Exact quad |

##### Table Design

Cassandra constraint: You can only efficiently query by partition key, then
filter on clustering columns left-to-right. For g-wildcard queries, g must be
a clustering column. For g-specified queries, g in the partition key is more
efficient.

**Two table families needed:**

**Family A: g-wildcard queries** (g in clustering columns)

| Table | Partition | Clustering | Supports patterns |
|-------|-----------|------------|-------------------|
| SPOG | (user, collection, s) | p, o, g | 5, 7, 8 |
| POSG | (user, collection, p) | o, s, g | 3, 4 |
| OSPG | (user, collection, o) | s, p, g | 2, 6 |

**Family B: g-specified queries** (g in partition key)

| Table | Partition | Clustering | Supports patterns |
|-------|-----------|------------|-------------------|
| GSPO | (user, collection, g, s) | p, o | 9, 13, 15, 16 |
| GPOS | (user, collection, g, p) | o, s | 11, 12 |
| GOSP | (user, collection, g, o) | s, p | 10, 14 |

**Collection table** (for iteration and bulk deletion)

| Table | Partition | Clustering | Purpose |
|-------|-----------|------------|---------|
| COLL | (user, collection) | g, s, p, o | Enumerate all quads in collection |

##### Write and Delete Paths

**Write path**: Insert into all 7 tables.

**Delete collection path**:
1. Iterate COLL table for `(user, collection)`
2. For each quad, delete from all 6 query tables
3. Delete from COLL table (or range delete)

**Delete single quad path**: Delete from all 7 tables directly.

##### Storage Cost

Each quad is stored 7 times. This is the cost of flexible querying combined
with efficient collection deletion.

##### Quoted Triples in Storage

Subject or object can be a triple itself. Options:

**Option A: Serialize quoted triples to canonical string**
```
S: "<<http://ex/Alice|http://ex/knows|http://ex/Bob>>"
P: http://ex/discoveredOn
O: "2024-01-15"
G: null
```
- Store quoted triple as serialized string in S or O columns
- Query by exact match on serialized form
- Pro: Simple, fits existing index patterns
- Con: Can't query "find triples where quoted subject's predicate is X"

**Option B: Triple IDs / Hashes**
```
Triple table:
  id: hash(s,p,o,g)
  s, p, o, g: ...

Metadata table:
  subject_triple_id: <hash>
  p: http://ex/discoveredOn
  o: "2024-01-15"
```
- Assign each triple an ID (hash of components)
- Reification metadata references triples by ID
- Pro: Clean separation, can index triple IDs
- Con: Requires computing/managing triple identity, two-phase lookups

**Recommendation**: Start with Option A (serialized strings) for simplicity.
Option B may be needed if advanced query patterns over quoted triple
components are required.

2. **Phase 2+: Other Backends**
   - Neo4j and other stores implemented in subsequent stages
   - Lessons learned from Cassandra inform these implementations

This approach de-risks the design by validating on a fully-controlled backend
before committing to implementations across all stores.

#### Value → Term Rename

The `Value` class will be renamed to `Term`. This affects ~78 files across
the codebase. The rename acts as a forcing function: any code still using
`Value` is immediately identifiable as needing review/update for 2.0
compatibility.

## Security Considerations

Named graphs are not a security feature. Users and collections remain the
security boundaries. Named graphs are purely for data organization and
reification support.

## Performance Considerations

- Quoted triples add nesting depth - may impact query performance
- Named graph indexing strategies needed for efficient graph-scoped queries
- Cassandra schema design will need to accommodate quad storage efficiently

### Vector Store Boundary

Vector stores always reference IRIs only:
- Never edges (quoted triples)
- Never literal values
- Never blank nodes

This keeps the vector store simple - it handles semantic similarity of named
entities. The graph structure handles relationships, reification, and metadata.
Quoted triples and named graphs don't complicate vector operations.

## Testing Strategy

Use existing test strategy. As this is a breaking change, extensive focus on
the end-to-end test suite to validate the new structures work correctly across
all components.

## Migration Plan

- 2.0 is a breaking release; no backward compatibility required
- Existing data may need migration to new schema (TBD based on final design)
- Consider migration tooling for converting existing triples

## Open Questions

- **Blank nodes**: Limited support confirmed. May need to decide on
  skolemization strategy (generate IRIs on load, or preserve blank node IDs).
- **Query syntax**: What is the concrete syntax for specifying quoted triples
  in queries? Need to define the query API.
- ~~**Predicate vocabulary**~~: Resolved. Any valid RDF predicates permitted,
  including custom user-defined. Minimal assumptions about RDF validity.
  Very few locked-in values (e.g., `rdfs:label` used in some places).
  Strategy: avoid locking anything in unless absolutely necessary.
- ~~**Vector store impact**~~: Resolved. Vector stores always point to IRIs
  only - never edges, literals, or blank nodes. Quoted triples and
  reification don't affect the vector store.
- ~~**Named graph semantics**~~: Resolved. Queries default to the default
  graph (matches SPARQL behavior, backward compatible). Explicit graph
  parameter required to query named graphs or all graphs.

## References

- [RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)
- [RDF-star and SPARQL-star](https://w3c.github.io/rdf-star/)
- [RDF Dataset](https://www.w3.org/TR/rdf11-concepts/#section-dataset)
