---
layout: default
title: "SPARQL Query Service Technical Specification"
parent: "Tech Specs"
---

# SPARQL Query Service Technical Specification

## Overview

A pub/sub-hosted SPARQL query service that accepts SPARQL queries, decomposes
them into triple pattern lookups via the existing triples query pub/sub
interface, performs in-memory joins/filters/projections, and returns SPARQL
result bindings.

This makes the triple store queryable using a standard graph query language
without coupling to any specific backend (Neo4j, Cassandra, FalkorDB, etc.).

## Goals

- **SPARQL 1.1 support**: SELECT, ASK, CONSTRUCT, DESCRIBE queries
- **Backend-agnostic**: query via the pub/sub triples interface, not direct
  database access
- **Standard service pattern**: FlowProcessor with ConsumerSpec/ProducerSpec,
  using TriplesClientSpec to call the triples query service
- **Correct SPARQL semantics**: proper BGP evaluation, joins, OPTIONAL, UNION,
  FILTER, BIND, aggregation, solution modifiers (ORDER BY, LIMIT, OFFSET,
  DISTINCT)

## Background

The triples query service provides a single-pattern lookup: given optional
(s, p, o) values, return matching triples. This is the equivalent of one
triple pattern in a SPARQL Basic Graph Pattern.

To evaluate a full SPARQL query, we need to:
1. Parse the SPARQL string into an algebra tree
2. Walk the algebra tree, issuing triple pattern lookups for each BGP pattern
3. Join results across patterns (nested-loop or hash join)
4. Apply filters, optionals, unions, and aggregations in-memory
5. Project and return the requested variables

rdflib (already a dependency) provides a SPARQL 1.1 parser and algebra
compiler. We use rdflib to parse queries into algebra trees, then evaluate
the algebra ourselves using the triples query client as the data source.

## Technical Design

### Architecture

```
                       pub/sub
  [Client] ──request──> [SPARQL Query Service] ──triples-request──> [Triples Query Service]
  [Client] <─response── [SPARQL Query Service] <─triples-response── [Triples Query Service]
```

The service is a FlowProcessor that:
- Consumes SPARQL query requests
- Uses TriplesClientSpec to issue triple pattern lookups
- Evaluates the SPARQL algebra in-memory
- Produces result responses

### Components

1. **SPARQL Query Service (FlowProcessor)**
   - ConsumerSpec for incoming SPARQL requests
   - ProducerSpec for outgoing results
   - TriplesClientSpec for calling the triples query service
   - Delegates parsing and evaluation to the components below

   Module: `trustgraph-flow/trustgraph/query/sparql/service.py`

2. **SPARQL Parser (rdflib wrapper)**
   - Uses `rdflib.plugins.sparql.prepareQuery` / `parseQuery` and
     `rdflib.plugins.sparql.algebra.translateQuery` to produce an algebra tree
   - Extracts PREFIX declarations, query type (SELECT/ASK/CONSTRUCT/DESCRIBE),
     and the algebra root

   Module: `trustgraph-flow/trustgraph/query/sparql/parser.py`

3. **Algebra Evaluator**
   - Recursive evaluator over the rdflib algebra tree
   - Each algebra node type maps to an evaluation function
   - BGP nodes issue triple pattern queries via TriplesClient
   - Join/Filter/Optional/Union etc. operate on in-memory solution sequences

   Module: `trustgraph-flow/trustgraph/query/sparql/algebra.py`

4. **Solution Sequence**
   - A solution is a dict mapping variable names to Term values
   - Solution sequences are lists of solutions
   - Join: hash join on shared variables
   - LeftJoin (OPTIONAL): hash join preserving unmatched left rows
   - Union: concatenation
   - Filter: evaluate SPARQL expressions against each solution
   - Projection/Distinct/Order/Slice: standard post-processing

   Module: `trustgraph-flow/trustgraph/query/sparql/solutions.py`

### Data Models

#### Request

```python
@dataclass
class SparqlQueryRequest:
    user: str = ""
    collection: str = ""
    query: str = ""           # SPARQL query string
    limit: int = 10000        # Safety limit on results
```

#### Response

```python
@dataclass
class SparqlQueryResponse:
    error: Error | None = None
    query_type: str = ""      # "select", "ask", "construct", "describe"

    # For SELECT queries
    variables: list[str] = field(default_factory=list)
    bindings: list[SparqlBinding] = field(default_factory=list)

    # For ASK queries
    ask_result: bool = False

    # For CONSTRUCT/DESCRIBE queries
    triples: list[Triple] = field(default_factory=list)

@dataclass
class SparqlBinding:
    values: list[Term | None] = field(default_factory=list)
```

### BGP Evaluation Strategy

For each triple pattern in a BGP:
- Extract bound terms (concrete IRIs/literals) and variables
- Call `TriplesClient.query_stream(s, p, o)` with bound terms, None for
  variables
- Map returned triples back to variable bindings

For multi-pattern BGPs, join solutions incrementally:
- Order patterns by selectivity (patterns with more bound terms first)
- For each subsequent pattern, substitute bound variables from the current
  solution sequence before querying
- This avoids full cross-products and reduces the number of triples queries

### Streaming and Early Termination

The triples query service supports streaming responses (batched delivery via
`TriplesClient.query_stream`). The SPARQL evaluator should use streaming
from the start, not as an optimisation. This is important because:

