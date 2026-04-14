---
layout: default
title: "Ontology Analytics Service Technical Specification"
parent: "Tech Specs"
---

# Ontology Analytics Service Technical Specification

## Overview

This specification proposes extracting ontology analytics — the embedding,
vector storage, and similarity-based selection of ontology elements — out of
`kg-extract-ontology` and into a separate, reusable service. The goal is to
make ontology analytics available to processors other than the extractor,
preload the analytics state at ontology-load time rather than on-demand, and
simplify the current per-flow duplication of vector stores.

## Problem Statement

The current implementation in `kg-extract-ontology`
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`) embeds
ontology analytics inside a single processor. This has four concrete
problems:

1. **Analytics are locked inside one processor.** Other services that
   could benefit from ontology-similarity lookups (e.g. relationship
   extraction, agent tool selection, query routing, future features that
   don't exist yet) have no way to call into the analytics without
   duplicating the embedder/vector store/selector machinery. The
   extractor owns state that conceptually belongs to the platform.

2. **Vector stores are built lazily, per-flow, on first message.** Each
   flow that uses `kg-extract-ontology` gets its own
   `{embedder, vector_store, selector}` triple, keyed by `id(flow)`, and
   the vector store is only populated the first time a message arrives
   on that flow. This has several consequences:

   - **Cold-start cost on the hot path.** The first document chunk
     processed by a flow pays the full cost of embedding every element
     of the ontology (hundreds to thousands of calls to the embeddings
     service) before extraction can even begin. Subsequent chunks are
     fast, but the first one can take seconds to minutes depending on
     ontology size.
   - **N copies of the same data.** If three flows all use the same
     embedding model and the same ontology, three identical in-memory
     vector stores are built and maintained. Memory scales with the
     number of flows, not the number of ontologies.
   - **Total loss on restart.** Vector stores are `InMemoryVectorStore`
     instances — nothing is persisted. A restart forces every flow to
     re-embed the entire ontology on its next message.
   - **Ontology updates re-embed everything.** When the ontology config
     changes, `flow_components` is cleared and the re-embedding happens
     lazily across every flow, again on the hot path.

   The per-flow split exists for a real reason: different flows may use
   different embedding models with different vector dimensions, and the
   current code detects the dimension by probing the flow's embeddings
   service with a test string. But in practice most deployments use one
   embedding model, and the per-flow split is paying a cost for
   flexibility that isn't being used.

3. **Per-message selection is not batched.** For every document chunk
   processed, the selector calls `embedder.embed_text(segment.text)`
   once per segment (`ontology_selector.py:96`), each of which
   round-trips through the pub/sub layer to the embeddings service as a
   single-element batch. A chunk with 20 segments fires 20 sequential
   embeddings requests when it could fire one. Ontology ingest is
   already batched at 50 at a time; per-message lookups are not.

4. **There is no way to scope ontologies to a flow.** All loaded
   ontologies are visible to all flows. A flow that only cares about,
   say, the FIBO ontology still pays for embedding and similarity search
   across every unrelated ontology in config. This is a usability and
   performance problem that gets worse as the number of loaded
   ontologies grows.

Together these problems mean the current implementation is tightly
coupled, duplicates work across flows, pays its worst costs on the
hot path, and can't be reused. Each of the four goals below addresses
one of these problems directly.

## Goals

- **Eager ontology processing.** When an ontology is loaded (via config
  push), embed it and populate the vector store immediately, before any
  document processing messages arrive. First-chunk latency should not
  include ontology embedding cost.

- **Simplify away from per-flow analytics.** Move the vector store out
  of per-flow scope. Revisit whether per-flow dimension detection is
  still necessary, or whether a shared analytics store (per embedding
  model, or globally) is sufficient for realistic deployments.

- **Extract ontology analytics into a standalone service.** Expose
  embedding, similarity search, and ontology-subset selection as a
  service callable from any processor via the normal pub/sub
  request/response pattern. `kg-extract-ontology` becomes one consumer
  among many.

- **(Stretch)** Allow flows to select which ontologies they use when
  the flow is started, so a flow can restrict itself to a named subset
  of the loaded ontologies rather than seeing all of them.

## Background

The current ontology analytics live in four files under
`trustgraph-flow/trustgraph/extract/kg/ontology/`:

- `ontology_loader.py` — parses ontology definitions from config.
- `ontology_embedder.py` — generates embeddings for ontology elements
  and stores them in an `InMemoryVectorStore`. Batches at 50 elements
  per call on ingest.
- `vector_store.py` — `InMemoryVectorStore`, a numpy-backed dense vector
  store with similarity search.
- `ontology_selector.py` — given a query (a document segment), returns
  the top-K most relevant ontology elements via similarity search.

These are wired together inside `extract.py`, where `Processor` holds
one `OntologyLoader` and one `TextProcessor` but maintains a
`flow_components` dict mapping `id(flow) →
{embedder, vector_store, selector}`. `initialize_flow_components` is
called on the first message for each flow; ontology config changes
trigger `self.flow_components.clear()` to force re-initialisation.

The analytics stack is conceptually independent from the extractor —
it's just a "given text, find relevant ontology elements" service —
but because it's embedded in the extractor, no other processor can use
it, and its lifecycle is coupled to message processing rather than to
ontology loading.

## Technical Design

### Architecture

A new processor, tentatively `ontology-analytics`, hosts the embedder,
vector store, and selector. It is a `FlowProcessor` — flow-aware so
future per-user state management can hook in at the flow boundary —
but the analytics state it holds is **global to the process**, not
per-flow. Shared state is the default; flow scope is just a handle
available when needed.

Crucially, the service does **not** call a separate embeddings service
for its own embedding work. It loads and runs an embedding model
directly, in-process, the same way `embeddings-fastembed` does today.
The rationale: the embedding model used for ontology analytics is a
deployment choice driven by the ontology's semantics, not by the
user's document embedding model. Coupling the two would be an
accidental constraint. Decoupling means:

- The analytics service has no dependency on a flow's
  `embeddings-request` service. No routing, no external call, no
  async dependency on another processor being up.
- Ontology ingest happens synchronously in the analytics process as
  soon as the ontology config is loaded. No round-trips.
- Per-message selection (embedding a query segment and searching the
  vector store) is also local. Fast path, no pub/sub hop for
  embedding.
- Most deployments will use a single embedding model configured on
  the analytics service. If a deployment needs two, run two
  `ontology-analytics` processor instances with different ids and
  have flows address the one they want.

The flow configuration optionally specifies which analytics service
id to use and which ontologies the flow cares about; otherwise the
flow sees all loaded ontologies through the default analytics
service.

Components inside the new processor:

1. **OntologyLoader** (moved from `kg-extract-ontology`)
   Parses ontologies from config-push messages. Owns the parsed
   ontology objects.

2. **In-process embedding model**
   Loaded once at startup using the service's configured model name.
   Same pattern as `embeddings-fastembed` — direct library call,
   batched.

3. **Vector store (global)**
   One `InMemoryVectorStore` per loaded ontology, not per flow.
   Populated eagerly when the ontology is loaded (or reloaded).
   Lives in process memory for the lifetime of the service.

4. **Selector**
   Given a query text and a subset of ontology ids, returns the
   top-K most relevant ontology elements across the union of those
   stores. Batches embedding calls for multi-segment queries.

5. **Request handler**
   Exposes a request/response service over the pub/sub layer for
   other processors (initially `kg-extract-ontology`, later
   others) to call.

Module: `trustgraph-flow/trustgraph/ontology_analytics/` (new)

### Data Models

#### Service request

```
OntologyAnalyticsRequest {
    query_texts: list[str]         # batch of query segments
    ontology_ids: list[str] | None # optional subset; None = all
    top_k: int                     # default per-service
    similarity_threshold: float    # default per-service
}
```

#### Service response

```
OntologyAnalyticsResponse {
    results: list[list[OntologyMatch]]  # one list per query_text
}

