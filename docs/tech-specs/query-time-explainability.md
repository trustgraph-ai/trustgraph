# Query-Time Explainability

## Status

Implemented

## Overview

This specification describes how GraphRAG records and communicates explainability data during query execution. The goal is full traceability: from final answer back through selected edges to source documents.

Query-time explainability captures what the GraphRAG pipeline did during reasoning. It connects to extraction-time provenance which records where knowledge graph facts originated.

## Terminology

| Term | Definition |
|------|------------|
| **Explainability** | The record of how a result was derived |
| **Session** | A single GraphRAG query execution |
| **Edge Selection** | LLM-driven selection of relevant edges with reasoning |
| **Provenance Chain** | Path from edge → chunk → page → document |

## Architecture

### Explainability Flow

```
GraphRAG Query
    │
    ├─► Session Activity
    │       └─► Query text, timestamp
    │
    ├─► Retrieval Entity
    │       └─► All edges retrieved from subgraph
    │
    ├─► Selection Entity
    │       └─► Selected edges with LLM reasoning
    │           └─► Each edge links to extraction provenance
    │
    └─► Answer Entity
            └─► Reference to synthesized response (in librarian)
```

### Two-Stage GraphRAG Pipeline

1. **Edge Selection**: LLM selects relevant edges from subgraph, providing reasoning for each
2. **Synthesis**: LLM generates answer from selected edges only

This separation enables explainability - we know exactly which edges contributed.

### Storage

- Explainability triples stored in configurable collection (default: `explainability`)
- Uses PROV-O ontology for provenance relationships
- RDF-star reification for edge references
- Answer content stored in librarian service (not inline - too large)

### Real-Time Streaming

Explainability events stream to client as the query executes:

1. Session created → event emitted
2. Edges retrieved → event emitted
3. Edges selected with reasoning → event emitted
4. Answer synthesized → event emitted

Client receives `explain_id`, `explain_graph`, and `explain_triples` inline
in each explain message. The triples contain the full provenance data for
that step — no follow-up graph query needed. The `explain_id` serves as
the root entity URI within the triples. Data is also written to the
knowledge graph for later audit/analysis.

## URI Structure

All URIs use the `urn:trustgraph:` namespace with UUIDs:

| Entity | URI Pattern |
|--------|-------------|
| Session | `urn:trustgraph:session:{uuid}` |
| Retrieval | `urn:trustgraph:prov:retrieval:{uuid}` |
| Selection | `urn:trustgraph:prov:selection:{uuid}` |
| Answer | `urn:trustgraph:prov:answer:{uuid}` |
| Edge Selection | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## RDF Model (PROV-O)

### Session Activity

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "GraphRAG query session" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "What was the War on Terror?" .
```

### Retrieval Entity

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "Retrieved edges" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### Selection Entity

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "Selected edges" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "This edge establishes the key relationship..." .
```

### Answer Entity

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "GraphRAG answer" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

The `tg:document` references the answer stored in the librarian service.

## Namespace Constants

Defined in `trustgraph-base/trustgraph/provenance/namespaces.py`:

| Constant | URI |
|----------|-----|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## GraphRagResponse Schema

```python
@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False
    explain_id: str | None = None
    explain_graph: str | None = None
    explain_triples: list[Triple] = field(default_factory=list)
    message_type: str = ""  # "chunk" or "explain"
    end_of_session: bool = False
```

### Message Types

| message_type | Purpose |
|--------------|---------|
| `chunk` | Response text (streaming or final) |
| `explain` | Explainability event with inline provenance triples |

### Session Lifecycle

1. Multiple `explain` messages (session, retrieval, selection, answer)
2. Multiple `chunk` messages (streaming response)
3. Final `chunk` with `end_of_session=True`

## Edge Selection Format

LLM returns JSONL with selected edges:

```jsonl
{"id": "edge-hash-1", "reasoning": "This edge shows the key relationship..."}
{"id": "edge-hash-2", "reasoning": "Provides supporting evidence..."}
```

The `id` is a hash of `(labeled_s, labeled_p, labeled_o)` computed by `edge_id()`.

## URI Preservation

### The Problem

GraphRAG displays human-readable labels to the LLM, but explainability needs original URIs for provenance tracing.

### Solution

`get_labelgraph()` returns both:
- `labeled_edges`: List of `(label_s, label_p, label_o)` for LLM
- `uri_map`: Dict mapping `edge_id(labels)` → `(uri_s, uri_p, uri_o)`

When storing explainability data, URIs from `uri_map` are used.

## Provenance Tracing

### From Edge to Source

Selected edges can be traced back to source documents:

1. Query for containing subgraph: `?subgraph tg:contains <<s p o>>`
2. Follow `prov:wasDerivedFrom` chain to root document
3. Each step in chain: chunk → page → document

### Cassandra Quoted Triple Support

The Cassandra query service supports matching quoted triples:

```python
# In get_term_value():
elif term.type == TRIPLE:
    return serialize_triple(term.triple)
```

This enables queries like:
```
?subgraph tg:contains <<http://example.org/s http://example.org/p "value">>
```

## CLI Usage

```bash
tg-invoke-graph-rag --explainable -q "What was the War on Terror?"
```

### Output Format

```
[session] urn:trustgraph:session:abc123

[retrieval] urn:trustgraph:prov:retrieval:abc123

[selection] urn:trustgraph:prov:selection:abc123
    Selected 12 edge(s)
      Edge: (Guantanamo, definition, A detention facility...)
        Reason: Directly connects Guantanamo to the War on Terror
        Source: Chunk 1 → Page 2 → Beyond the Vigilant State

[answer] urn:trustgraph:prov:answer:abc123

Based on the provided knowledge statements...
```

### Features

- Real-time explainability events during query
- Label resolution for edge components via `rdfs:label`
- Source chain tracing via `prov:wasDerivedFrom`
- Label caching to avoid repeated queries

## Files Implemented

| File | Purpose |
|------|---------|
| `trustgraph-base/trustgraph/provenance/uris.py` | URI generators |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | RDF namespace constants |
| `trustgraph-base/trustgraph/provenance/triples.py` | Triple builders |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | GraphRagResponse schema |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` | Core GraphRAG with URI preservation |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` | Service with librarian integration |
| `trustgraph-flow/trustgraph/query/triples/cassandra/service.py` | Quoted triple query support |
| `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py` | CLI with explainability display |

## References

- PROV-O (W3C Provenance Ontology): https://www.w3.org/TR/prov-o/
- RDF-star: https://w3c.github.io/rdf-star/
- Extraction-time provenance: `docs/tech-specs/extraction-time-provenance.md`
