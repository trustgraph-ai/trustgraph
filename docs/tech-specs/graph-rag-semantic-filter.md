# GraphRAG Semantic Filter Improvement

## Problem Statement

The GraphRAG semantic filter is observed to be ineffective with certain
LLM models.  Smaller models in particular produce poor-quality edge
relevance scores, and there is a suspicion that models trained or
evaluated heavily on non-Roman-script datasets offer lower performance
on the semantic ranking operation.

The root cause is that the current implementation delegates edge
relevance scoring to the LLM via a prompt that asks the model to
assign a 1–10 relevance score to each knowledge-graph edge.  This
task — ranking structured triples for relevance to a natural-language
query — is not well covered in standard LLM evaluation suites, so
model benchmark scores are not predictive of performance on this
operation.  The result is that GraphRAG quality varies unpredictably
across model choices, undermining confidence in the pipeline.

Beyond model variability, the LLM scoring step has further problems:

- **Cost and latency.**  The LLM call consumes tokens and adds
  latency to every query, yet its output is unreliable.  Even when
  the model performs well, the cost is disproportionate for what is
  fundamentally a ranking operation.

- **Subjective scoring scale.**  The 1–10 relevance scale gives the
  model no objective criteria for what constitutes a 5 versus a 7.
  Different models interpret the scale differently, and even the same
  model can produce inconsistent scores across runs.

- **Redundancy with the embedding pre-filter.**  The pipeline already
  contains a cosine-similarity stage that ranks edges by semantic
  relevance using embeddings.  The LLM scoring step is a second
  filter applied on top of this, and it is not clear that it adds
  enough value to justify the additional cost and risk of
  degradation.

### Industry context

Semantic ranking is rigorously evaluated on dedicated benchmarks such
as MTEB (Massive Text Embedding Benchmark) and BEIR (Benchmarking
Information Retrieval), which test retrieval and reranking across
diverse domains.  The current TrustGraph approach — prompting a
general-purpose LLM to score and rank documents (the "listwise"
approach) — is known to be poorly optimized for this task.  It
suffers from positional bias, formatting failures, and
inconsistency at scale.

The industry standard for semantic ranking has moved to
cross-encoder models: lightweight, purpose-built models that take a
query–document pair as input and produce a single relevance score.
These models are fine-tuned on millions of relevance-labelled pairs
and dominate retrieval benchmarks.  They are fast, deterministic,
and do not require an LLM inference call.

## Architecture

### Cross-encoder service

A new request/response service that exposes a generic semantic
ranking API.  The service is not specific to GraphRAG — it is a
reusable building block for any component that needs to rank text
by relevance.

The service interface is pluggable.  Alternative implementations
can be swapped in behind the same API.

**Packaging options considered:**

- *`sentence-transformers`.*  Full-featured, widely used.
  However, it pulls in PyTorch (~2 GB), making containers
  very large.  Tested at ~1.8 seconds for 2200 edges.

- *`optimum.onnxruntime`.*  ONNX-based inference.  Still
  depends on PyTorch at import time despite using ONNX for
  inference.  Tested at ~4.2 seconds for 2200 edges.

- *`flashrank`.*  Lightweight wrapper around ONNX Runtime
  with a clean API (`Ranker`, `RerankRequest`).  No PyTorch
  dependency.  Tested at ~4.4 seconds for 2200 edges.

- *Pure `onnxruntime` + `tokenizers`.*  Leanest option
  (~200 MB total).  Requires manual tokenisation, padding,
  and numpy array management — more boilerplate to maintain.

- *External API (e.g. Cohere Rerank).*  No local model at
  all.  Adds network latency and an external dependency.

**Decision:** `flashrank` for the initial implementation.
No PyTorch dependency, clean API, comparable performance.
The pluggable interface allows swapping to another backend
later.

**Request:**

- `queries` — list of `{id, text}` objects.  In the GraphRAG use
  case these are the concepts extracted from the user's question.
- `documents` — list of `{id, text}` objects.  In the GraphRAG
  use case these are the candidate knowledge-graph edges
  represented as text.
- `limit` — integer.  Maximum number of results to return.

**Scoring:**