OntologyMatch {
    element_id: str        # e.g. "fibo:Bond"
    element_type: str      # class | property | individual
    ontology_id: str       # which ontology it came from
    text: str              # the text that was embedded
    score: float           # similarity score
}
```

The request is a batch by construction: the caller sends a list of
segments, the service embeds them in one batched embedding call,
searches the relevant stores, and returns a list of match-lists
aligned with the input. This directly fixes the per-segment
unbatched call in the current selector.

#### Flow configuration

Flow instance config gains an optional `ontology_analytics` block:

```
ontology_analytics:
  service_id: ontology-analytics   # default
  ontologies: [fibo, geonames]     # default: all loaded
```

If omitted, flows use the default analytics service id and see every
loaded ontology.

### APIs

New services:
- `ontology-analytics` request/response service, schema as above.

New flow service client:
- `flow("ontology-analytics-request")` — standard flow-scoped client
  wrapper for calling the analytics service.

Modified code paths:
- `kg-extract-ontology` no longer owns the embedder, vector store,
  or selector. Its per-message logic calls
  `flow("ontology-analytics-request")` with the segments extracted
  from the chunk and gets back the same shape of data it used to
  compute locally.
- The `on_ontology_config` handler in `kg-extract-ontology` goes
  away; config-push of ontology types is handled by the new
  service.

### Implementation Details

- **Eager ingest.** When `on_ontology_config` fires on the analytics
  service, the service synchronously (well, in an asyncio task)
  re-embeds the changed ontologies and atomically swaps the new
  vector stores in. Per-ontology granularity — unchanged ontologies
  are not re-embedded.
- **Ontology updates as cutover.** Once a new ontology version is
  swapped in, all subsequent requests see the new state. In-flight
  requests complete against whichever version they started reading.
  No version pinning; callers who care take responsibility.
- **Shared vs flow state.** The processor keeps a flow dict for
  future per-user additions but the vector stores themselves are
  module-level (on `self`, not on per-flow state). The flow is only
  used to find the caller's `ontology_analytics` config block for
  this request.
- **Batching.** Both ontology ingest and per-request query embedding
  use the in-process embedder's batched interface. No per-element
  round-trips anywhere on the hot path.

## Security Considerations

*(To be filled in.)*

## Performance Considerations

*(To be filled in — but note up front that batching per-message
selector calls is an easy pre-existing win that doesn't require the
new service, and should probably land separately first.)*

## Testing Strategy

*(To be filled in.)*

## Migration Plan

*(To be filled in — needs to cover how `kg-extract-ontology`
transitions from owning the analytics to calling a new service, and
what happens to in-flight flows during the rollover.)*

## Resolved Questions

- **Persistence:** in-memory only. Ontology data is small, restart
  cost is acceptable, and adding a storage backend (Qdrant, local
  file, etc.) isn't justified.
- **Per-embedding-model scoping:** the service has its own embedding
  model, loaded in-process, independent of any flow's embeddings
  service. Deployments needing multiple analytics embedding models
  run multiple `ontology-analytics` instances.
- **Flow-scoped ontology selection:** configured in flow instance
  config under an `ontology_analytics` block, same place as other
  flow-scoped service selection (LLM, embedding model, etc.).
- **Ontology-update semantics:** cutover. Once a new ontology version
  is swapped in, subsequent requests see the new state. No version
  pinning; users take responsibility for dangerous changes.
- **Processor shape:** FlowProcessor. Keeps the flow boundary
  available as a hook for future per-user state management, even
  though the analytics state itself is global to the process.
- **Embedding model configuration:** processor argument (e.g.
  `--embedding-model all-MiniLM-L6-v2`), not flow-class parameter.
  Default is minilm. Deployments needing a different model restart
  the service with a different argument; multi-model deployments
  run multiple service instances.
- **`kg-extract-ontology` after the split:** still owns LLM
  invocation, prompt construction, triple building, and emission.
  The only change is that it calls
  `flow("ontology-analytics-request")` to get the relevant ontology
  subset for a chunk, instead of maintaining its own embedder,
  vector store, and selector. The local `OntologyLoader`,
  `OntologyEmbedder`, `OntologySelector`, `InMemoryVectorStore` and
  the per-flow `flow_components` dict all go away.

## Future Work

- **Dynamic ontology learning.** A future flow may identify new
  potential ontology elements at runtime and extend the ontology in
  a learning/bootstrap fashion. That this is even feasible is a
  useful validation of the split: the analytics service becomes a
  reusable component with broader applications than the initial
  extractor use case. Several write-path shapes are viable —
  config-round-trip (learning flow writes back to config, normal
  config-push triggers re-embed, one source of truth, heavier per
  element) or a direct add API on the service (cheaper per element,
  but creates two sources of truth and loses state on restart). The
  config-round-trip feels like the right default but the decision
  is deferred until a concrete learning flow is designed.

## References

- Current implementation:
  `trustgraph-flow/trustgraph/extract/kg/ontology/`
- Related existing spec: `ontorag.md`
