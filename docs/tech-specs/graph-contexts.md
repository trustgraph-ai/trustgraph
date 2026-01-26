# Graph Contexts Technical Specification

## Overview

This specification describes changes to TrustGraph's core graph primitives to
align with RDF 1.2 and support full RDF Dataset semantics. This is a breaking
change for version 2.0.

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
   - Alternative/complementary pattern to triple reification: group related
     facts in a named graph and annotate the graph as a whole
   - The graph IRI can be a subject in statements, e.g.:
     ```
     <graph-source-A> <discoveredOn> "2024-01-15"
     <graph-source-A> <hasVeracity> "high"
     ```

3. **Blank Nodes**
   - Anonymous nodes without a global URI
   - Local scope identifiers
   - Adds complexity around identity and serialization
   - May be needed for certain reification patterns (needs investigation)

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

#### Term (currently named Value)

The `Value` class should potentially be renamed to `Term` or `Node` to better
reflect RDF terminology. A Term can represent:

- **IRI/URI** - A named node/resource
- **Blank Node** - An anonymous node with local scope
- **Literal** - A data value with either:
  - A datatype (XSD type), OR
  - A language tag
- **Quoted Triple** - A triple used as a term (RDF 1.2)

#### Triple / Quad

The `Triple` class may need restructuring to:
- Allow nested triples (for RDF-star quoted triples)
- Support an optional graph context (for named graphs / quads)

### Architecture

TODO: Detail the component changes required.

### APIs

TODO: Document API changes.

### Implementation Details

TODO: Implementation approach.

**Note:** The `Value` class is currently used in ~78 files, so renaming to
`Term` would be a significant but feasible refactor for a 2.0 release.

## Security Considerations

## Performance Considerations

## Testing Strategy

## Migration Plan

## Open Questions

## References