The service produces the cartesian product of all query–document
pairs and scores each pair through the cross-encoder model.  For
each document, the maximum score across all queries is taken as the
document's relevance score.  Documents are then ranked by this
score and the top `limit` results are returned.

**Response:**

A list of the top `limit` results, each containing:

- `document_id` — the ID of the matched document.
- `query_id` — the ID of the query (concept) that produced the
  highest score for this document.
- `score` — the relevance score.

Including `query_id` in the response supports the explainability
interface: it records that an edge was selected because it is
related to a specific concept.

### Integration

The cross-encoder service follows the standard TrustGraph service
integration pattern:

- **Base package (trustgraph-base).**  Schema definitions for the
  cross-encoder request/response messages.  A client class that
  other components (e.g. GraphRAG) can use to call the
  cross-encoder service.  Message translator registration so the
  pub/sub layer can serialise/deserialise the messages.

- **Flow package (trustgraph-flow).**  The cross-encoder service
  implementation itself — loads the model, listens for requests,
  scores pairs, returns results.  Flow definition support so the
  cross-encoder can be introduced into a processing flow via the
  standard flow configuration.  `flashrank` is added as a
  dependency of `trustgraph-flow`.  The service runs in its own
  container.

- **API gateway.**  A gateway endpoint that routes cross-encoder
  requests from the HTTP API to the service over pub/sub and
  returns the response.

- **CLI tool.**  A command-line utility
  (e.g. `tg-invoke-cross-encoder`) that calls the gateway
  endpoint for manual testing and debugging.

### Current GraphRAG pipeline

The current pipeline follows these steps:

1. **Concept extraction.**  An LLM prompt extracts key concepts
   from the user's query.

2. **Graph exploration.**  Seed entities are found via embedding
   similarity.  A subgraph is built by multi-hop traversal from
   the seed entities (up to `max_path_length` hops, capped at
   `max_subgraph_size` edges).

3. **Embedding pre-filter.**  Each edge is embedded as
   `"subject, predicate, object"` and scored by cosine similarity
   against the concept embeddings.  The top `edge_score_limit`
   (default 30) edges are kept.

4. **LLM edge scoring.**  The `kg-edge-scoring` prompt asks the
   LLM to assign a 1–10 relevance score to each remaining edge.
   The top `edge_limit` (default 25) edges are kept.

5. **LLM edge reasoning.**  The `kg-edge-reasoning` prompt asks
   the LLM to explain why each selected edge is relevant to the
   query.  Used for the explainability interface.

6. **Document tracing.**  Selected edges are traced back to their
   source documents in the librarian.  Runs concurrently with
   step 5.

7. **Synthesis.**  The `kg-synthesis` prompt generates the final
   answer from the selected edges and source document metadata.

### Potential improvements

#### Replace LLM edge scoring with cross-encoder (step 4)

The LLM edge scoring step is replaced by a call to the
cross-encoder service.  The candidate edges are the documents and
`edge_limit` is the limit.  This is a direct substitution: faster,
cheaper, deterministic, and more reliable across model choices.
The LLM `kg-edge-scoring` prompt is retired.

**Cross-encoder query input: concepts vs. raw query.**  There are
two options for what to use as the cross-encoder queries:

- *Option A: Raw user query.*  Pass the original question as a
  single query string.  Simpler, no dependency on concept
  extraction.  However, raw queries contain noise words and
  conversational phrasing that do not match well against the
  structured vocabulary of knowledge-graph edges.  A single query
  also means every edge competes against the full question — a
  partial match on one aspect is diluted.

- *Option B: Extracted concepts.*  Pass the concepts from step 1
  as separate queries.  The concepts are distilled, focused terms
  that are closer to the language of the edges.  With multiple
  concepts as independent queries, the cross-encoder scores each
  edge against each concept separately, giving better coverage —
  an edge only needs to match one concept well to be selected.
  The trade-off is a dependency on the LLM concept extraction
  step, but this is already in the pipeline and is a lightweight,
  reliable LLM call.

**Decision:** Option B — use extracted concepts.  The concept
extraction is fast, and the resulting terms produce better
cross-encoder matches against structured triples.

#### Edge text representation

The current embedding pre-filter represents each edge as
`"subject, predicate, object"`.  Two changes:

