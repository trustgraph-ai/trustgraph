---
layout: default
title: "Guided Graph Traversal"
parent: "Tech Specs"
---

# Guided Graph Traversal

## Status

Draft

## Problem Statement

The GraphRAG capability is a popular and extensively-used retrieval
mechanism with good evaluation results for precision and recall. There
are circumstances where the caller has additional information which
could be used to steer the retrieval to more efficient discovery of
pertinent knowledge for the retrieval.

## Proposed Additions

The following information will be considered for addition to the
GraphRAG query interface:

1. **Grounding seeds** — an optional list of text concepts
   (e.g. `["graphrag", "information retrieval", "graph traversal"]`)
   which bypass the standard grounding phase. When provided, these
   concepts are used directly for entity discovery instead of
   extracting concepts from the query via the LLM.

2. **Graph seeds** — an optional list of IRIs to use as initial entry
   points for graph traversal. These allow the caller to specify
   known entities in the knowledge graph, skipping the
   concept-embedding lookup and placing the traversal frontier
   directly at the given nodes.

3. **Language restrictions** — an optional list of language tags
   (e.g. `["en", "fr"]`) to restrict retrieval to knowledge
   expressed in the specified languages. An empty string `""` matches
   literals with no language tag, so `["en", "fr", ""]` would match
   English, French, and untagged literals.

4. **Traversal instructions** — directives that restrict which
   traversal steps are taken during the graph walk. There are two
   kinds of traversal restriction:

   Traversal instructions are expressed as an ordered list, where
   each item corresponds to a hop in the multihop traversal. Each
   item can specify one or both of the following restrictions:

   a. **Type restriction** — a list of RDF type IRIs. Only nodes
      whose `rdf:type` matches one of the specified types are
      eligible for selection at this hop.

   b. **Relationship restriction** — a list of predicate IRIs. Only
      edges whose predicate matches one of the specified IRIs are
      followed at this hop.

   The first item in the list selects the starting nodes, so it can
   only specify a type restriction (there is no preceding edge to
   constrain). Subsequent items may specify a type restriction, a
   relationship restriction, or both.

   For example, a two-hop traversal might be expressed as:

   ```
   [
     { "types": ["http://example.org/Person"] },
     { "relationships": ["http://example.org/worksFor"], "types": ["http://example.org/Organisation"] }
   ]
   ```

   This would start at `http://example.org/Person` nodes, then follow only
   `http://example.org/worksFor` edges to reach `http://example.org/Organisation` nodes.

## Changes Required

### API Schema (`specs/api/components/schemas/rag/GraphRagRequest.yaml`)

Add optional fields: `grounding_seeds`, `graph_seeds`, `languages`,
and `traversal_instructions`.

### Data Model (`trustgraph-base/trustgraph/schema/retrieval.py`)

Add corresponding fields to the `GraphRagQuery` dataclass. Validate
that `grounding_seeds` and `graph_seeds` are not both provided.

### Gateway Dispatch (`trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py`)

Pass the new fields through from the API request to `GraphRagQuery`.

### GraphRAG Core (`trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`)

- **Grounding seeds**: When provided, skip the LLM concept extraction
  call and use the supplied concepts directly for entity embedding
  lookup.

- **Graph seeds**: When provided, skip both grounding and entity
  lookup. Set the traversal frontier directly to the specified IRIs.

- **Language filtering**: Filter candidate triples by language tag
  before reranking. Only triples whose literal values match one of
  the specified language tags (or have no language tag, if `""` is
  in the list) are retained.

- **Traversal instructions**: Make `hop_and_filter()` hop-aware so
  that each iteration applies the restrictions from the
  corresponding item in the traversal instructions list:

  - **Relationship restrictions**: Filter candidate edges by
    predicate IRI before passing to the reranker.

  - **Type restrictions**: Look up `rdf:type` for candidate nodes
    and discard nodes that do not match. This requires additional
    triple queries per hop that do not exist today.

  All traversal restrictions are applied before reranking so that
  the reranker only scores edges that are eligible for selection.

### Python API Client (`trustgraph-base/trustgraph/base/graph_rag_client.py`)

Add the new optional parameters to `GraphRagClient.rag()` so that
callers can pass grounding seeds, graph seeds, language restrictions,
and traversal instructions programmatically.

### CLI (`trustgraph-cli/trustgraph/cli/invoke_graph_rag.py`)

Add command-line arguments for the new fields to `tg-invoke-graph-rag`.

### Tests

Cover the new code paths: grounding seeds, graph seeds, language
filtering, traversal instructions (type and relationship
restrictions), and the validation that both seed types cannot be
specified together.

## Design Decisions

- **Grounding seeds and graph seeds are mutually exclusive**.
  Grounding seeds bypass the LLM concept extraction phase but still
  go through entity embedding lookup. Graph seeds bypass both
  grounding and entity lookup entirely, placing the traversal
  frontier directly at the specified nodes. Specifying both is
  invalid.

- **Existing parameters still apply**. Parameters such as
  `max_path_length`, `edge_limit`, and reranker scoring are
  unchanged. Traversal restrictions are applied first to narrow the
  candidate set, then existing limits and scoring operate on the
  filtered results.

- **Restrictions are applied before reranking**. The reranker only
  scores edges that are eligible for selection, avoiding wasted
  computation on candidates that would be discarded.
