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

## Open Questions

- **Interaction between seeds**: Specifying both grounding seeds and
  graph seeds is invalid. Grounding seeds bypass the LLM concept
  extraction phase but still go through entity embedding lookup.
  Graph seeds bypass both grounding and entity lookup entirely,
  placing the traversal frontier directly at the specified nodes.
- **Interaction with existing parameters**: Existing parameters such
  as `max_path_length`, `edge_limit`, and reranker scoring still
  apply. Traversal restrictions are applied first to narrow the
  candidate set, then existing limits and scoring operate on the
  filtered results.