- **Drop commas.**  Commas add tokenisation noise without semantic
  value.

- **Direction-aware text.**  The reranker text should highlight
  the *new* information relative to the traversal direction.
  The frontier entity is already known context — repeating it
  adds noise and, when traversing from an object node, causes
  many edges to produce identical reranker text (e.g. 18
  products sharing the same `hasSubcategory Processors` triple
  all collapse to the same string when the subject is dropped).

  The text is constructed based on which position the frontier
  entity occupied in the triple:

  - **From subject** (s=entity): `"{predicate} {object}"` —
    the subject is known, predicate and object are new.
  - **From object** (o=entity): `"{subject} {predicate}"` —
    the object is known, subject and predicate are new.
  - **From predicate** (p=entity): `"{subject} {object}"` —
    the predicate is known, subject and object are new.

  This eliminates the duplicate-text problem that arises when
  traversing inward from a shared object node, and gives the
  cross-encoder a more informative signal at every hop.

#### Remove the embedding pre-filter (step 3)

The embedding pre-filter was introduced to reduce the number of
edges before the expensive LLM scoring call.  With the
cross-encoder replacing the LLM call, this cost equation changes.

**Arguments for removal:**

- The cross-encoder is fast enough to score the full subgraph
  directly.  In testing, 2200 edges scored in ~1.8 seconds; at
  the default `max_subgraph_size` of 150 edges, scoring takes
  a fraction of a second.

- The pre-filter is a weaker version of what the cross-encoder
  does.  Bi-encoder cosine similarity embeds the query and
  document independently and compares vectors; the cross-encoder
  processes both texts together through the full transformer,
  giving it much better relevance judgement.  Running a weaker
  filter before a stronger one adds latency without improving
  quality.

- Removing it eliminates an embedding service call (two batches:
  concepts + edges) and the associated latency.

**Arguments for keeping it:**

- If the subgraph is very large (thousands of edges), the
  cross-encoder's linear scaling could become a bottleneck.
  The pre-filter would act as a safety valve.

- The embedding call is cheap compared to an LLM call, so the
  overhead is modest.

**Decision:** Remove the pre-filter.  The `max_subgraph_size`
parameter (default 150) already caps the number of edges entering
this stage, so the cross-encoder will not face an unbounded
workload.  If very large subgraphs become a concern in future,
the pre-filter can be reintroduced or `max_subgraph_size` can be
tuned.

#### Iterative graph traversal with cross-encoder filtering

The current pipeline performs graph exploration and edge filtering
as separate phases: first build the full subgraph (up to
`max_path_length` hops), then score and filter edges.  An
alternative is to interleave traversal and filtering — at each
hop, use the cross-encoder to select relevant edges before
expanding further.

**Option A: Big-bang traversal then filter.**  Traverse the full
subgraph up to `max_path_length` hops from the seed entities,
collecting all edges up to `max_subgraph_size`.  Then
cross-encode the entire result to select the top edges.

- Simple to implement — the current traversal logic is largely
  unchanged.
- Produces large, unfocused subgraphs.  Irrelevant branches are
  explored and scored even though they will be discarded.
- Poorly suited to multi-hop reasoning.  For a query about
  Voyager 1, the subgraph includes Voyager 2's edges because
  they are within hop distance, and the filter must then
  separate them.

**Option B: Iterative hop-and-filter.**  At each hop:

1. Retrieve all edges one hop from the current frontier nodes.
2. Cross-encode these edges against the query concepts.
3. Select the top relevant edges.
4. The target nodes of the selected edges become the frontier
   for the next hop.
5. Repeat up to `max_path_length` hops.

The final set of selected edges across all hops is the input to
synthesis.

- **Guided exploration.**  Each hop focuses the search by
  pruning irrelevant branches before expanding further.  The
  working set stays small and relevant at every step.
- **Multi-hop reasoning works naturally.**  Following
  "Voyager 1 → has-event → crossed the heliopause" succeeds
  because each hop is individually relevant and leads to the
  next.
- **Smaller total workload.**  Fewer edges are scored overall
  because irrelevant branches are never expanded.
- **Trade-off: greedy pruning.**  An edge discarded at hop 1
  cannot lead to relevant edges at hop 2.  This is inherent in
  any bounded traversal, and the cross-encoder is better
  equipped to make this relevance judgement than a blind hop
  limit.
