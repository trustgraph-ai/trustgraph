# Extraction Provenance: Subgraph Model

## Problem

Extraction-time provenance currently generates a full reification per
extracted triple: a unique `stmt_uri`, `activity_uri`, and associated
PROV-O metadata for every single knowledge fact.  Processing one chunk
that yields 20 relationships produces ~220 provenance triples on top of
the ~20 knowledge triples — a roughly 10:1 overhead.

This is both expensive (storage, indexing, transmission) and semantically
inaccurate.  Each chunk is processed by a single LLM call that produces
all its triples in one transaction.  The current per-triple model
obscures that by creating the illusion of 20 independent extraction
events.

Additionally, two of the four extraction processors (kg-extract-ontology,
kg-extract-agent) have no provenance at all, leaving gaps in the audit
trail.

## Solution

Replace per-triple reification with a **subgraph model**: one provenance
record per chunk extraction, shared across all triples produced from that
chunk.

### Terminology Change

| Old | New |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
| `tg:reifies` (1:1, identity) | `tg:contains` (1:many, containment) |

### Target Structure

All provenance triples go in the `urn:graph:source` named graph.

```
# Subgraph contains each extracted triple (RDF-star quoted triples)
<subgraph> tg:contains <<s1 p1 o1>> .
<subgraph> tg:contains <<s2 p2 o2>> .
<subgraph> tg:contains <<s3 p3 o3>> .

# Derivation from source chunk
<subgraph> prov:wasDerivedFrom <chunk_uri> .
<subgraph> prov:wasGeneratedBy <activity> .

# Activity: one per chunk extraction
<activity> rdf:type          prov:Activity .
<activity> rdfs:label        "{component_name} extraction" .
<activity> prov:used         <chunk_uri> .
<activity> prov:wasAssociatedWith <agent> .
<activity> prov:startedAtTime "2026-03-13T10:00:00Z" .
<activity> tg:componentVersion "0.25.0" .
<activity> tg:llmModel       "gpt-4" .          # if available
<activity> tg:ontology        <ontology_uri> .   # if available

# Agent: stable per component
<agent> rdf:type   prov:Agent .
<agent> rdfs:label "{component_name}" .
```

### Volume Comparison

For a chunk producing N extracted triples:

| | Old (per-triple) | New (subgraph) |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| Activity triples | ~9 x N | ~9 |
| Agent triples | 2 x N | 2 |
| Statement/subgraph metadata | 2 x N | 2 |
| **Total provenance triples** | **~13N** | **N + 13** |
| **Example (N=20)** | **~260** | **33** |

## Scope

### Processors to Update (existing provenance, per-triple)

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

Currently calls `statement_uri()` + `triple_provenance_triples()` inside
the per-definition loop.

Changes:
- Move `subgraph_uri()` and `activity_uri()` creation before the loop
- Collect `tg:contains` triples inside the loop
- Emit shared activity/agent/derivation block once after the loop

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

Same pattern as definitions.  Same changes.

### Processors to Add Provenance (currently missing)

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

Currently emits triples with no provenance.  Add subgraph provenance
using the same pattern: one subgraph per chunk, `tg:contains` for each
extracted triple.

**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

Currently emits triples with no provenance.  Add subgraph provenance
using the same pattern.

### Shared Provenance Library Changes

**`trustgraph-base/trustgraph/provenance/triples.py`**

- Replace `triple_provenance_triples()` with `subgraph_provenance_triples()`
- New function accepts a list of extracted triples instead of a single one
- Generates one `tg:contains` per triple, shared activity/agent block
- Remove old `triple_provenance_triples()`

**`trustgraph-base/trustgraph/provenance/uris.py`**

- Replace `statement_uri()` with `subgraph_uri()`

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

- Replace `TG_REIFIES` with `TG_CONTAINS`

### Not in Scope

- **kg-extract-topics**: older-style processor, not currently used in
  standard flows
- **kg-extract-rows**: produces rows not triples, different provenance
  model
- **Query-time provenance** (`urn:graph:retrieval`): separate concern,
  already uses a different pattern (question/exploration/focus/synthesis)
- **Document/page/chunk provenance** (PDF decoder, chunker): already uses
  `derived_entity_triples()` which is per-entity, not per-triple — no
  redundancy issue

## Implementation Notes

### Processor Loop Restructure

Before (per-triple, in relationships):
```python
for rel in rels:
    # ... build relationship_triple ...
    stmt_uri = statement_uri()
    prov_triples = triple_provenance_triples(
        stmt_uri=stmt_uri,
        extracted_triple=relationship_triple,
        ...
    )
    triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

After (subgraph):
```python
sg_uri = subgraph_uri()

for rel in rels:
    # ... build relationship_triple ...
    extracted_triples.append(relationship_triple)

prov_triples = subgraph_provenance_triples(
    subgraph_uri=sg_uri,
    extracted_triples=extracted_triples,
    chunk_uri=chunk_uri,
    component_name=default_ident,
    component_version=COMPONENT_VERSION,
    llm_model=llm_model,
    ontology_uri=ontology_uri,
)
triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

### New Helper Signature

```python
def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata
    """
```

### Breaking Change

This is a breaking change to the provenance model.  Provenance has not
been released, so no migration is needed.  The old `tg:reifies` /
`statement_uri` code can be removed outright.

## Vocabulary Reference

The full OWL ontology covering all extraction and query-time classes and predicates is at `specs/ontology/trustgraph.ttl`.