- **Early termination**: when the SPARQL query has a LIMIT, or when only one
  solution is needed (ASK queries), we can stop consuming triples as soon as
  we have enough results. Without streaming, a wildcard pattern like
  `?s ?p ?o` would fetch the entire graph before we could apply the limit.
- **Memory efficiency**: results are processed batch-by-batch rather than
  materialising the full result set in memory before joining.

The batch callback in `query_stream` returns a boolean to signal completion.
The evaluator should signal completion (return True) as soon as sufficient
solutions have been produced, allowing the underlying pub/sub consumer to
stop pulling batches.

### Parallel BGP Execution (Phase 2 Optimisation)

Within a BGP, patterns that share variables benefit from sequential
evaluation with bound-variable substitution (query results from earlier
patterns narrow later queries). However, patterns with no shared variables
are independent and could be issued concurrently via `asyncio.gather`.

A practical approach for a future optimisation pass:
- Analyse BGP patterns and identify connected components (groups of
  patterns linked by shared variables)
- Execute independent components in parallel
- Within each component, evaluate patterns sequentially with substitution

This is not needed for correctness -- the sequential approach works for all
cases -- but could significantly reduce latency for queries with independent
pattern groups. Flagged as a phase 2 optimisation.

### FILTER Expression Evaluation

rdflib's algebra represents FILTER expressions as expression trees. We
evaluate these against each solution row, supporting:
- Comparison operators (=, !=, <, >, <=, >=)
- Logical operators (&&, ||, !)
- SPARQL built-in functions (isIRI, isLiteral, isBlank, str, lang,
  datatype, bound, regex, etc.)
- Arithmetic operators (+, -, *, /)

## Implementation Order

1. **Schema and service skeleton** -- define SparqlQueryRequest/Response
   dataclasses, create the FlowProcessor subclass with ConsumerSpec,
   ProducerSpec, and TriplesClientSpec wired up. Verify it starts and
   connects.

2. **SPARQL parsing** -- wrap rdflib's parser to produce algebra trees from
   SPARQL strings. Handle parse errors gracefully. Unit test with a range of
   query shapes.

3. **BGP evaluation** -- implement single-pattern and multi-pattern BGP
   evaluation using TriplesClient. This is the core building block. Test
   with simple SELECT WHERE { ?s ?p ?o } queries.

4. **Joins and solution sequences** -- implement hash join, left join (for
   OPTIONAL), and union. Test with multi-pattern queries.

5. **FILTER evaluation** -- implement the expression evaluator for FILTER
   clauses. Start with comparisons and logical operators, then add built-in
   functions incrementally.

6. **Solution modifiers** -- DISTINCT, ORDER BY, LIMIT, OFFSET, projection.

7. **ASK / CONSTRUCT / DESCRIBE** -- extend beyond SELECT. ASK is trivial
   (non-empty result = true). CONSTRUCT builds triples from a template.
   DESCRIBE fetches all triples for matched resources.

8. **Aggregation** -- GROUP BY, HAVING, COUNT, SUM, AVG, MIN, MAX,
   GROUP_CONCAT, SAMPLE.

9. **BIND, VALUES, subqueries** -- remaining SPARQL 1.1 features.

10. **API gateway integration** -- add SparqlQueryRequestor dispatcher,
    request/response translators, and API endpoint so that the SPARQL
    service is accessible via the HTTP gateway.

11. **SDK support** -- add `sparql_query()` method to FlowInstance in the
    Python API SDK, following the same pattern as `triples_query()`.

12. **CLI command** -- add a `tg-sparql-query` CLI command that takes a
    SPARQL query string (or reads from a file/stdin), submits it via the
    SDK, and prints results in a readable format (table for SELECT,
    true/false for ASK, Turtle for CONSTRUCT/DESCRIBE).

## Performance Considerations

In-memory join over pub/sub round-trips will be slower than native SPARQL on
a graph database. Key mitigations:

- **Streaming with early termination**: use `query_stream` so that
  limit-bound queries don't fetch entire result sets. A `SELECT ... LIMIT 1`
  against a wildcard pattern fetches one batch, not the whole graph.
- **Bound-variable substitution**: when evaluating BGP patterns sequentially,
  substitute known bindings into subsequent patterns to issue narrow queries
  rather than broad ones followed by in-memory filtering.
- **Parallel independent patterns** (phase 2): patterns with no shared
  variables can be issued concurrently.
- **Query complexity limits**: may need a cap on the number of triple pattern
  queries issued per SPARQL query to prevent runaway evaluation.

### Named Graph Mapping

SPARQL's `GRAPH ?g { ... }` and `GRAPH <uri> { ... }` clauses map to the
triples query service's graph filter parameter:

- `GRAPH <uri> { ?s ?p ?o }` — pass `g=uri` to the triples query
- Patterns outside any GRAPH clause — pass `g=""` (default graph only)
- `GRAPH ?g { ?s ?p ?o }` — pass `g="*"` (all graphs), then bind `?g` from
  the returned triple's graph field

The triples query interface does not support a wildcard graph natively in
the SPARQL sense, but `g="*"` (all graphs) combined with client-side
filtering on the returned graph values achieves the same effect.

## Open Questions

- **SPARQL 1.2**: rdflib's parser support for 1.2 features (property paths
  are already in 1.1; 1.2 adds lateral joins, ADJUST, etc.). Start with
  1.1 and extend as rdflib support matures.
