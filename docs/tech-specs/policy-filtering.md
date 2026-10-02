---
layout: default
title: "Policy Filtering Overview"
parent: "Tech Specs"
---

# Policy Filtering Overview

## Overview

This specification describes the policy filtering layer that
determines what data a user may see when querying the knowledge
graph. It covers the problem space, the policy language, and how
policies interact with user context at query time.

See also:
- [Policy Ontology](policy-ontology.md) — vocabulary, relationships,
  storage, and the full Turtle ontology
- [Policy Audit Events](policy-audit-events.md) — audit event types,
  payloads, and the policy-events queue
- [Policy Examples](policy-examples.md) — worked examples with
  SPARQL targets and CONSTRUCT rules

## Problem Statement

A shared knowledge graph contains data from multiple sources,
about multiple entities, at multiple sensitivity levels. Different
users need different views of the same graph — not because of
workspace separation (which is a deployment boundary) but because
of who they are, what they're doing, and what policies govern
their access.

### The same data, different viewers

Consider an enterprise graph containing client records, internal
research, deal intelligence, and operational data. A relationship
manager should see their assigned clients' data but not other
clients'. A compliance officer should see audit trails across the
organisation but not deal-specific intelligence. A client logging
into a portal should see their own holdings and nothing else.

These are not edge cases — they are the normal operating mode of
any multi-user system built on a shared graph.

### Information barriers within the same organisation

Organisations routinely erect barriers between groups that must
not share information, even though they work for the same company
and query the same graph. The classic case is Chinese Walls in
financial services: buy-side and sell-side teams on the same deal
must not see each other's intelligence. But the pattern is
general:

- A law firm where two partners advise opposing parties in a
  dispute. Both query the firm's knowledge graph, but neither
  should see the other's case materials.
- A pharmaceutical company where the clinical trials team and the
  commercial team must be isolated to prevent inside information
  leaking into marketing decisions.
- A consultancy where competing client engagements must not
  cross-contaminate.

These barriers are dynamic — they activate when a conflict arises
and deactivate when it resolves. They cannot be modelled as static
permissions on folders or tables.

### The same person, different roles

A single user may legitimately need different views of the graph
depending on what role they are acting in at the time. A doctor
who is also a patient at the same hospital should see all records
when acting as treating physician and only their own records when
acting as patient. A portfolio manager who is also a personal
investor should see all managed accounts in their professional
role but only their personal account when acting as a retail
client.

The access decision depends not just on who the user is but on
which hat they are currently wearing — captured by the user
context's role field.

### Pre-context pruning for AI safety

When the graph feeds an LLM — for RAG synthesis, report
generation, or conversational queries — the policy boundary must
sit upstream of the model. Data that a user should not see must
never enter the LLM's context window. This is a structural
guarantee: the model cannot leak what it was never given,
regardless of prompt injection attacks or instruction-following
failures.

Post-hoc redaction (letting the LLM see everything and then
filtering the output) is not acceptable. The policy engine prunes
the graph before context assembly, not after.

### Why static permissions don't work

Traditional file-and-folder permissions answer "is this user
allowed to access this resource?" — a binary gate on a named
object. Knowledge graph access is fundamentally different:

- **The resource is a traversal, not a document.** A query like
  "show me my portfolio exposure by sector" traverses account
  nodes, holding nodes, security nodes, and classification nodes.
  Policy must scope the traversal at the account level while
  allowing it through shared reference data.
- **Shared reference data must be accessible without leaking
  private data.** The fact that "AAPL is classified as Technology"
  is public. The fact that "Client A holds 5,000 shares of AAPL"
  is private. Both live in the same graph.
- **Absence of data must not be informative.** A policy-filtered
  response must be structurally indistinguishable from a response
  where the filtered data never existed. No "access denied"
  markers, no empty placeholders, no differences in response shape
  that reveal the existence of hidden data.

## Policy Representation: SHACL-AF

Policies are expressed using SHACL Advanced Features (SHACL-AF),
the W3C standard for graph validation and rule evaluation.
SHACL-AF is not a future compilation target — it is how policies
are represented, stored, and evaluated.

### Why SHACL-AF

SHACL was designed to validate RDF graphs against conditions.
SHACL Advanced Features extends it with capabilities that make
it suitable for policy evaluation:

- **Custom targets (`sh:SPARQLTarget`)** select focus nodes
  dynamically using SPARQL. A policy that applies to "all
  triples whose subject is assigned to the requesting user"
  requires a query that joins user context with data — not
  simple class-based targeting.
- **SPARQL rules (`sh:SPARQLRule`)** execute CONSTRUCT queries
  with the focus node pre-bound as `$this`. The rule traverses
  graph paths, evaluates conditions, and produces determination
  triples.
- **Triple rules (`sh:TripleRule`)** compose simple
  subject-predicate-object determinations from node expressions,
  suitable for straightforward policies.
- **`sh:order`** controls rule execution order within a shape
  and across shapes, handling priority when multiple policies
  match.
- **Monotonic inference** — SHACL rules add triples to an
  inference graph without modifying the original data. Policy
  determinations annotate the data graph rather than changing
  it, preserving the separation between asserted facts and
  policy evaluations.

A policy expressed as a SHACL-AF shape has four parts:

1. **Target** — which graph nodes the policy applies to
   (`sh:targetClass`, `sh:targetNode`, or `sh:SPARQLTarget`)
2. **Condition** — prerequisites that must hold before the rule
   fires (`sh:condition` referencing other shapes)
3. **Rule body** — the evaluation logic (`sh:SPARQLRule` with a
   CONSTRUCT query producing `sh:ValidationResult` triples)
4. **Determination** — the `sh:resultSeverity` IRI and
   `tg-pol:blocks` boolean from the ValidationResult, which
   control the audit event and filtering action

The policy engine executes both the SELECT target (to identify
matching nodes) and the CONSTRUCT rule (to produce the
determination). The CONSTRUCT output is parsed for
`sh:resultSeverity`, `sh:resultMessage`, and `tg-pol:blocks`
— these drive the filtering decision and the policy audit
event payload.

### Interaction with user context

At query time, the user context is injected into the evaluation
graph as a set of triples describing the current accessor. SHACL
rules reference user context properties in their targets and
conditions using the same SPARQL patterns used for data graph
properties.

The user context lives in an ephemeral named graph for the
duration of the query. Policies live in `urn:graph:policy`. The
data lives in the default graph (or domain-specific named
graphs). The SHACL engine evaluates rules across all three.

### Policy enforcement mode

The presence of policies in `urn:graph:policy` determines
whether user context is required. If policies exist, every
request to the policy-filtered query service must include a
`user_context` — requests without one are rejected as
validation errors. If no policies are loaded, `user_context`
is optional and the service operates in open mode.

This means existing deployments without policies continue to
work unchanged. Loading policies into the policy graph is the
explicit opt-in to enforcement.
