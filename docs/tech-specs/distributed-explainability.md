---
layout: default
title: "Distributed Explainability"
parent: "Tech Specs"
---

# Distributed Explainability

## Status

Proposed

## Overview

When a retrieval or execution pipeline is composed of multiple
services, explainability must work across service boundaries.  This
spec defines how explain context propagates through service calls so
that the full provenance chain is preserved regardless of how many
services participate.

Supersedes the single-process model in query-time-explainability.md
where one GraphRAG instance owns the entire explain graph.

## Principles

1. **Explain context flows downstream on requests.**  Every service
   that supports explainability accepts two fields on its request:
   `explain` (bool) and `explain-parent` (context URI of the caller's
   stage).  When `explain` is false, no provenance work is performed.

2. **Explain context returns upstream on responses.**  Every response
   includes `explain-context` — the context URI of the stage that
   produced the output.  Empty when `explain` was false.

3. **The response context is the terminal node.**  When a service
   performs an internal chain of stages (A → B → C), the response
   returns C's context URI.  That is the derivation point for any
   subsequent work.  The full internal chain is still present in the
   explain graph — callers walk it by following prov:wasInformedBy
   links from C back through B and A.

4. **Each service links to its parent, nothing more.**  A service
   mints its own context URI, emits
   `this-context → prov:wasInformedBy → explain-parent`, and
   publishes its explain triples.  It does not need to know the full
   chain — the graph assembles itself from pairwise links.

5. **Explain events stream to a shared topic.**  Every service
   publishes explain triples to the explainability topic, tagged with
   the correlation ID (run-id or root context URI).  The caller
   subscribes to the topic filtered by that ID and receives a
   real-time stream of provenance events as stages complete across
   services.

6. **Hierarchical services relay explain events upstream.**  When
   service A calls service B, explain events emitted by B appear on
   the shared topic.  If the caller sits above A and subscribes to
   the topic, it sees B's events directly.  No manual relay needed
   — the topic is the shared bus.

## Request/Response Contract

On request schemas that support explainability:

```
explain: bool           # whether to emit provenance
explain-parent: str     # caller's context URI (empty if root)
```

On response schemas:

```
explain-context: str    # this service's terminal context URI
                        # (empty if explain was false)
```

## Context Linking Example

A planner orchestrates: subgraph-retrieval → synthesis.

```
Planner creates root context P
  │
  ├─ calls subgraph-retrieval(explain=true, explain-parent=P)
  │    internally: concept-extract(A) → embed(B) → lookup(C) → traverse(D)
  │    each stage: stage → prov:wasInformedBy → previous
  │    response: explain-context = D
  │
  ├─ calls synthesis(explain=true, explain-parent=D)
  │    mints context S, emits S → prov:wasInformedBy → D
  │    response: explain-context = S
  │
  └─ planner records: run-complete → prov:wasInformedBy → S
```

The explain graph for this run:

```
P ← A ← B ← C ← D ← S ← run-complete
```

Traversable end-to-end.  Each service only knew its immediate parent.

## Applicability

This pattern applies wherever explainability is relevant:

- Execution framework (planner, action worker, verification, policy)
- Retrieval services (graph RAG stages, document RAG)
- Agent framework (agent calling retrieval services)

Services that have no meaningful provenance to record (e.g. pure
local transforms like tabular-redact) can omit the explain fields
or pass them through unchanged.