- **Trade-off: sequential latency.**  Hops cannot be
  parallelised since each depends on the previous.  However,
  each cross-encoder call on a small edge set is very fast
  (sub-second for typical working sets).

**Decision:** Option B — iterative hop-and-filter.  The guided
traversal produces more focused subgraphs and supports multi-hop
reasoning, which is a significant quality improvement over the
current approach.

#### Replace LLM edge reasoning with cross-encoder metadata (step 5)

The current `kg-edge-reasoning` prompt asks the LLM to explain why
each edge is relevant.  With the cross-encoder now making the
selection, this explanation would be a post-hoc fabrication — the
LLM was not involved in the decision.

- *Option A: Keep LLM reasoning.*  Generates natural-language
  explanations but they are not grounded in the actual selection
  process.  Adds an LLM call per query.

- *Option B: Record cross-encoder metadata.*  The cross-encoder
  already returns the matched concept and score for each selected
  edge.  Use this directly as the explanation.

**Decision:** Option B.  The cross-encoder metadata is the true
reason the edge was selected.  The `kg-edge-reasoning` prompt is
retired.

#### Explainability interface update

The explainability interface uses a `Focus` entity containing
`EdgeSelection` sub-entities.  Each `EdgeSelection` currently
carries an `edge` (the quoted triple) and a `reasoning` field
(free-text LLM prose), stored as `tg:reasoning` in the
provenance graph.

With the cross-encoder replacing LLM reasoning, the
`EdgeSelection` type gains two new predicates and drops one:

- **Remove** `tg:reasoning` — no longer produced.
- **Add** `tg:concept` — the concept text that produced the
  highest cross-encoder score for this edge.
- **Add** `tg:score` — the cross-encoder relevance score.

This is an evolution of the existing `EdgeSelection` type, not a
new entity type.  The edge selection sub-entities currently have
no `rdf:type` declared; a new `tg:EdgeSelection` type should be
added so that consumers can identify them in the provenance
graph.  The `Focus` entity and its relationship to `Exploration`
are unchanged.

The `Focus` entity's token-usage metadata (`tg:inToken`,
`tg:outToken`, `tg:llmModel`) no longer applies since there is
no LLM call.  These fields are dropped from the Focus entity.

### Proposed pipeline

1. **Concept extraction.**  Unchanged — LLM extracts key concepts
   from the user's query.

2. **Seed entity lookup.**  Find seed entities via embedding
   similarity against the extracted concepts.

3. **Iterative hop-and-filter.**  For each hop up to
   `max_path_length`:

   a. Retrieve all edges one hop from the current frontier nodes.

   b. Filter and represent edges for scoring:

      - **Schema predicate filter.**  Edges with RDF/RDFS/OWL
        schema predicates (`rdfs:domain`, `owl:inverseOf`, etc.)
        are removed.  `rdf:type` is kept as it carries useful
        data signal.

      - **IRI filter.**  Edges where the reranker-visible text
        components (after label resolution) are still raw IRIs
        are removed — the cross-encoder cannot meaningfully score
        unresolved URIs.  Only the components that would appear
        in the reranker text are checked, based on traversal
        direction.

      - **Direction-aware text.**  Each surviving edge is
        represented using direction-aware text: from a subject
        node use `"{predicate} {object}"`, from an object node
        use `"{subject} {predicate}"`, from a predicate node
        use `"{subject} {object}"`.

      - **Reranker input cap.**  The candidate set is truncated
        to `max_reranker_input` (default 350) edges.  This is a
        safety measure, not an accuracy optimisation — there is
        no point in producing a perfectly ranked edge set if the
        reranker crashes or times out because it was handed
        thousands of candidates.  The cap is applied after
        filtering so that the most useful edges fill the budget.

   c. Score edges against the extracted concepts using the
      cross-encoder service.

   d. Select the top relevant edges.  The target nodes of the
      selected edges become the frontier for the next hop.

4. **Document tracing.**  Selected edges are traced back to source
   documents.

5. **Synthesis.**  The `kg-synthesis` prompt generates the final
   answer from the selected edges and source document metadata.

### Implementation order

1. Cross-encoder service with full integration (base schema,
   flow service, gateway endpoint, CLI tool).
2. GraphRAG pipeline changes (iterative hop-and-filter,
   edge representation, remove pre-filter).
3. Explainability update (`tg:EdgeSelection` type, concept
   and score predicates, retire `tg:reasoning`).
4. Retire `kg-edge-scoring` and `kg-edge-reasoning` prompts.
5. Update `tg-invoke-graph-rag` and `tg-show-explain-trace`
   to display the new metadata.  Use these as the main
   end-to-end test.
6. Fix any failing unit tests, then add new tests as needed.
7. Write guidance for UX devs to update the UI for the new
   explainability predicates.

## UX developer guidance

This section describes the changes to the explainability interface
that affect frontend rendering of GraphRAG Focus events.

### What changed

Edge selection in GraphRAG previously used LLM-based scoring and
reasoning.  Each selected edge carried a `tg:reasoning` predicate
with free-text explanation from the LLM.  This has been replaced
by a cross-encoder reranker that scores edges against query
concepts.  The explainability data now carries structured metadata
instead of free text.

### Removed

- **`tg:reasoning`** is no longer emitted on edge selection
  entities in GraphRAG Focus events.  UX code that reads
  `edge_sel.reasoning` will get an empty string.  Remove any
  rendering that displays a "Reasoning" or "Reason" field for
  Focus edges.

- The **`kg-edge-scoring`**, **`kg-edge-reasoning`**, and
  **`kg-edge-selection`** prompts are retired.  Any UX that
  references these prompt names should be cleaned up.

### Added

Each edge selection entity within a Focus event now has three
new properties:

| RDF predicate | API field | Type | Description |
|---|---|---|---|
| `rdf:type tg:EdgeSelection` | (type check) | — | Each edge selection entity is now explicitly typed |
| `tg:concept` | `edge_sel.concept` | `str` | The query concept that matched this edge |
| `tg:score` | `edge_sel.score` | `float` or `None` | Cross-encoder relevance score (0.0–1.0) |

The `tg:edge` predicate (RDF-star quoted triple) is unchanged.

### How to render

The recommended rendering for each selected edge in a Focus event:

```
Edge: (subject_label, predicate_label, object_label)
  Concept: <concept>  Score: <score formatted to 4 decimal places>
```

Scores near 1.0 indicate high relevance; scores near 0.0 indicate
low relevance.  UX could use the score to drive visual indicators
such as colour intensity or a relevance bar.

Edges are not returned in score order — they arrive in traversal
order across hops.  If the UX wants to display edges ranked by
relevance, sort by `edge_sel.score` descending.

### API classes (Python)

The `EdgeSelection` dataclass in `trustgraph.api.explainability`
has these fields:

```python
@dataclass
class EdgeSelection:
    uri: str
    edge: Optional[Dict[str, str]]  # {"s": ..., "p": ..., "o": ...}
    reasoning: str = ""              # Legacy, always empty for new traces
    concept: str = ""                # Query concept that matched
    score: Optional[float] = None    # Cross-encoder relevance score
```

These are populated when calling
`ExplainabilityClient.fetch_focus_with_edges()` or when parsing
inline provenance triples from the streaming response.

### WebSocket response format

For inline explainability via the streaming WebSocket, Focus events
arrive as `message_type: "explain"` responses.  The `explain_triples`
array contains the edge selection triples.  The relevant predicates
in wire format are:

```json
{"s": {"t": "i", "i": "<edge_sel_uri>"},
 "p": {"t": "i", "i": "https://trustgraph.ai/ns/concept"},
 "o": {"t": "l", "v": "flyby event"}}

{"s": {"t": "i", "i": "<edge_sel_uri>"},
 "p": {"t": "i", "i": "https://trustgraph.ai/ns/score"},
 "o": {"t": "l", "v": "0.9962"}}
```

Note that `tg:score` is transmitted as a string literal and must
be parsed to a float on the client side.

### Exploration event

The Exploration event's `edge_count` field now reports the number
of edges selected by the cross-encoder across all hops (previously
it reported the total number of edges retrieved before filtering).
The `entities` list continues to report the seed entities found
by vector search.
